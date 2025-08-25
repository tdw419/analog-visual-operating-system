from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageStat

# Monospace cell configuration
CELL_W, CELL_H = 8, 12       # pixel size per character cell
PAD_X, PAD_Y = 2, 2          # padding inside cell for sampling
ROWS, COLS = 8, 40           # text grid (adjust per screen area)

# A tiny 1-bit font atlas encoded as “on” sample points relative to cell.
# Keep it small: digits, ops, letters used in simple evals. You can extend this.
# Points are in 0..(CELL_W-1), 0..(CELL_H-1).
GLYPH = {
    "0": [(1,1),(2,1),(3,1),(4,1),(5,1),(1,2),(5,2),(1,3),(5,3),(1,4),(5,4),(1,5),(5,5),(1,6),(5,6),(1,7),(5,7),(1,8),(5,8),(1,9),(5,9),(1,10),(2,10),(3,10),(4,10),(5,10)],
    "1": [(3,1),(3,2),(3,3),(3,4),(3,5),(3,6),(3,7),(3,8),(3,9),(3,10)],
    "2": [(1,1),(2,1),(3,1),(4,1),(5,1),(5,2),(5,3),(4,4),(3,5),(2,6),(1,7),(1,8),(1,9),(1,10),(2,10),(3,10),(4,10),(5,10)],
    "3": [(1,1),(2,1),(3,1),(4,1),(5,1),(5,2),(5,3),(3,4),(4,5),(5,6),(5,7),(5,8),(1,10),(2,10),(3,10),(4,10),(5,10)],
    "4": [(1,1),(1,2),(1,3),(1,4),(5,1),(5,2),(5,3),(5,4),(1,4),(2,4),(3,4),(4,4),(5,4),(5,5),(5,6),(5,7),(5,8),(5,9),(5,10)],
    "5": [(1,1),(2,1),(3,1),(4,1),(5,1),(1,2),(1,3),(1,4),(1,5),(2,5),(3,5),(4,5),(5,5),(5,6),(5,7),(5,8),(1,10),(2,10),(3,10),(4,10),(5,10)],
    "6": [(5,1),(4,1),(3,1),(2,1),(1,2),(1,3),(1,4),(1,5),(2,5),(3,5),(4,5),(5,5),(5,6),(5,7),(5,8),(1,10),(2,10),(3,10),(4,10),(5,10)],
    "7": [(1,1),(2,1),(3,1),(4,1),(5,1),(5,2),(4,3),(4,4),(3,5),(3,6),(2,7),(2,8),(2,9),(1,10)],
    "8": [(1,1),(2,1),(3,1),(4,1),(5,1),(1,2),(5,2),(1,3),(5,3),(1,4),(5,4),(2,5),(3,5),(4,5),(1,6),(5,6),(1,7),(5,7),(1,8),(5,8),(1,9),(5,9),(1,10),(2,10),(3,10),(4,10),(5,10)],
    "9": [(1,1),(2,1),(3,1),(4,1),(5,1),(1,2),(5,2),(1,3),(5,3),(1,4),(5,4),(2,5),(3,5),(4,5),(5,6),(5,7),(5,8),(1,10),(2,10),(3,10),(4,10)],
    "+": [(3,4),(2,5),(3,5),(4,5),(3,6)],
    "-": [(2,5),(3,5),(4,5)],
    "*": [(2,4),(4,4),(3,5),(2,6),(4,6)],
    "/": [(5,1),(4,2),(4,3),(3,4),(3,5),(2,6),(2,7),(1,8),(1,9)],
    "(": [(3,2),(2,3),(2,4),(2,5),(2,6),(2,7),(2,8),(3,9)],
    ")": [(2,2),(3,3),(3,4),(3,5),(3,6),(3,7),(3,8),(2,9)],
    "=": [(2,4),(3,4),(4,4),(2,6),(3,6),(4,6)],
    " ": [],
}

def draw_text(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, color_fg="#FFFFFF", color_bg="#000000"):
    cx, cy = x, y
    for ch in text[:COLS]:
        draw.rectangle([cx, cy, cx+CELL_W-1, cy+CELL_H-1], fill=color_bg)
        pts = GLYPH.get(ch, GLYPH[" "])
        for (px, py) in pts:
            draw.point((cx+px, cy+py), fill=color_fg)
        cx += CELL_W

def sample_text(img: Image.Image, x: int, y: int) -> str:
    # Convert a row of cells back into characters by matching the atlas.
    row = ""
    for c in range(COLS):
        x0, y0 = x + c*CELL_W, y
        # Build a fingerprint: collect on-pixels roughly where atlas would set them.
        on = []
        for ch, pts in GLYPH.items():
            # quick test: count bright points at atlas positions
            score = 0
            for (px, py) in pts[:max(1, len(pts))]:
                roi = img.crop((x0+px, y0+py, x0+px+1, y0+py+1))
                if ImageStat.Stat(roi).mean[0] > 127:
                    score += 1
            on.append((score, ch))
        on.sort(reverse=True)
        best_score, best_char = on[0]
        if best_score > 0:
            row += best_char
        else:
            row += " "
    return row.rstrip()
