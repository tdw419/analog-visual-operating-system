#!/usr/bin/env python3
# visual_python_panes.py — Visual Python MVP with live edit → pixels → decode → exec → pixels

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from collections import deque

# Third-party
from PIL import Image

# Local deps you already have
from py2px import Px
from control_strip import draw_control, read_control
from visual_codec import draw_text, sample_text, CELL_W, CELL_H, COLS, ROWS

# Optional: keyboard input (for live mode)
import tkinter as tk


# ----- Configuration ---------------------------------------------------------

# Screen and layout
W, H = 640, 360
GAP = 8
CTRL_H = 24
PANE_W = (W - GAP * 3) // 2
PANE_H = (H - CTRL_H - GAP * 3) // 2

# Pane anchors (top-left corners)
AX, AY = GAP, CTRL_H + GAP                    # Pane A: Source (truth, editable)
BX, BY = AX + PANE_W + GAP, AY                # Pane B: Pixelated (decoded)
CX, CY = AX, AY + PANE_H + GAP                # Pane C: Result (pixels)
DX, DY = BX, BY + PANE_H + GAP                # Pane D: Decode Heatmap

# Behavior
PIXEL_READ = True       # Decode from pixels each tick (True for MVP)
LOG_DIR = "out_vpy_mvp" # Frame PNGs + logs (if using Px out_dir) will land here


# ----- State ----------------------------------------------------------------

@dataclass
class VPState:
    pc: int = 0
    source_lines: List[str] = field(default_factory=lambda: [""])
    caret: Tuple[int, int] = (0, 0)  # (row, col) in Source pane
    last_result: str = ""            # Rendered to Pane C

    # NEW: refresh-sequencing + temporal ECC
    seq_out: int = 0             # what we’re drawing this frame (0/1)
    last_seq_seen: int = -1      # what we’ve already processed
    decode_hist: deque[list[str]] = field(default_factory=lambda: deque(maxlen=3))

    # Internal helpers (not persisted)
    def current_line(self) -> str:
        return self.source_lines[self.caret[0]]

    def set_current_line(self, new_text: str) -> None:
        r, _ = self.caret
        self.source_lines[r] = new_text[:COLS]


# ----- Safe execution --------------------------------------------------------

def _pad_to(s: str, n: int) -> str:
    return (s + " " * n)[:n]

def vote3(blocks: list[list[str]], rows: int, cols: int) -> list[str]:
    """Per-cell majority from up to 3 decoded blocks; tie -> newest wins."""
    if not blocks:
        return [""]
    # Right-align lengths
    B = []
    for b in blocks:
        rows_here = max(rows, len(b))
        B.append([_pad_to(b[r] if r < len(b) else "", cols) for r in range(rows_here)])
    rows_final = max(len(b) for b in B)
    out: list[str] = []
    for r in range(rows_final):
        row_chars = []
        for c in range(cols):
            # newest first so ties prefer newest
            cands = [B[k][r][c] if r < len(B[k]) else " " for k in reversed(range(len(B)))]
            # simple majority
            if len(cands) == 1:
                ch = cands[0]
            elif len(cands) == 2:
                ch = cands[0] if cands[0] == cands[1] else cands[0]  # tie->newest
            else:
                ch = (cands[0] if cands[0] == cands[1] or cands[0] == cands[2]
                      else (cands[1] if cands[1] == cands[2] else cands[0]))
            row_chars.append(ch)
        out.append("".join(row_chars).rstrip())
    return out[:rows]

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

class SafeEvaluator:
    def __init__(self):
        self.globals = SAFE_GLOBALS

    def eval(self, lines: List[str]) -> str:
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
            exec(compile(tree, "<vpy>", "exec"), {"__builtins__": {}}, {**self.globals, **loc})
            # If last line is an expression, eval it for display
            if lines and lines[-1].strip():
                try:
                    last_expr = ast.parse(lines[-1], mode="eval")
                    val = eval(compile(last_expr, "<vpy>", "eval"), {"__builtins__": {}}, {**self.globals, **loc})
                    return str(val)[:COLS]
                except SyntaxError:
                    return "" # Last line was a statement, not an expression
            return ""
        except Exception as e:
            return f"Err: {str(e)[:COLS]}"


# ----- Drawing helpers -------------------------------------------------------

def draw_text_block(px: Px, x: int, y: int, lines: List[str], fg="#FFFFFF", bg="#1A1F2B") -> None:
    for r, line in enumerate(lines[:ROWS]):
        draw_text(px._draw, x, y + r * CELL_H, line.ljust(COLS)[:COLS], fg, bg)

def draw_caret(px: Px, x: int, y: int, caret: Tuple[int, int]) -> None:
    cr, cc = caret
    cx, cy = x + cc * CELL_W, y + cr * CELL_H
    px.rect(cx, cy + CELL_H - 2, CELL_W, 2, "#00FF00")

def draw_labels(px: Px) -> None:
    px.text(AX, AY - 12, "A: Source (edit)", 12, "#A0FFA0")
    px.text(BX, BY - 12, "B: Pixelated (decoded)", 12, "#9BB4FF")
    px.text(CX, CY - 12, "C: Result", 12, "#FFD966")
    px.text(DX, DY - 12, "D: Decode Heatmap", 12, "#FF8080")

def draw_heatmap(px: Px, truth: List[str], decoded: List[str]) -> None:
    # Green cell = match, red = mismatch
    for r in range(ROWS):
        t = (truth[r] if r < len(truth) else "").ljust(COLS)
        d = (decoded[r] if r < len(decoded) else "").ljust(COLS)
        for c in range(COLS):
            cx, cy = DX + c * CELL_W, DY + r * CELL_H
            color = "#002200" if t[c] == d[c] else "#220000"
            px.rect(cx, cy, CELL_W, CELL_H, color)


# ----- Frame lifecycle -------------------------------------------------------

def draw_frame(px: Px, st: VPState) -> None:
    # Background
    px.clear("#0E0F14")

    # Panes
    draw_labels(px)

    # A: Source (truth)
    draw_text_block(px, AX, AY, st.source_lines, fg="#FFFFFF", bg="#1A1F2B")
    draw_caret(px, AX, AY, st.caret)

    # B: Pixelated (this is what we decode)
    draw_text_block(px, BX, BY, st.source_lines, fg="#FFFFFF", bg="#1E2330")

    # C: Result
    result_fg = "#FFD966" if not st.last_result.startswith("Err:") else "#FF8080"
    draw_text_block(px, CX, CY, [st.last_result], fg=result_fg, bg="#1A1F2B")

    # Control strip (CRC is computed inside draw_control)
    draw_control(px._draw, {
        "SCREEN_ID": 100,
        "PC": st.pc,
        "SEQ": st.seq_out & 1,       # parity for this presented frame
        "ACK": st.last_seq_seen & 1, # receiver’s acknowledgement
        "MAILBOX_IN": 0,
        "MAILBOX_OUT": 0,
    })


def decode_and_step(px: Px, st: VPState) -> Tuple[VPState, Dict]:
    img = px._img
    ctrl = read_control(img)
    seq_in = int(ctrl.get("SEQ", 0))

    # If we already processed this frame’s payload, do nothing.
    if seq_in == (st.last_seq_seen & 1):
        # still flip seq for the next draw to keep time
        st.seq_out ^= 1
        return st, ctrl # Return early with the original state and the new ctrl info

    # Fresh frame boundary -> read pixelated code (Pane B)
    decoded_lines = []
    for r in range(len(st.source_lines)):
        y = BY + r * CELL_H
        decoded_lines.append(sample_text(img, BX, y).rstrip())

    # Temporal ECC: vote across {this, last1, last2}
    st.decode_hist.append(decoded_lines)
    voted = vote3(list(st.decode_hist), rows=len(st.source_lines), cols=COLS)
    ctrl["_decoded_lines"] = voted # Pass voted result for heatmap

    # Update state for NEXT frame (execution happens in the main loop)
    new_st = VPState(
        pc=st.pc + 1,
        source_lines=st.source_lines,
        caret=st.caret,
        last_result=st.last_result, # Carry over old result for now
        seq_out = st.seq_out ^ 1, # toggle for next presentation
        last_seq_seen = seq_in, # ACK will reflect this in the next draw
        decode_hist=st.decode_hist
    )
    return new_st, ctrl


# ----- Logging (optional) ----------------------------------------------------

def log_frame_json(st: VPState, ctrl: Dict, frame_idx: int) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    payload = {
        "frame": frame_idx,
        "pc": st.pc,
        "source": st.source_lines,
        "decoded": ctrl.get("code", ""),
        "result": st.last_result,
        "crc_ok": ctrl.get("_crc_ok", False),
    }
    with open(os.path.join(LOG_DIR, f"log_{frame_idx:06d}.json"), "w") as f:
        json.dump(payload, f, indent=2)


# ----- Keyboard editor -------------------------------------------------------

class Editor:
    """
    Minimal editor for Pane A (single line MVP):
    - Insert printable characters
    - Backspace delete
    - Arrow left/right
    - Enter trims line (acts like "commit" visually)
    """
    def __init__(self, root: tk.Tk, st: VPState) -> None:
        self.root = root
        self.st = st
        self.root.title("Visual Python — Input")
        self.root.geometry("320x80+30+30")
        self.root.attributes("-topmost", True)
        self.root.bind("<Key>", self.on_key)
        tk.Label(root, text="Type here. ESC to clear.", font=("Consolas", 10)).pack()

    def on_key(self, ev: tk.Event) -> None:
        ch = ev.char or ""
        r, c = self.st.caret
        line = self.st.current_line()

        if ev.keysym == "Escape":
            self.st.source_lines = [""]
            self.st.caret = (0, 0)
            return

        if ch.isprintable():
            self.st.set_current_line(line[:c] + ch + line[c:])
            self.st.caret = (r, min(c + 1, COLS - 1))
        elif ev.keysym == "BackSpace":
            if c > 0:
                self.st.set_current_line(line[:c - 1] + line[c:])
                self.st.caret = (r, c - 1)
            elif r > 0:
                prev_len = len(self.st.source_lines[r - 1])
                self.st.source_lines[r - 1] += line
                del self.st.source_lines[r]
                self.st.caret = (r - 1, prev_len)
        elif ev.keysym == "Return":
            new_line = line[c:]
            self.st.set_current_line(line[:c])
            self.st.source_lines.insert(r + 1, new_line)
            self.st.caret = (r + 1, 0)
        elif ev.keysym == "Left":
            if c > 0:
                self.st.caret = (r, c - 1)
            elif r > 0:
                self.st.caret = (r - 1, len(self.st.source_lines[r - 1]))
        elif ev.keysym == "Right":
            if c < len(line):
                self.st.caret = (r, c + 1)
            elif r < len(self.st.source_lines) - 1:
                self.st.caret = (r + 1, 0)
        elif ev.keysym == "Up" and r > 0:
            self.st.caret = (r - 1, min(c, len(self.st.source_lines[r - 1])))
        elif ev.keysym == "Down" and r < len(self.st.source_lines) - 1:
            self.st.caret = (r + 1, min(c, len(self.st.source_lines[r + 1])))


# ----- Main loops ------------------------------------------------------------

def run_batch(frames: int = 90, out_dir: str = LOG_DIR) -> None:
    """
    Batch mode:
    - Renders frames to PNGs (via Px out_dir)
    - Logs JSON per frame
    - Performs two code edits at f=40 and f=80 to demonstrate round-trip
    """
    px = Px(W, H, fps=60, out_dir=out_dir)
    st = VPState(source_lines=["1+2"], caret=(0, 0))
    evaluator = SafeEvaluator()

    scripted_changes = {
        40: "sum(range(5))",
        80: "(3*7)+4",
    }

    for f in range(frames):
        # scripted edits to prove decode/execute/pixels loop
        if f in scripted_changes:
            st.set_current_line(scripted_changes[f])
            st.caret = (0, len(st.current_line()))

        draw_frame(px, st)
        px.tick()

        new_st, ctrl = decode_and_step(px, st)
        st = new_st
        st.last_result = evaluator.eval(st.source_lines) if any("".join(st.source_lines)) else ""


        # Decode heatmap (Pane D)
        decoded_lines = ctrl.get("_decoded_lines", [])
        if decoded_lines != st.source_lines:
            draw_heatmap(px, st.source_lines, decoded_lines)

        log_frame_json(st, ctrl, f)


def run_live(out_dir: str | None = None) -> None:
    """
    Live interactive mode:
    - Captures keyboard input from a small Tk window
    - Renders frames each ~16ms to Px
    - If out_dir is set, frames will be saved too (optional)
    """
    root = tk.Tk()
    px = Px(W, H, fps=60, out_dir=out_dir)
    st = VPState(source_lines=["1+2"], caret=(0, 0))
    editor = Editor(root, st)

    def loop():
        draw_frame(px, st)
        px.tick()

        new_st, ctrl = decode_and_step(px, st)
        st = new_st
        st.last_result = evaluator.eval(st.source_lines) if any("".join(st.source_lines)) else ""

        # We won't assert CRC in live mode, but we can surface mismatch via heatmap
        decoded_lines = ctrl.get("_decoded_lines", [])
        if decoded_lines and decoded_lines != st.source_lines:
            draw_heatmap(px, st.source_lines, decoded_lines)

        # Next tick
        root.after(16, loop)

    loop()
    root.mainloop()


# ----- Entrypoint ------------------------------------------------------------

if __name__ == "__main__":
    run_batch(frames=5)
