#!/usr/bin/env python3
"""
analog_renderer.py
Renders a character to a hardware-specific analog timeline using a
device-independent font and a device-specific profile.
"""

import argparse
import math
import csv
import sys

from vector_font import SIMPLE_FONT
from device_profiles import DEVICE_15_INCH, DEVICE_17_INCH, DEVICE_15_INCH_INV_Y

# --- Default rendering parameters ---
DS_EM = 0.01            # Spatial step per sample in EM units (~1% of EM box height)
DRAW_SPEED_EM_S = 2.0   # Drawing speed in EM units per second

def resample_polyline(poly, step):
    """Returns points sampled along a polyline at ~constant spacing 'step'."""
    out = []
    if len(poly) < 2:
        return out

    # Calculate cumulative lengths at each vertex
    seglens = []
    for i in range(len(poly)-1):
        x0, y0 = poly[i]
        x1, y1 = poly[i+1]
        seglens.append(math.hypot(x1 - x0, y1 - y0))

    total_len = sum(seglens)
    if total_len == 0:
        return [poly[0]]

    num_points = max(1, int(round(total_len / step)))

    s_targets = [total_len * (i / num_points) for i in range(num_points + 1)]

    i_seg = 0
    s_accum = 0.0
    for s_target in s_targets:
        while i_seg < len(seglens) and s_target > s_accum + seglens[i_seg] + 1e-9: # Add epsilon for float errors
            s_accum += seglens[i_seg]
            i_seg += 1

        if i_seg >= len(seglens):
            out.append(poly[-1])
            continue

        xA, yA = poly[i_seg]
        xB, yB = poly[i_seg+1]
        seg_len = seglens[i_seg]

        u = 0.0 if seg_len == 0 else (s_target - s_accum) / seg_len
        x = xA + u * (xB - xA)
        y = yA + u * (yB - yA)
        out.append((x, y))

    return out

def render_char_to_em_timeline(char, settle_us):
    """From a character, build a device-independent timeline [(t_us, x_em, y_em, z_on?)]."""
    if char not in SIMPLE_FONT:
        raise ValueError(f"Character '{char}' not found in font.")

    strokes = SIMPLE_FONT[char]
    timeline = []
    t_us = 0.0

    for stroke_polyline in strokes:
        if len(stroke_polyline) < 2:
            continue

        # 1. Blanked move to the start of the stroke
        start_x, start_y = stroke_polyline[0]
        timeline.append((t_us, start_x, start_y, 0)) # z=0 for beam off
        t_us += settle_us

        # 2. Resample the stroke polyline to get dense points
        samples = resample_polyline(stroke_polyline, DS_EM)
        if not samples:
            continue

        # 3. Draw the stroke with the beam on
        dt_us = 1e6 * (DS_EM / DRAW_SPEED_EM_S) if DRAW_SPEED_EM_S > 0 else 0
        for x, y in samples:
            timeline.append((t_us, x, y, 1)) # z=1 for beam on
            t_us += dt_us

        # 4. Add a final point with beam off to end the stroke
        end_x, end_y = samples[-1]
        timeline.append((t_us, end_x, end_y, 0))

    return timeline

def map_timeline_to_volts(timeline_em, profile):
    """Maps a device-independent timeline to hardware-specific voltages."""
    out = []
    for t_us, x_em, y_em, z_on in timeline_em:
        y_final = (1.0 - y_em) if profile['invert_y'] else y_em

        # Map EM unit [0,1] to voltage span centered around center voltage
        vx = profile['vx_center'] + profile['vx_span'] * (x_em - 0.5)
        vy = profile['vy_center'] + profile['vy_span'] * (y_final - 0.5)
        vz = profile['vz_on'] if z_on else profile['vz_off']

        out.append((int(round(t_us)), round(vx, 4), round(vy, 4), round(vz, 4)))
    return out

def main():
    profile_map = {
        "15": DEVICE_15_INCH,
        "17": DEVICE_17_INCH,
        "15_inv": DEVICE_15_INCH_INV_Y,
    }

    parser = argparse.ArgumentParser(description="Render a character to an analog XY timeline.")
    parser.add_argument("char", help="The character to render (e.g., 'X').")
    parser.add_argument("--profile", default="15", choices=profile_map.keys(),
                        help="The device profile to use.")
    parser.add_argument("--out", help="CSV output path (default: <char>_<profile>.csv).")
    args = parser.parse_args()

    if len(args.char) != 1:
        print("Error: Please provide exactly one character.", file=sys.stderr)
        sys.exit(1)

    profile = profile_map[args.profile]

    try:
        # 1. Generate device-independent timeline
        em_timeline = render_char_to_em_timeline(args.char, profile['settle_us'])

        # 2. Map to hardware-specific voltages
        volt_timeline = map_timeline_to_volts(em_timeline, profile)

        # 3. Save to CSV
        out_path = args.out or f"{args.char}_{args.profile}.csv"
        with open(out_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["t_us", "Vx", "Vy", "Vz"])
            writer.writerows(volt_timeline)

        total_time_ms = (volt_timeline[-1][0] / 1000.0) if volt_timeline else 0.0
        print(f"Successfully rendered '{args.char}' using profile '{profile['name']}'.")
        print(f"Generated {len(volt_timeline)} samples over {total_time_ms:.2f} ms.")
        print(f"Output written to: {out_path}")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
