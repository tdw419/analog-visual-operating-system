from PIL import Image, ImageDraw
from typing import Dict, Any, Tuple

def rasterize_rects(hlir: Dict[str, Any], size: Tuple[int, int] = (256, 256)) -> Image.Image:
    """Render HLIR to a PIL Image, focusing on RECT ops"""
    img = Image.new("L", size, 0)  # Grayscale
    d = ImageDraw.Draw(img)
    for op in hlir.get("program", []):
        if op.get("op") == "RECT":
            x, y = int(op["x"]), int(op["y"])
            w, h = int(op["w"]), int(op["h"])
            gray = int(op.get("g", op.get("r", 0)))
            x2, y2 = x + max(w, 0), y + max(h, 0)
            d.rectangle([x, y, x2, y2], fill=max(0, min(255, gray)))
    return img
