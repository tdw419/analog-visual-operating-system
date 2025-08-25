#!/usr/bin/env python3
# visual_python_mvp.py — Visual Python MVP (live edit → pixels → decode → exec → pixels)
import sys
import time
import math
from dataclasses import dataclass, field
from typing import Dict, List
from PIL import Image, ImageDraw, ImageStat
import tkinter as tk
from py2px import Px
from control_strip import draw_control, read_control
from visual_codec import draw_text, sample_text, CELL_W, CELL_H, COLS, ROWS

# Configuration
PIXEL_READ = True
W, H = 640, 360
GAP = 8
CTRL_H = 24
PANE_W = (W - GAP*3) // 2
PANE_H = (H - CTRL_H - GAP*3) // 2
FRAME_DIR = "out_vpy_mvp"

@dataclass
class VPState:
    pc: int = 0
    source_lines: List[str] = field(default_factory=lambda: ["1+2"])
    caret: tuple[int, int] = (0, 0)  # (row, col)
    last_result: str = ""

import ast

ALLOWED_NODES = {
    ast.Module, ast.Expr, ast.Assign, ast.BinOp, ast.UnaryOp,
    ast.Num, ast.Constant, ast.Name, ast.Load, ast.Store,
    ast.Call, ast.If, ast.For, ast.While, ast.Compare,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.arguments, ast.arg, ast.FunctionDef, ast.Return,
    ast.List, ast.Tuple, ast.Dict, ast.Str, ast.Attribute,
}

SAFE_GLOBALS = {
    "math": math,
    "range": range,
    "sum": sum,
    "len": len,
    "min": min,
    "max": max,
    "abs": abs,
    "pow": pow,
}

def safe_exec_multiline(lines: List[str]) -> str:
    code = "\n".join(lines)
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as e:
        return f"SyntaxErr: {e.msg}"

    for node in ast.walk(tree):
        if type(node) not in ALLOWED_NODES:
            return f"Disallowed: {type(node).__name__}"

    try:
        loc: Dict[str, object] = {}
        exec(compile(tree, "<vpy>", "exec"), {"__builtins__": {}}, {**SAFE_GLOBALS, **loc})
        # If last line is an expression, eval it for display
        try:
            last_expr = ast.parse(lines[-1], mode="eval")
            val = eval(compile(last_expr, "<vpy>", "eval"), {"__builtins__": {}}, {**SAFE_GLOBALS, **loc})
            return str(val)[:COLS]
        except SyntaxError:
            return ""
    except Exception as e:
        return f"Err: {str(e)[:COLS]}"

def draw_pane(px: Px, x: int, y: int, lines: List[str], color_fg="#FFFFFF", color_bg="#1E2330", caret=None):
    """Draw a text pane with optional caret."""
    for r, line in enumerate(lines[:ROWS]):
        draw_text(px._draw, x, y + r * CELL_H, line.ljust(COLS)[:COLS], color_fg, color_bg)
    if caret:
        cx, cy = x + caret[1] * CELL_W, y + caret[0] * CELL_H
        px.rect(cx, cy + CELL_H - 2, CELL_W, 2, "#00FF00")

def decode_pane(img: Image.Image, x: int, y: int, num_lines: int) -> List[str]:
    """Decode a text pane from pixel data."""
    return [sample_text(img, x, y + r * CELL_H).rstrip() for r in range(num_lines)]

def draw_heatmap(px: Px, x: int, y: int, truth: List[str], decoded: List[str]):
    """Visualize decoding errors as a heatmap."""
    max_rows = max(len(truth), len(decoded))
    for r in range(max_rows):
        t = (truth[r] if r < len(truth) else "").ljust(COLS)
        d = (decoded[r] if r < len(decoded) else "").ljust(COLS)
        for c in range(COLS):
            cx, cy = x + c * CELL_W, y + r * CELL_H
            color = "#002200" if t[c] == d[c] else "#220000"
            px.rect(cx, cy, CELL_W, CELL_H, color)

def draw_frame(px: Px, st: VPState):
    """Draw the entire frame with all panes."""
    px.clear("#0E0F14")
    # Pane coordinates
    ax, ay = GAP, CTRL_H + GAP  # A: Source (editable truth)
    bx, by = ax + PANE_W + GAP, ay  # B: Pixelated Source
    cx, cy = ax, ay + PANE_H + GAP  # C: Result
    dx, dy = bx, cy  # D: Heatmap
    # Labels
    px.text(ax, ay-12, "A: Source (edit)", 12, "#A0FFA0")
    px.text(bx, by-12, "B: Pixelated (decoded)", 12, "#9BB4FF")
    px.text(cx, cy-12, "C: Result", 12, "#FFD966")
    px.text(dx, dy-12, "D: Decode Heatmap", 12, "#FF8080")
    # Draw panes
    draw_pane(px, ax, ay, st.source_lines, color_fg="#FFFFFF", color_bg="#1A1F2B", caret=st.caret)
    draw_pane(px, bx, by, st.source_lines, color_fg="#FFFFFF", color_bg="#1E2330")
    draw_pane(px, cx, cy, [st.last_result], color_fg="#FFD966" if "Err" not in st.last_result else "#FF8080", color_bg="#1A1F2B")
    # Control strip
    draw_control(px._draw, {"SCREEN_ID": 100, "PC": st.pc, "MAILBOX_IN": 0, "MAILBOX_OUT": 0})

def decode(px: Px, st: VPState) -> Dict:
    """Decode the frame (control strip + pixelated code)."""
    img = px._img
    ctrl = read_control(img)
    if not ctrl.get("_crc_ok", False):
        ctrl["err"] = "crc"

    ax, ay = GAP, CTRL_H + GAP
    bx, by = ax + PANE_W + GAP, ay

    decoded_lines = decode_pane(img, bx, by, len(st.source_lines)) if PIXEL_READ else st.source_lines
    ctrl["code"] = "\n".join(decoded_lines)
    ctrl["_decoded_lines"] = decoded_lines
    return ctrl

def update(st: VPState, ctrl: Dict) -> VPState:
    """Update state based on decoded frame."""
    decoded_block = ctrl.get("_decoded_lines", [])
    result = safe_exec_multiline(decoded_block) if any(decoded_block) else ""
    return VPState(pc=st.pc + 1, source_lines=st.source_lines, caret=st.caret, last_result=result)

class Editor:
    """Handle live keyboard input."""
    def __init__(self, master, state: VPState):
        self.master = master
        self.state = state
        self.master.bind("<Key>", self.handle_key)

    def handle_key(self, event):
        ch = event.char
        r, c = self.state.caret
        line = self.state.source_lines[r]
        if ch.isprintable() and len(line) < COLS:
            self.state.source_lines[r] = line[:c] + ch + line[c:]
            self.state.caret = (r, min(c+1, COLS-1))
        elif event.keysym == "BackSpace" and c > 0:
            self.state.source_lines[r] = line[:c-1] + line[c:]
            self.state.caret = (r, c-1)
        elif event.keysym == "Left" and c > 0:
            self.state.caret = (r, c-1)
        elif event.keysym == "Right" and c < len(line):
            self.state.caret = (r, c+1)
        elif event.keysym == "Return":
            self.state.source_lines[r] = line[:COLS].strip()

def log_frame(st: VPState, ctrl: Dict, frame_idx: int):
    """Log frame data for replay and debugging, including forensic mismatch stats."""
    import json
    import os

    decoded_lines = ctrl.get("_decoded_lines", [])
    mismatches = []
    mismatch_count = 0
    max_rows = max(len(st.source_lines), len(decoded_lines))
    for r in range(max_rows):
        t_line = (st.source_lines[r] if r < len(st.source_lines) else "").ljust(COLS)
        d_line = (decoded_lines[r] if r < len(decoded_lines) else "").ljust(COLS)
        for c in range(COLS):
            if t_line[c] != d_line[c]:
                mismatch_count += 1
                mismatches.append({"row": r, "col": c, "expected": t_line[c], "got": d_line[c]})

    log = {
        "frame": frame_idx,
        "pc": st.pc,
        "source": st.source_lines,
        "decoded": decoded_lines,
        "result": st.last_result,
        "crc_ok": ctrl.get("_crc_ok", False),
        "decode_forensics": {
            "mismatch_count": mismatch_count,
            "mismatches": mismatches
        }
    }
    os.makedirs(FRAME_DIR, exist_ok=True)
    with open(f"{FRAME_DIR}/log_{frame_idx:06d}.json", "w") as f:
        json.dump(log, f, indent=2)

def run_visual_python_mvp(frames=5, out_dir=FRAME_DIR):
    """Run the Visual Python MVP (batch or live)."""
    print("Starting Visual Python MVP demo...")
    px = Px(W, H, 60, out_dir)
    st = VPState(source_lines=["1+2"], caret=(0, 0))

    if frames > 0:  # Batch mode
        # Pre-programmed code changes for batch mode
        code_changes = {2: "sum(range(5))", 4: "(3*7)+4"}

        for f in range(frames):
            print(f"--- Frame {f} ---")
            if f in code_changes:
                st.source_lines[0] = code_changes[f]
                st.caret = (0, len(st.source_lines[0]))

            ax, ay = GAP, CTRL_H + GAP
            bx, by = ax + PANE_W + GAP, ay
            dx, dy = bx, ay + PANE_H + GAP

            draw_frame(px, st)
            px.tick()
            ctrl = decode(px, st)
            assert ctrl.get("SCREEN_ID") == 100 and ctrl.get("_crc_ok", True), f"Frame {f} failed: {ctrl}"

            decoded_lines = ctrl["_decoded_lines"]
            if PIXEL_READ and decoded_lines != st.source_lines:
                draw_heatmap(px, dx, dy, st.source_lines, decoded_lines)

            st = update(st, ctrl)
            log_frame(st, ctrl, f)

    else:  # Live interactive loop
        root = tk.Tk()
        root.withdraw()  # Hide main window
        editor = Editor(root, st)

        def loop():
            draw_frame(px, st)
            # In live mode, py2px would need a way to display the image in a window
            # For now, we'll just save it to show the loop is working
            px._img.save(f"{out_dir}/live_frame.png")

            ctrl = decode(px, st)

            ax, ay = GAP, CTRL_H + GAP
            bx, by = ax + PANE_W + GAP, ay
            dx, dy = bx, ay + PANE_H + GAP

            if PIXEL_READ and ctrl["code"].strip() != st.source_lines[0].strip():
                draw_heatmap(px, dx, dy, st.source_lines, [ctrl["code"]])
            else:
                px.rect(dx, dy, PANE_W, PANE_H, "#112211") # Green overlay for success
            st = update(st, ctrl)
            log_frame(st, ctrl, st.pc)
            root.after(16, loop)  # ~60Hz

        print("Starting live mode... (Will save frames to out_vpy_mvp/live_frame.png)")
        loop()
        root.mainloop()


if __name__ == "__main__":
    # In batch mode, we need to ensure there are some multi-line edits to test
    # The scripted changes will be sufficient for this verification.
    run_visual_python_mvp(frames=5)
