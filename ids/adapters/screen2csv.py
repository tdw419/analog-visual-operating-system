# adapters/screen2csv.py
import time, math
from typing import Optional, Tuple
import numpy as np
from PIL import Image
import mss
try:
    import pygetwindow as gw  # Windows-friendly window locator
except Exception:
    gw = None

def _find_window_bbox(title_substr: str) -> Optional[Tuple[int,int,int,int]]:
    """Return (left, top, right, bottom) for the first matching window."""
    if gw is None:
        return None
    wins = [w for w in gw.getAllTitles() if title_substr.lower() in w.lower()]
    if not wins:
        return None
    w = gw.getWindowsWithTitle(wins[0])[0]
    if not w or not w.isVisible:
        return None
    # gw box: (left, top, width, height)
    return (w.left, w.top, w.left + w.width, w.top + w.height)

def _tile_average(img: np.ndarray, tile: int) -> np.ndarray:
    """Downsample to tile grid by averaging; returns (H//tile, W//tile, 3) uint8."""
    H, W, C = img.shape
    h = (H // tile) * tile
    w = (W // tile) * tile
    img = img[:h, :w, :3]  # drop alpha if present
    img = img.reshape(h // tile, tile, w // tile, tile, 3).mean(axis=(1,3)).astype(np.uint8)
    return img  # [Th, Tw, 3]

def run_screen_to_csv(csv_sess, window_title_substr: str, fps: int = 30, tile_px: int = 8,
                      thresh: float = 10.0, max_rects_per_frame: int = 200):
    """
    Capture a window by (fuzzy) title, tile & diff, and emit RECT ops + COMMIT per frame.
    thresh: per-tile mean RGB delta to consider 'changed'.
    """
    bbox = _find_window_bbox(window_title_substr)
    if not bbox:
        raise RuntimeError(f"Window not found or unsupported. Title contains: {window_title_substr!r}")
    left, top, right, bottom = bbox
    width, height = right - left, bottom - top

    sct = mss.mss()
    prev_small = None
    period = 1.0 / max(1, fps)
    next_t = time.perf_counter()

    while True:
        # capture
        frame = np.array(sct.grab({"left": left, "top": top, "width": width, "height": height}))  # BGRA
        frame_rgb = frame[..., :3][:, :, ::-1]  # to RGB

        # tile & diff
        small = _tile_average(frame_rgb, tile_px)  # [Th, Tw, 3]
        changed_tiles = []
        if prev_small is None:
            # first frame: emit a background CLEAR-ish via coarse rect mosaic
            baseline = np.zeros_like(small)
            diff = np.linalg.norm(small.astype(np.float32) - baseline.astype(np.float32), axis=2)
            changed_tiles = np.argwhere(diff > 0.0)
        else:
            diff = np.linalg.norm(small.astype(np.float32) - prev_small.astype(np.float32), axis=2)
            changed_tiles = np.argwhere(diff > thresh)

        Th, Tw, _ = small.shape
        # Emit RECT per changed tile (merged runs would be nicer; MVP keeps it simple)
        rects_emitted = 0
        for ty, tx in changed_tiles:
            if rects_emitted >= max_rects_per_frame:
                break
            r, g, b = map(int, small[ty, tx])
            x = int(tx * tile_px)
            y = int(ty * tile_px)
            w = tile_px
            h = tile_px
            csv_sess.write_rect(x, y, w, h, r, g, b, 1.0)
            rects_emitted += 1

        csv_sess.commit()
        prev_small = small

        # pacing
        next_t += period
        sleep_for = next_t - time.perf_counter()
        if sleep_for > 0:
            time.sleep(sleep_for)
