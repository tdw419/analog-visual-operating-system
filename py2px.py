#!/usr/bin/env python3
# py2px.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Optional, Iterable, Callable, List
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
class Sleep: frames:int                 # sleep N ticks
@dataclass
class Tick:  pass                        # end-of-frame marker (optional)

Op = Rect | Line | Text | Clear | Sleep | Tick

# ---------- Runtime ----------
class Px:
    def __init__(self, width:int=640, height:int=360, fps:int=60, out_dir:str|None="out"):
        self.width, self.height, self.fps = width, height, fps
        self.out_dir = out_dir
        self._frame_idx = 0
        self._img = Image.new("RGB", (width, height), "#000000")
        self._draw = ImageDraw.Draw(self._img)
        self._default_font = None  # load lazily
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

    # ---- Drawing ops (imperative, immediate-mode) ----
    def clear(self, color:str="#000000"):     self._apply(Clear(color))
    def rect(self, x:int,y:int,w:int,h:int,color:str): self._apply(Rect(x,y,w,h,color))
    def line(self,x1:int,y1:int,x2:int,y2:int,width:int=1,color:str="#FFFFFF"): self._apply(Line(x1,y1,x2,y2,width,color))
    def text(self,x:int,y:int,text:str,size:int=14,color:str="#FFFFFF"): self._apply(Text(x,y,text,size,color))
    def sleep(self, frames:int):              self._apply(Sleep(frames))
    def tick(self):                           self._apply(Tick())

    # ---- Batch support (if you want to yield ops) ----
    def run(self, ops: Iterable[Op]):
        for op in ops: self._apply(op)

    # ---- Internals ----
    def _apply(self, op: Op):
        if isinstance(op, Clear):
            self._img.paste(Image.new("RGB", (self.width, self.height), op.color))
            self._draw = ImageDraw.Draw(self._img)
        elif isinstance(op, Rect):
            self._draw.rectangle([op.x, op.y, op.x+op.w-1, op.y+op.h-1], fill=op.color)
        elif isinstance(op, Line):
            self._draw.line([op.x1, op.y1, op.x2, op.y2], fill=op.color, width=op.width)
        elif isinstance(op, Text):
            font = self._font(op.size)
            self._draw.text((op.x, op.y), op.text, fill=op.color, font=font)
        elif isinstance(op, Sleep):
            for _ in range(max(0, op.frames)): self._commit()
        elif isinstance(op, Tick):
            self._commit()
        else:
            raise TypeError(f"Unknown op {op}")

    def _font(self, size:int):
        if self._default_font is None:
            try:
                self._default_font = ImageFont.load_default()
            except Exception:
                self._default_font = ImageFont.load_default()
        if hasattr(ImageFont, "truetype"):
            # Try a basic truetype if available; fallback otherwise
            try: return ImageFont.truetype("arial.ttf", size)
            except Exception: return self._default_font
        return self._default_font

    def _commit(self):
        self._frame_idx += 1
        if self.out_dir:
            self._img.save(os.path.join(self.out_dir, f"frame_{self._frame_idx:06d}.png"))

# ---------- Python-embedded DSL helpers ----------
def program(width:int=640, height:int=360, fps:int=60, out_dir:str|None="out"):
    """
    Decorator: turns a function f(px) into an entrypoint that renders frames.
    Usage:
        @program(320,240,60,"out")
        def main(px): ...
    """
    def wrap(fn: Callable[[Px], None]):
        def runner():
            px = Px(width, height, fps, out_dir)
            t0 = time.time()
            fn(px)
            # ensure at least one frame exists for static screens
            if px._frame_idx == 0: px.tick()
            dt = time.time()-t0
            print(f"[py2px] wrote {px._frame_idx} frames to {px.out_dir or '(memory)'} in {dt:.2f}s")
        return runner
    return wrap

# ---------- Demo program when run as a script ----------
@program(width=320, height=200, fps=60, out_dir="out_demo")
def main(px: Px):
    px.clear("#111111")
    px.text(8, 8, "PXOS — Python → Pixels", 12, "#A0FFA0")
    px.rect(6, 26, 308, 2, "#2F2F2F")
    px.tick()

    # animate a scanline + bouncing box for 120 frames
    vx, vy = 2, 1
    x, y, w, h = 20, 50, 40, 24
    for f in range(120):
        px.clear("#111111")
        px.text(8, 8, f"frame {f}", 12, "#FFFFFF")
        # scanline
        yy = 40 + (f % 80)
        px.line(0, yy, 319, yy, 1, "#00FFFF")
        # box
        px.rect(x, y, w, h, "#00FF88")
        px.text(x+6, y+6, "PX", 12, "#001a10")
        # bounce logic
        x += vx; y += vy
        if x < 0 or x+w >= 320: vx = -vx
        if y < 30 or y+h >= 190: vy = -vy
        px.tick()

if __name__ == "__main__":
    main()
