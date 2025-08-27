#!/usr/bin/env python3
"""
visual_python_panes.py

Implements the Visual Python MVP with a live editor.
This is a self-contained, runnable demonstration of the core
code -> pixels -> decode -> execute -> pixels loop.

Dependencies:
- py2px_runtime.py
- control_strip.py (assumed to exist)
- visual_codec.py (assumed to exist)
- A Tkinter-compatible environment for keyboard input.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
from PIL import Image
import time
import tkinter as tk
import math

# Assume these are in the same directory
from py2px_runtime import Px
from control_strip import draw_control, read_control
from visual_codec import draw_text, sample_text, CELL_W, CELL_H, COLS, ROWS

# --- Configuration ---
PIXEL_READ = True  # Set to True to enable decoding from pixels
W, H = 640, 360
CTRL_H = 24
GAP = 8
PANE_W = (W - GAP * 3) // 2
PANE_H = (H - CTRL_H - GAP * 3) // 2

@dataclass
class EditorState:
    """Holds the state for our simple text editor pane."""
    text: str = "21 * 2"
    cursor_pos: int = 6

    def handle_key(self, key_sym: str, char: str):
        """Update editor state based on a key press."""
        if key_sym == "BackSpace":
            if self.cursor_pos > 0:
                self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
                self.cursor_pos -= 1
        elif key_sym == "Left":
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif key_sym == "Right":
            self.cursor_pos = min(len(self.text), self.cursor_pos + 1)
        elif len(char) == 1 and char.isprintable():
            self.text = self.text[:self.cursor_pos] + char + self.text[self.cursor_pos:]
            self.cursor_pos += 1

@dataclass
class VpState:
    """Holds the overall state of the Visual Python screen."""
    pc: int = 0
    editor: EditorState = field(default_factory=EditorState)
    last_result: str = ""
    decode_error: bool = False

def safe_eval(expr: str) -> str:
    """Sandboxed eval for safe execution of simple arithmetic."""
    allowed_names = {"math": math, "min": min, "max": max, "sum": sum, "range": range}
    try:
        # A real implementation would use a much more robust sandbox (e.g., ast.literal_eval or a custom parser)
        val = eval(expr, {"__builtins__": {}}, allowed_names)
        return str(val)
    except Exception as e:
        return f"ERR: {type(e).__name__}"

def pane_rect(col: int, row: int) -> tuple[int, int, int, int]:
    """Calculate the bounding box for a pane."""
    x = GAP + col * (PANE_W + GAP)
    y = CTRL_H + GAP + row * (PANE_H + GAP)
    return (x, y, x + PANE_W, y + PANE_H)

def draw_pane_a_source(px: Px, rect: tuple, state: EditorState):
    """Draws the source text editor pane."""
    x0, y0, _, _ = rect
    px.text(x0, y0 - 12, "A: Source Code (Live Editor)", 10, "#A0FFA0")
    px.rect(x0, y0, PANE_W, PANE_H, "#111820")

    # Draw text with a blinking cursor
    display_text = state.text
    if int(time.time() * 2) % 2 == 1: # Blink cursor
        display_text = state.text[:state.cursor_pos] + "_" + state.text[state.cursor_pos:]

    draw_text(px._draw, x0 + 4, y0 + 4, display_text.ljust(COLS), "#FFFFFF", "#111820")

def draw_pane_b_pixelated(px: Px, rect: tuple, text: str):
    """Draws the pixelated version of the source code."""
    x0, y0, _, _ = rect
    px.text(x0, y0 - 12, "B: Pixelated Source (Decoded)", 10, "#9BB4FF")
    px.rect(x0, y0, PANE_W, PANE_H, "#1E2330")
    draw_text(px._draw, x0 + 4, y0 + 4, text.ljust(COLS), "#FFFFFF", "#1E2330")

def draw_pane_c_result(px: Px, rect: tuple, result: str, error: bool):
    """Draws the result pane."""
    x0, y0, _, _ = rect
    px.text(x0, y0 - 12, "C: Result", 10, "#FFD966")
    px.rect(x0, y0, PANE_W, PANE_H, "#1A1F2B")

    result_color = "#FF6060" if error or "ERR:" in result else "#FFFFFF"
    draw_text(px._draw, x0 + 4, y0 + 4, result.ljust(COLS), result_color, "#1A1F2B")

def run_visual_python_editor(out_dir="out_vpy_editor"):
    """Main loop for the interactive Visual Python editor."""
    root = tk.Tk()
    root.title("Visual Python Input")
    root.geometry("100x50") # Keep it small and out of the way
    
    px = Px(W, H, 60, out_dir=None) # We'll manage the loop and saving
    state = VpState()

    key_queue: List[tuple[str, str]] = []
    def handle_key(event):
        key_queue.append((event.keysym, event.char))
    
    root.bind("<Key>", handle_key)

    def main_loop():
        # --- Handle Input ---
        if key_queue:
            keysym, char = key_queue.pop(0)
            state.editor.handle_key(keysym, char)

        # --- Draw Frame ---
        px.clear("#0E0F14")
        
        rect_a = pane_rect(0, 0)
        rect_b = pane_rect(1, 0)
        rect_c = pane_rect(0, 1)
        
        draw_pane_a_source(px, rect_a, state.editor)
        draw_pane_b_pixelated(px, rect_b, state.editor.text)
        draw_pane_c_result(px, rect_c, state.last_result, state.decode_error)

        draw_control(px._draw, {
            "SCREEN_ID": 101, "PC": state.pc & 0xFFF, "MAILBOX_OUT": len(state.last_result)
        })

        # --- Present Frame (e.g., to a live window or save it) ---
        # For this demo, we'll just use the internal image buffer.
        # A full implementation would use a FrameSink here.

        # --- Decode and Verify ---
        img = px._img # In digital mode, we capture the framebuffer directly
        ctrl = read_control(img)
        
        if PIXEL_READ:
            decoded_code = sample_text(img, rect_b[0] + 4, rect_b[1] + 4)
            state.decode_error = (decoded_code != state.editor.text)
        else: # Truth-tap mode for debugging
            decoded_code = state.editor.text
            state.decode_error = False

        # --- Execute ---
        if not state.decode_error:
            state.last_result = safe_eval(decoded_code)
        else:
            state.last_result = "DECODE FAIL"

        # --- Update State ---
        state.pc += 1

        # --- Acceptance Test ---
        assert ctrl.get("SCREEN_ID") == 101 and ctrl.get("_crc_ok", False), f"Control strip failed validation on frame {state.pc}"
        if PIXEL_READ:
            assert not state.decode_error, f"Decode mismatch on frame {state.pc}: expected '{state.editor.text}', got '{decoded_code}'"

        # This would be where you'd show the image in a live window
        # For now, we just loop.
        root.after(16, main_loop) # ~60Hz

    print("Starting Visual Python live editor. Close the small Tkinter window to exit.")
    root.after(10, main_loop)
    root.mainloop()

if __name__ == "__main__":
    run_visual_python_editor()