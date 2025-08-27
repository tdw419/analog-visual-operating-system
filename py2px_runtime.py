#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Iterable, Callable, List, Optional
from PIL import Image, ImageDraw, ImageFont
import os, time

# ---------- Core IR (immediate-mode ops) ----------
@dataclass
class Rect:  x:int; y:int; w:int; h:int; color:str
@dataclass
class Line:  x1:int; y1:int; x2:int; y2:int; width:int; color:str
@dataclass
class Text:  x:int; y:int; text:str; size:int; color:str
@dataclass
class Clear: color:str
@dataclass
class Sleep: frames:int
@dataclass
class Tick:  pass

Op = Rect | Line | Text | Clear | Sleep | Tick

# ---------- Runtime ----------
class Px:
    """A minimal, immediate-mode pixel runtime."""
    def __init__(self, width:int=640, height:int=360, fps:int=60, out_dir:str|None="out"):
        self.width, self.height, self.fps = width, height, fps
        self.out_dir = out_dir
        self._frame_idx = 0
        self._img = Image.new("RGB", (width, height), "#000000")
        self._draw = ImageDraw.Draw(self._img)
        self._op_log_for_frame: List[Op] = []
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

    # ---- Drawing ops (imperative, immediate-mode) ----
    def clear(self, color:str="#000000"):     self._apply(Clear(color))
    def rect(self, x:int,y:int,w:int,h:int,color:str): self._apply(Rect(x,y,w,h,color))
    def line(self,x1:int,y1:int,x2:int,y2:int,width:int=1,color:str="#FFFFFF"): self._apply(Line(x1,y1,x2,y2,width,color))
    def text(self,x:int,y:int,text:str,size:int=14,color:str="#FFFFFF"): self._apply(Text(x,y,text,size,color))
    def sleep(self, frames:int):              self._apply(Sleep(frames))
    def tick(self):                           self._apply(Tick())

    # ---- Batch support ----
    def run(self, ops: Iterable[Op]):
        for op in ops: self._apply(op)

    # ---- Internals ----
    def _apply(self, op: Op):
        """Applies an op to the canvas and logs it for the current frame."""
        self._op_log_for_frame.append(op)

        if isinstance(op, Clear):
            self._draw.rectangle([0, 0, self.width, self.height], fill=op.color)
        elif isinstance(op, Rect):
            self._draw.rectangle([op.x, op.y, op.x+op.w-1, op.y+op.h-1], fill=op.color)
        elif isinstance(op, Line):
            self._draw.line([op.x1, op.y1, op.x2, op.y2], fill=op.color, width=op.width)
        elif isinstance(op, Text):
            # For simplicity, using a default font. A real implementation would handle fonts better.
            font = ImageFont.load_default()
            self._draw.text((op.x, op.y), op.text, fill=op.color, font=font)
        elif isinstance(op, Sleep):
            for _ in range(max(0, op.frames)): self._commit()
        elif isinstance(op, Tick):
            self._commit()
        else:
            raise TypeError(f"Unknown op {op}")

    def _commit(self) -> Tuple[str, List[Op]]:
        """Saves the current frame, returns its path and op log, then resets."""
        self._frame_idx += 1
        frame_path = ""
        if self.out_dir:
            frame_path = os.path.join(self.out_dir, f"frame_{self._frame_idx:06d}.png")
            self._img.save(frame_path)

        committed_ops = self._op_log_for_frame
        self._op_log_for_frame = []
        return frame_path, committed_ops

def program(width:int=640, height:int=360, fps:int=60, out_dir:str|None="out"):
    """Decorator: turns a function f(px) into a runnable entrypoint."""
    def wrap(fn: Callable[[Px], None]):
        def runner():
            px = Px(width, height, fps, out_dir)
            t0 = time.time()
            fn(px)
            if not px._op_log_for_frame and px._frame_idx == 0:
                px.tick() # Ensure at least one frame is committed
            dt = time.time()-t0
            print(f"[py2px] wrote {px._frame_idx} frames to {px.out_dir or '(memory)'} in {dt:.2f}s")
        return runner
    return wrap