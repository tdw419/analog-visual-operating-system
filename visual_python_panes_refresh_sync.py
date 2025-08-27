#!/usr/bin/env python3
# visual_python_panes_refresh_sync.py — Visual Python MVP with refresh-synchronous updates and temporal ECC
import sys
import time
import math
import ast
import json
import os
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from PIL import Image, ImageDraw, ImageStat, ImageTk, ImageFilter
import tkinter as tk
from py2px import Px
from control_strip import draw_control, read_control
from visual_codec import draw_text, sample_text, CELL_W, CELL_H, COLS, ROWS

# Configuration
PIXEL_READ = True  # Decode from pixels only
W, H = 640, 360
GAP = 8
CTRL_H = 24
PANE_W = (W - GAP * 3) // 2
PANE_H = (H - CTRL_H - GAP * 3) // 2
FRAME_DIR = "out_vpy_refresh_sync"

# Pane coordinates (global for access by helpers)
AX, AY = GAP, CTRL_H + GAP
BX, BY = AX + PANE_W + GAP, AY
CX, CY = AX, AY + PANE_H + GAP
DX, DY = BX, CY

@dataclass
class VPState:
    pc: int = 0
    source_lines: List[str] = field(default_factory=lambda: [""])
    caret: Tuple[int, int] = (0, 0)  # (row, col)
    last_result: str = ""

    # NEW: refresh-sequencing + temporal ECC
    seq_out: int = 0
    last_seq_seen: int = -1
    decode_hist: deque[List[str]] = field(default_factory=lambda: deque(maxlen=3))

    def current_line(self) -> str:
        return self.source_lines[self.caret[0]] if self.source_lines else ""

    def set_current_line(self, new_text: str) -> None:
        r = self.caret[0]
        if r < len(self.source_lines):
            self.source_lines[r] = new_text[:COLS]
        else:
            self.source_lines.append(new_text[:COLS])

class SafeEvaluator:
    """Safely evaluate Python AST with whitelisted operations."""
    ALLOWED_NODES = {
        ast.Module, ast.Expr, ast.Assign, ast.BinOp, ast.UnaryOp,
        ast.Num, ast.Constant, ast.Name, ast.Load, ast.Store,
        ast.Call, ast.If, ast.For, ast.Compare,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
        ast.List, ast.Tuple, ast.NameConstant
    }
    ALLOWED_NAMES = {
        "range", "sum", "len", "min", "max", "abs", "pow",
        "sin", "cos", "tan", "sqrt", "log", "exp", "floor", "ceil", "pi", "e", "tau"
    }

    def __init__(self):
        self.globals = {
            "range": range, "sum": sum, "len": len,
            "min": min, "max": max, "abs": abs, "pow": pow,
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "sqrt": math.sqrt, "log": math.log, "exp": math.exp,
            "floor": math.floor, "ceil": math.ceil,
            "pi": math.pi, "e": math.e, "tau": math.tau,
            "__builtins__": {}
        }

    def check_node(self, node):
        if type(node) not in self.ALLOWED_NODES:
            raise ValueError(f"Unsupported node: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in self.ALLOWED_NAMES:
            raise ValueError(f"Unsupported name: {node.id}")
        for child in ast.walk(node):
            if type(child) not in self.ALLOWED_NODES:
                raise ValueError(f"Unsupported child node: {type(child).__name__}")
        return True

    def eval(self, code: List[str]) -> str:
        code_str = "\n".join(code)
        if not code_str.strip(): return ""
        try:
            tree = ast.parse(code_str)
            self.check_node(tree)
            # Wrap in parentheses to evaluate multi-line expressions
            eval_code = compile(f"({code_str})", "<vpy>", "eval")
            result = eval(eval_code, self.globals)
            return str(result)[:COLS-5]
        except Exception as e:
            return f"Err: {str(e)[:COLS-5]}"

# -------- color palette for machine tiles (from demo) --------
PALETTE = {
    "0":"#2dd4bf","1":"#22c55e","2":"#84cc16","3":"#eab308","4":"#f59e0b",
    "5":"#f97316","6":"#ef4444","7":"#ec4899","8":"#a855f7","9":"#3b82f6",
    "+":"#fb923c","-":"#f43f5e","*":"#8b5cf6","/":"#06b6d4","(":"#94a3b8",")":"#94a3b8",
    " ":"#0f172a"
}
def char_color(ch: str) -> str:
    return PALETTE.get(ch, "#64748b")  # default slate if unknown

def _pad_to(s: str, n: int) -> str:
    return (s + " " * n)[:n]

def vote3(blocks: list[list[str]], rows: int, cols: int) -> list[str]:
    """Per-cell majority from up to 3 decoded blocks; tie -> newest wins."""
    if not blocks:
        return [""]
    B = []
    for b in blocks:
        rows_here = max(rows, len(b))
        B.append([_pad_to(b[r] if r < len(b) else "", cols) for r in range(rows_here)])
    rows_final = max(len(b) for b in B)
    out: list[str] = []
    for r in range(rows_final):
        row_chars = []
        for c in range(cols):
            cands = [B[k][r][c] if r < len(B[k]) else " " for k in reversed(range(len(B)))]
            if len(cands) == 1:
                ch = cands[0]
            elif len(cands) == 2:
                ch = cands[0] if cands[0] == cands[1] else cands[0]
            else:
                ch = (cands[0] if cands[0] == cands[1] or cands[0] == cands[2]
                      else (cands[1] if cands[1] == cands[2] else cands[0]))
            row_chars.append(ch)
        out.append("".join(row_chars).rstrip())
    return out[:rows]

def draw_pane(px: Px, x: int, y: int, lines: List[str], color_fg="#FFFFFF", color_bg="#1E2330", caret=None):
    for r, line in enumerate(lines[:ROWS]):
        draw_text(px._draw, x, y + r * CELL_H, line.ljust(COLS)[:COLS], color_fg, color_bg)
    if caret and (int(time.time() * 2) % 2):
        cx, cy = x + caret[1] * CELL_W, y + caret[0] * CELL_H
        px.rect(cx, cy + CELL_H - 2, CELL_W, 2, "#00FF00")

def draw_heatmap(px: Px, x: int, y: int, truth: List[str], decoded: List[str]) -> List:
    # This function is kept for verification but not displayed in the 4-pane demo layout
    mismatches = []
    max_rows = max(len(truth), len(decoded))
    for r in range(max_rows):
        t = (truth[r] if r < len(truth) else "").ljust(COLS)
        d = (decoded[r] if r < len(decoded) else "").ljust(COLS)
        row_mismatches = []
        for c in range(COLS):
            cx, cy = x + c * CELL_W, y + r * CELL_H
            color = "#002200" if t[c] == d[c] else "#220000"
            px.rect(cx, cy, CELL_W, CELL_H, color)
            if t[c] != d[c]:
                row_mismatches.append((c, t[c], d[c]))
        mismatches.append(row_mismatches)
    return mismatches

def draw_color_tiles(px: Px, x: int, y: int, w: int, h: int, text: str):
    """Draws the machine-readable color tiles in a pane."""
    tiles = list(text)
    if not tiles: return
    tile_size = min(48, (w - 40) // max(3, len(tiles)))
    tx0 = x + (w - tile_size * len(tiles)) // 2
    ty0 = y + (h - tile_size) // 2
    for i, ch in enumerate(tiles):
        tile_x = tx0 + i * tile_size
        tile_y = ty0
        c = char_color(ch)
        px.rect(tile_x, tile_y, tile_size - 2, tile_size - 2, c)

def draw_compiler_pane(px: Px, x: int, y: int, source_text: str, result_text: str):
    """Draws the compiler/result pane."""
    if "Err" in result_text:
        line = f"Err: Could not evaluate"
        color = "#f87171"
    else:
        line = f"{source_text} = {result_text}"
        color = "#facc15"

    px.text(x + 20, y + 20, "Compiling color tiles...", 12, "#94a3b8")
    px.text(x + 20, y + 40, "Interpreting expression...", 12, "#94a3b8")
    px.text(x + 20, y + 80, line, 24, color)

def draw_frame(px: Px, st: VPState):
    px.clear("#0E0F14")
    px.text(AX, AY-12, "A: Source (edit)", 12, "#A0FFA0")
    px.text(BX, BY-12, "B: Pixelated (decoded)", 12, "#9BB4FF")
    px.text(CX, CY-12, "C: Color Tiles (machine readable)", 12, "#FFD966")
    px.text(DX, DY-12, "D: Compiler / Result", 12, "#FF8080")
    draw_pane(px, AX, AY, st.source_lines, color_fg="#FFFFFF", color_bg="#1A1F2B", caret=st.caret)
    draw_pane(px, BX, BY, st.source_lines, color_fg="#FFFFFF", color_bg="#1E2330")
    
    # Pane C: Color Tiles
    source_text_for_tiles = " ".join(st.source_lines)
    draw_color_tiles(px, CX, CY, PANE_W, PANE_H, source_text_for_tiles)

    # Pane D: Compiler / Result
    draw_compiler_pane(px, DX, DY, source_text_for_tiles, st.last_result)

    draw_control(px._draw, {
        "SCREEN_ID": 100, "PC": st.pc,
        "SEQ": st.seq_out & 1,
        "ACK": st.last_seq_seen & 1,
        "MAILBOX_IN": 0, "MAILBOX_OUT": 0,
    })

def decode_and_step(px: Px, st: VPState, evaluator: SafeEvaluator) -> Tuple[VPState, List[str], Dict]:
    img = px._img
    ctrl = read_control(img)
    seq_in = int(ctrl.get("SEQ", 0))

    if seq_in == (st.last_seq_seen & 1):
        st.seq_out ^= 1
        return st, [], ctrl
    
    decoded_lines = [sample_text(img, BX, BY + r * CELL_H).rstrip() for r in range(len(st.source_lines))]
    ctrl["_decoded_lines"] = decoded_lines

    st.decode_hist.append(decoded_lines)
    voted = vote3(list(st.decode_hist), rows=len(st.source_lines), cols=COLS)

    result = evaluator.eval(voted)

    st.last_result = result
    st.pc += 1
    st.last_seq_seen = seq_in
    st.seq_out ^= 1
    return st, voted, ctrl

class Editor:
    def __init__(self, master, state: VPState):
        self.master = master
        self.state = state
        self.master.bind("<Key>", self.handle_key)

    def handle_key(self, event):
        ch, ks = event.char, event.keysym
        r, c = self.state.caret
        lines = self.state.source_lines
        line = self.state.current_line()

        if ks == "Escape": self.state.source_lines, self.state.caret = [""], (0, 0)
        elif ks == "BackSpace":
            if c > 0: self.state.set_current_line(line[:c-1] + line[c:]); self.state.caret = (r, c-1)
            elif r > 0:
                prev_len = len(lines[r-1])
                lines[r-1] += line
                del lines[r]
                self.state.caret = (r-1, prev_len)
        elif ks in ("Return", "KP_Enter") and r < ROWS - 1:
            lines.insert(r + 1, line[c:])
            self.state.set_current_line(line[:c])
            self.state.caret = (r + 1, 0)
        elif ks == "Up" and r > 0: self.state.caret = (r - 1, min(c, len(lines[r-1])))
        elif ks == "Down" and r < len(lines) - 1: self.state.caret = (r + 1, min(c, len(lines[r+1])))
        elif ks == "Left":
            if c > 0: self.state.caret = (r, c - 1)
            elif r > 0: self.state.caret = (r - 1, len(lines[r-1]))
        elif ks == "Right":
            if c < len(line): self.state.caret = (r, c + 1)
            elif r < len(lines) - 1: self.state.caret = (r + 1, 0)
        elif ks == "Home": self.state.caret = (r, 0)
        elif ks == "End": self.state.caret = (r, len(line))
        elif ch.isprintable() and len(line) < COLS:
            self.state.set_current_line(line[:c] + ch + line[c:])
            self.state.caret = (r, c + 1)

def log_frame_json(st: VPState, ctrl: Dict, frame_idx: int, mismatches: List):
    os.makedirs(FRAME_DIR, exist_ok=True)
    mismatch_map = ["".join("x" if any(m[0] == c for m in row) else "." for c in range(COLS)) for row in mismatches]
    payload = {
        "frame": frame_idx, "pc": st.pc, "source": st.source_lines,
        "decoded": ctrl.get("_decoded_lines", []), "result": st.last_result,
        "crc_ok": ctrl.get("_crc_ok", False), "mismatch_map": mismatch_map,
        "mismatches": [[{"col": col, "expected": exp, "actual": act} for col, exp, act in row] for row in mismatches]
    }
    with open(f"{FRAME_DIR}/log_{frame_idx:06d}.json", "w") as f: json.dump(payload, f, indent=2)
    with open(f"{FRAME_DIR}/index.jsonl", "a") as f:
        json.dump({"frame": frame_idx, "pc": st.pc, "crc_ok": payload["crc_ok"], "mismatches": sum(len(r) for r in mismatches)}, f)
        f.write("\n")

def run_visual_python(args):
    root = tk.Tk()
    if not args.live: root.withdraw()
    else:
        canvas = tk.Canvas(root, width=W, height=H, bg="#0E0F14")
        canvas.pack()
        root.title("Visual Python - Refresh Synchronous")

    px = Px(W, H, 60, FRAME_DIR if args.frames else None)
    st = VPState(source_lines=["1+1"])
    evaluator = SafeEvaluator()
    editor = Editor(root, st)

    code_changes = {
        40: ["sum(range(10))"],
        80: ["(3*7)+4", "2**8"],
    }

    if args.frames:
        for f in range(args.frames):
            if f in code_changes:
                st.source_lines = code_changes[f]
                st.caret = (0, len(st.source_lines[0]))

            draw_frame(px, st)
            px.tick()
            st, voted, ctrl = decode_and_step(px, st, evaluator)

            if voted:
                # Heatmap is no longer drawn, but we can still calculate mismatches for logging
                mismatches = [[(c, t[c], d[c]) for c in range(COLS) if _pad_to(t, COLS)[c] != _pad_to(d, COLS)[c]] for t, d in zip(st.source_lines, voted)]
                log_frame_json(st, ctrl, f, mismatches)
                if args.overlays and (any(mismatches) or not ctrl.get("_crc_ok", True)):
                    px._img.save(f"{FRAME_DIR}/fail_{f:06d}.png")
        print(f"Batch run complete. {args.frames} frames saved to {FRAME_DIR}/")
    else:
        photo = None
        def loop():
            nonlocal photo
            draw_frame(px, st)
            px.tick()
            st, voted, ctrl = decode_and_step(px, st, evaluator)

            if voted:
                # Heatmap is no longer drawn, but we can still calculate mismatches for logging
                mismatches = [[(c, t[c], d[c]) for c in range(COLS) if _pad_to(t, COLS)[c] != _pad_to(d, COLS)[c]] for t, d in zip(st.source_lines, voted)]
                log_frame_json(st, ctrl, st.pc, mismatches)
                if args.overlays and (any(mismatches) or not ctrl.get("_crc_ok", True)):
                    px._img.save(f"{FRAME_DIR}/fail_{st.pc:06d}.png")

            photo = ImageTk.PhotoImage(px._img)
            canvas.create_image(0, 0, image=photo, anchor="nw")
            root.after(16, loop)
        loop()
        root.mainloop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visual Python MVP with Refresh-Synchronous updates.")
    parser.add_argument("--frames", type=int, default=0, help="Run in batch mode for N frames.")
    parser.add_argument("--live", action="store_true", help="Run in live interactive mode.")
    parser.add_argument("--out", default=FRAME_DIR, help="Output directory for logs.")
    parser.add_argument("--overlays", action="store_true", help="Save PNGs for frames with errors.")
    args = parser.parse_args()

    if not args.live and not args.frames:
        args.live = True # Default to live mode if no frames specified

    FRAME_DIR = args.out
    if os.path.exists(f"{FRAME_DIR}/index.jsonl"):
        os.remove(f"{FRAME_DIR}/index.jsonl")

    run_visual_python(args)