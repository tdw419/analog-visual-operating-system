#!/usr/bin/env python3
# Source/DSL → Analog IR → timed (X,Y,R,G,B) signals + PPM preview + bytecode
# Usage examples:
#   python3 analog_compiler.py                    # uses inline SOURCE
#   python3 analog_compiler.py program.analog     # compile DSL file
#   python3 analog_compiler.py --disasm program.ab
# Outputs: frame.ppm, signals.csv, program.ab

from typing import List, Tuple, Iterable, Optional
import re, sys, struct, argparse, socket, time, json
from font_5x7 import glyph_for
from air import AIR, IROp, TextOp, RectOp, LineOp, CursorOp, MoveOp, BlankOp, air_to_json, pack_airb, unpack_airb

# ---------- Config ----------
WIDTH, HEIGHT = 160, 90
SCAN_DT_US = 1  # 1 µs per sample (demo)
MOVE_US_PER_PX = 0.1 # Cost to move the beam
GREEN = (0, 255, 0)
BLUE  = (100, 100, 255)
WHITE = (255, 255, 255)

# ---------- Types ----------
Color = Tuple[int,int,int]
IR = List[IROp] # Keep this alias for clarity

# ---------- Helpers ----------
HEX = re.compile(r'^#([0-9a-fA-F]{6})$')
def hex_rgb(s: str) -> Color:
    m = HEX.match(s.strip())
    if not m: raise ValueError(f"Bad color {s}")
    v = int(m.group(1), 16)
    return ((v>>16)&255, (v>>8)&255, v&255)

def parse_color_default(s: Optional[str], default: Color) -> Color:
    return hex_rgb(s) if s else default

# ---------- Front-end (parsers) ----------
def parse_pythonish(line: str, ir: IR):
    # print("HELLO") or print("X", x=16, y=20, color="#00FF00", scale=2)
    if line.startswith("print("):
        text = re.findall(r'print\("([^"]*)"', line)
        if not text: return
        x = int(re.findall(r'x\s*=\s*(\d+)', line)[0]) if 'x=' in line else 16
        y = int(re.findall(r'y\s*=\s*(\d+)', line)[0]) if 'y=' in line else 20
        scale = int(re.findall(r'scale\s*=\s*(\d+)', line)[0]) if 'scale=' in line else 2
        color = GREEN
        mcol = re.findall(r'color\s*=\s*"(#?[0-9a-fA-F]{6})"', line)
        if mcol: color = hex_rgb(mcol[0])
        ir.append(TextOp(text=text[0], x=x, y=y, color=color, scale=scale))
        return
    # rect(10,40,60,14,"#6464FF")
    if line.startswith("rect("):
        nums = re.findall(r'rect\(([^)]*)\)', line)[0].split(',')
        x,y,w,h = map(int, nums[:4])
        color = BLUE
        if len(nums) >= 5:
            color = hex_rgb(nums[4].strip().strip('"').strip("'"))
        ir.append(RectOp(x=x, y=y, w=w, h=h, color=color))
        return
    # line(10,10, 120,60, "#FFAA00")
    if line.startswith("line("):
        nums = re.findall(r'line\(([^)]*)\)', line)[0].split(',')
        x1,y1,x2,y2 = map(int, nums[:4])
        color = parse_color_default(nums[4].strip().strip('"').strip("'") if len(nums)>=5 else None, WHITE)
        ir.append(LineOp(x1=x1,y1=y1,x2=x2,y2=y2,color=color))
        return

def parse_dsl(line: str, ir: IR):
    # TEXT "HELLO" AT 16,20 COLOR #00FF00 [SCALE 2]
    m = re.match(r'^TEXT\s+"([^"]+)"\s+AT\s+(\d+)\s*,\s*(\d+)(?:\s+COLOR\s+(#?[0-9a-fA-F]{6}))?(?:\s+SCALE\s+(\d+))?$', line, re.I)
    if m:
        s,x,y,col,sc = m.groups()
        ir.append(TextOp(text=s, x=int(x), y=int(y), color=hex_rgb(col) if col else GREEN, scale=int(sc) if sc else 2))
        return

    # RECT 10,40,60,14 [COLOR #6464FF]
    m = re.match(r'^RECT\s+(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s+COLOR\s+(#?[0-9a-fA-F]{6}))?$', line, re.I)
    if m:
        x,y,w,h,col = m.groups()
        ir.append(RectOp(x=int(x), y=int(y), w=int(w), h=int(h), color=hex_rgb(col) if col else BLUE))
        return

    # LINE 10,10 -> 120,60 [COLOR #FFAA00]
    m = re.match(r'^LINE\s+(\d+)\s*,\s*(\d+)\s*->\s*(\d+)\s*,\s*(\d+)(?:\s+COLOR\s+(#?[0-9a-fA-F]{6}))?$', line, re.I)
    if m:
        x1,y1,x2,y2,col = m.groups()
        ir.append(LineOp(x1=int(x1),y1=int(y1),x2=int(x2),y2=int(y2), color=hex_rgb(col) if col else WHITE))
        return

    # CURSOR AT 16,20 [SIZE 2x14] [COLOR #FFFFFF] [BLINK 2]
    m = re.match(r'^CURSOR\s+AT\s+(\d+)\s*,\s*(\d+)(?:\s+SIZE\s+(\d+)x(\d+))?(?:\s+COLOR\s+(#?[0-9a-fA-F]{6}))?(?:\s+BLINK\s+(\d+))?$', line, re.I)
    if m:
        x,y,w,h,col,bhz = m.groups()
        ir.append(CursorOp(
            x=int(x), y=int(y),
            w=int(w) if w else 2, h=int(h) if h else 14,
            color=hex_rgb(col) if col else WHITE,
            blink_hz=int(bhz) if bhz else 0))
        return

    # MOVE TO 10,10
    m = re.match(r'^MOVE\s+TO\s+(\d+)\s*,\s*(\d+)$', line, re.I)
    if m:
        x, y = m.groups()
        ir.append(MoveOp(x=int(x), y=int(y)))
        return

    # BLANK ON/OFF
    m = re.match(r'^BLANK\s+(ON|OFF)$', line, re.I)
    if m:
        state = m.groups()[0].upper()
        ir.append(BlankOp(enable=(state == "ON")))
        return

    raise ValueError(f"Unrecognized line: {line}")

def compile_from_source(text: str) -> IR:
    ir: IR = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"): continue
        # try DSL first
        try:
            # A simple heuristic to decide which parser to use
            if line.split(' ',1)[0].upper() in {"TEXT","RECT","LINE","CURSOR", "MOVE", "BLANK"}:
                parse_dsl(line, ir); continue
        except ValueError:
            # If DSL fails, it might be pythonish. Or an error.
            pass
        # then pythonish helpers
        parse_pythonish(line, ir)
    return ir

# ---------- Back-end (signal emission) ----------
def text_pixels(op: TextOp) -> Iterable[Tuple[int,int]]:
    x0,y0,s = op.x, op.y, op.scale
    cx = x0
    for ch in op.text:
        g = glyph_for(ch)
        for gy,row in enumerate(g):
            for gx,c in enumerate(row):
                if c == '#':
                    for sy in range(s):
                        for sx in range(s):
                            yield (cx + gx*s + sx, y0 + gy*s + sy)
        cx += (5*s + 1*s)  # letter spacing

def rect_pixels(op: RectOp) -> Iterable[Tuple[int,int]]:
    for dy in range(op.h):
        py = op.y + dy
        for dx in range(op.w):
            px = op.x + dx
            yield (px, py)

def line_pixels(op: LineOp) -> Iterable[Tuple[int,int]]:
    x1,y1,x2,y2 = op.x1,op.y1,op.x2,op.y2
    dx = abs(x2-x1); sx = 1 if x1<x2 else -1
    dy = -abs(y2-y1); sy = 1 if y1<y2 else -1
    err = dx + dy
    x,y = x1,y1
    while True:
        yield (x,y)
        if x==x2 and y==y2: break
        e2 = 2*err
        if e2 >= dy: err += dy; x += sx
        if e2 <= dx: err += dx; y += sy

def cursor_pixels(op: CursorOp) -> Iterable[Tuple[int,int]]:
    for dy in range(op.h):
        py = op.y + dy
        for dx in range(op.w):
            px = op.x + dx
            yield (px, py)

def move_cost(x1: int, y1: int, x2: int, y2: int) -> int:
    """Estimates the time cost to move the beam between two points."""
    return int(MOVE_US_PER_PX * (abs(x2 - x1) + abs(y2 - y1)))

def rle_compress_signals(signals: List[Tuple[int, int, int, int, int, int, str]]) -> List[Tuple[int, int, int, int, int, int, str, int]]:
    """Compresses a list of raw signals using Run-Length Encoding."""
    if not signals:
        return []

    compressed = []
    run_start_signal = signals[0]
    run_length = 1

    for i in range(1, len(signals)):
        current_signal = signals[i]
        prev_signal = signals[i-1]

        # Check if the core signal properties are the same (color and op)
        # and if the position is adjacent (for horizontal runs)
        is_same_run = (
            current_signal[3:] == run_start_signal[3:] and
            current_signal[2] == run_start_signal[2] and # same row (y)
            current_signal[1] == prev_signal[1] + 1 # adjacent column (x)
        )

        if is_same_run:
            run_length += 1
        else:
            compressed.append((*run_start_signal, run_length))
            run_start_signal = current_signal
            run_length = 1

    # Add the last run
    compressed.append((*run_start_signal, run_length))

    return compressed

def generate_signals(ir: IR) -> List[Tuple[int, int, int, int, int, int, str, int]]:
    """
    Return list of (t_us, x, y, r, g, b, op_name, length)
    This version models beam movement, blanking, and applies RLE compression.
    """
    t = 0
    last_x, last_y = 0, 0
    beam_blanked = True
    raw_signals: List[Tuple[int, int, int, int, int, int, str]] = []

    # First, generate all raw signals with timestamps
    for op in ir:
        op_x = op.x if hasattr(op, 'x') else op.x1 if hasattr(op, 'x1') else last_x
        op_y = op.y if hasattr(op, 'y') else op.y1 if hasattr(op, 'y1') else last_y

        if op_x != last_x or op_y != last_y:
            if not beam_blanked:
                raw_signals.append((t, last_x, last_y, 0, 0, 0, "BLANK_ON")); t += 1
                beam_blanked = True

            cost = move_cost(last_x, last_y, op_x, op_y)
            raw_signals.append((t, op_x, op_y, 0, 0, 0, "MOVE")); t += cost
            last_x, last_y = op_x, op_y

        if isinstance(op, (TextOp, RectOp, LineOp, CursorOp)):
            if beam_blanked:
                raw_signals.append((t, last_x, last_y, 0, 0, 0, "BLANK_OFF")); t += 1
                beam_blanked = False

        if isinstance(op, TextOp):
            for (x,y) in text_pixels(op):
                raw_signals.append((t, x, y, *op.color, "TEXT")); t += SCAN_DT_US
                last_x, last_y = x, y
        elif isinstance(op, RectOp):
             for (x,y) in rect_pixels(op):
                raw_signals.append((t, x, y, *op.color, "RECT")); t += SCAN_DT_US
                last_x, last_y = x, y
        elif isinstance(op, LineOp):
            for (x,y) in line_pixels(op):
                raw_signals.append((t, x, y, *op.color, "LINE")); t += SCAN_DT_US
                last_x, last_y = x, y
        elif isinstance(op, CursorOp):
            for (x,y) in cursor_pixels(op):
                raw_signals.append((t, x, y, *op.color, "CURSOR")); t += SCAN_DT_US
                last_x, last_y = x, y
        elif isinstance(op, MoveOp):
             last_x, last_y = op.x, op.y
        elif isinstance(op, BlankOp):
            if op.enable != beam_blanked:
                op_name = "BLANK_ON" if op.enable else "BLANK_OFF"
                raw_signals.append((t, last_x, last_y, 0, 0, 0, op_name)); t += 1
                beam_blanked = op.enable

    # Finally, compress the raw signals
    return rle_compress_signals(raw_signals)

# ---------- Preview image (PPM) ----------
def write_ppm(path: str, ir: IR):
    frame = [[[0,0,0] for _ in range(WIDTH)] for _ in range(HEIGHT)]
    for op in ir:
        if isinstance(op, TextOp):
            for (x,y) in text_pixels(op):
                if 0 <= x < WIDTH and 0 <= y < HEIGHT: frame[y][x] = list(op.color)
        elif isinstance(op, RectOp):
            for (x,y) in rect_pixels(op):
                if 0 <= x < WIDTH and 0 <= y < HEIGHT: frame[y][x] = list(op.color)
        elif isinstance(op, LineOp):
            for (x,y) in line_pixels(op):
                if 0 <= x < WIDTH and 0 <= y < HEIGHT: frame[y][x] = list(op.color)
        elif isinstance(op, CursorOp):
            for (x,y) in cursor_pixels(op):
                if 0 <= x < WIDTH and 0 <= y < HEIGHT: frame[y][x] = list(op.color)
    with open(path, "w") as f:
        f.write(f"P3\n{WIDTH} {HEIGHT}\n255\n")
        for row in frame:
            f.write(" ".join(f"{r} {g} {b}" for r,g,b in row) + "\n")

def write_csv(path: str, signals: List[Tuple[int, int, int, int, int, int, str, int]]):
    with open(path, "w") as f:
        f.write("t_us,x,y,r,g,b,op,length\n")
        for t,x,y,r,g,b,op,length in signals:
            f.write(f"{t},{x},{y},{r},{g},{b},{op},{length}\n")

import socket

# ---------- Bytecode (emit + disasm) ----------
OP_TEXT, OP_RECT, OP_LINE, OP_CURSOR, OP_MOVE, OP_BLANK, OP_END = 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0xFF

def write_bytecode(path: str, ir: IR):
    ops = []
    for op in ir:
        if isinstance(op, TextOp):
            text_bytes = op.text.encode('ascii', 'ignore')[:255]
            ops.append(struct.pack('<BHHBBBB', OP_TEXT, op.x, op.y, *op.color, op.scale) + struct.pack('<B', len(text_bytes)) + text_bytes)
        elif isinstance(op, RectOp):
            ops.append(struct.pack('<BHHHHBBB', OP_RECT, op.x, op.y, op.w, op.h, *op.color))
        elif isinstance(op, LineOp):
            ops.append(struct.pack('<BHHHHBBB', OP_LINE, op.x1, op.y1, op.x2, op.y2, *op.color))
        elif isinstance(op, CursorOp):
            ops.append(struct.pack('<BHHBBBBB', OP_CURSOR, op.x, op.y, op.w, op.h, *op.color, op.blink_hz))
        elif isinstance(op, MoveOp):
            ops.append(struct.pack('<BHH', OP_MOVE, op.x, op.y))
        elif isinstance(op, BlankOp):
            ops.append(struct.pack('<BB', OP_BLANK, 1 if op.enable else 0))

    body = b''.join(ops) + struct.pack('<B', OP_END)
    header = b'ANLG' + struct.pack('<BHHHHI', 1, WIDTH, HEIGHT, SCAN_DT_US, 0, len(ops))
    # (the extra u16 reserved is 0 for future use)
    with open(path, 'wb') as f:
        f.write(header + body)

def disasm(path: str):
    with open(path, 'rb') as f:
        data = f.read()
    if data[:4] != b'ANLG': raise SystemExit("Bad magic")
    ver = data[4]
    width, height, dt, _reserved, count = struct.unpack('<HHHHI', data[5:17])
    print(f"ANLG v{ver} {width}x{height} dt={dt}us ops={count}")
    i = 17  # header size
    idx = 0
    while i < len(data):
        op_code = data[i]; i += 1
        if op_code == OP_END: print("END"); break
        idx += 1
        if op_code == OP_TEXT:
            x,y,r,g,b,scale = struct.unpack('<HHBBBB', data[i:i+8]); i += 8
            ln = data[i]; i += 1
            s = data[i:i+ln].decode('ascii','ignore'); i += ln
            print(f"{idx:03d}: TEXT  x={x} y={y} col=({r},{g},{b}) scale={scale} '{s}'")
        elif op_code == OP_RECT:
            x,y,w,h,r,g,b = struct.unpack('<HHHHBBB', data[i:i+11]); i += 11
            print(f"{idx:03d}: RECT  x={x} y={y} w={w} h={h} col=({r},{g},{b})")
        elif op_code == OP_LINE:
            x1,y1,x2,y2,r,g,b = struct.unpack('<HHHHBBB', data[i:i+11]); i += 11
            print(f"{idx:03d}: LINE  ({x1},{y1})->({x2},{y2}) col=({r},{g},{b})")
        elif op_code == OP_CURSOR:
            x,y,w,h,r,g,b,blink = struct.unpack('<HHBBBBB', data[i:i+9]); i += 9
            print(f"{idx:03d}: CURSOR x={x} y={y} size={w}x{h} col=({r},{g},{b}) blink={blink}Hz")
        elif op_code == OP_MOVE:
            x,y = struct.unpack('<HH', data[i:i+4]); i += 4
            print(f"{idx:03d}: MOVE to ({x},{y})")
        elif op_code == OP_BLANK:
            state = struct.unpack('<B', data[i:i+1])[0]; i += 1
            print(f"{idx:03d}: BLANK {'ON' if state else 'OFF'}")
        else:
            raise SystemExit(f"Unknown opcode {op_code:#x} at {i-1}")

def stream_to_runtime(ir: IR, host: str = "localhost", port: int = 12345):
    """Connects to the runtime and streams AIR commands."""
    print(f"\nConnecting to runtime at {host}:{port}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            print("Connection successful. Streaming commands...")
            for op in ir:
                if isinstance(op, TextOp):
                    # Format as DSL for the runtime
                    color_str = f"#{op.color[0]:02x}{op.color[1]:02x}{op.color[2]:02x}"
                    cmd = f'TEXT "{op.text}" AT {op.x},{op.y} COLOR {color_str} SCALE {op.scale}\n'
                    s.sendall(cmd.encode('utf-8'))
                elif isinstance(op, RectOp):
                    color_str = f"#{op.color[0]:02x}{op.color[1]:02x}{op.color[2]:02x}"
                    cmd = f'RECT {op.x},{op.y},{op.w},{op.h} COLOR {color_str}\n'
                    s.sendall(cmd.encode('utf-8'))
                # Add other op types here...
                time.sleep(0.01) # Small delay to allow runtime to process
            print("Streaming complete.")
    except ConnectionRefusedError:
        print("Error: Connection refused. Is the analog_runtime.py server running?")
    except Exception as e:
        print(f"An error occurred during streaming: {e}")

# ---------- Demo ----------
SOURCE = '''
# Two equivalent styles + new ops:
print("HELLO", x=16, y=20, color="#00FF00")
rect(10,40,60,14,"#6464FF")
line(10,10, 120,60, "#FFAA00")

# DSL flavor
TEXT "PRESS X" AT 16,50 COLOR #00FF00 SCALE 2
LINE 16,64 -> 140,64 COLOR #FFFFFF
CURSOR AT 76,20 SIZE 2x14 COLOR #FFFFFF BLINK 0

# “press X” experiment — shows the exact analog points emitted for the glyph
print("X", x=16, y=70, color="#00FF00")
'''

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs='?', help="Optional .analog source file")
    ap.add_argument("--disasm", help="Disassemble a .ab bytecode file and exit")
    ap.add_argument("--no-stream", action="store_true", help="Disable TCP streaming to runtime")
    args = ap.parse_args()

    if args.disasm:
        disasm(args.disasm); return

    src = SOURCE
    if args.input:
        with open(args.input, 'r') as f: src = f.read()

    ir = compile_from_source(src)
    signals = generate_signals(ir)
    write_csv("signals.csv", signals)
    write_ppm("frame.ppm", ir)
    write_bytecode("program.ab", ir)

    print(f"OK: {len(ir)} ops → {len(signals)} signal samples")
    print("Wrote frame.ppm, signals.csv, program.ab")

    if not args.no_stream:
        stream_to_runtime(ir)

if __name__ == "__main__":
    main()
