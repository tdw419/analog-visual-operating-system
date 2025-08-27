# px_bitpack_v1.py — BitPack v1 codec (lossless "code as pixels")  (MIT)
from dataclasses import dataclass
from hashlib import sha256
from typing import Dict, Any, Optional, Tuple

try:
    from PIL import Image, ImageDraw  # type: ignore
except Exception:
    Image = None
    ImageDraw = None

MAGIC = b"PXCODE1\0"

@dataclass
class Spec:
    tile_w: int = 8   # payload bits across (per tile)
    tile_h: int = 8   # payload bits down   (per tile)
    cell:   int = 10  # tile size in pixels (edge length). Payload uses (cell-2)^2 bits; border=1px
    finder: int = 60  # finder square size in pixels
    margin: int = 16  # outer margin in pixels

def _draw_finder(draw, x, y, s):
    draw.rectangle([x, y, x+s, y+s], fill=(0,0,0))
    m = s//6
    draw.rectangle([x+m, y+m, x+s-m, y+s-m], fill=(255,255,255))
    draw.rectangle([x+2*m, y+2*m, x+s-2*m, y+s-2*m], fill=(0,0,0))

def encode_to_png(src_bytes: bytes, lang_id: str="pixelpy", spec: Spec=Spec(), out_path: str="out.png") -> str:
    """Encode bytes to a BitPack v1 PNG file."""
    if Image is None:
        raise RuntimeError("Pillow not available. pip install pillow")

    bits_per_tile = spec.tile_w * spec.tile_h
    bytes_per_tile = (bits_per_tile + 7)//8

    lang = (lang_id.encode("ascii")[:8]).ljust(8, b"\0")
    hdr = bytearray()
    hdr += MAGIC
    hdr += lang
    hdr += (len(src_bytes)).to_bytes(4, "little")
    hdr += sha256(src_bytes).digest()
    hdr += bytes([spec.tile_w, spec.tile_h, 1])  # bpp=1
    payload = bytes(hdr) + src_bytes

    tiles_needed = (len(payload) + bytes_per_tile - 1)//bytes_per_tile
    side = int((tiles_needed)**0.5 + 0.999)
    cols = side
    rows = (tiles_needed + cols - 1)//cols

    W = spec.margin*2 + spec.finder + cols*spec.cell + spec.finder
    H = spec.margin*2 + spec.finder + rows*spec.cell + spec.finder
    img = Image.new("RGB", (W, H), (255,255,255))
    d = ImageDraw.Draw(img)

    # Finders
    fx, fy = spec.margin, spec.margin
    _draw_finder(d, fx, fy, spec.finder)
    _draw_finder(d, W - spec.margin - spec.finder, fy, spec.finder)
    _draw_finder(d, fx, H - spec.margin - spec.finder, spec.finder)

    origin_x = fx + spec.finder
    origin_y = fy + spec.finder

    bi = 0  # bit index into payload
    for r in range(rows):
        for c in range(cols):
            ox = origin_x + c*spec.cell
            oy = origin_y + r*spec.cell
            # tile border + white fill
            d.rectangle([ox, oy, ox+spec.cell-1, oy+spec.cell-1], outline=(0,0,0), fill=(255,255,255))
            # payload bits
            for y in range(spec.tile_h):
                for x in range(spec.tile_w):
                    byte_i = bi // 8
                    bit_i  = 7 - (bi % 8)
                    bit = 0
                    if byte_i < len(payload):
                        bit = (payload[byte_i] >> bit_i) & 1
                    px = ox + 1 + x
                    py = oy + 1 + y
                    color = (255,255,255) if bit else (0,0,0)
                    d.point((px, py), fill=color)
                    bi += 1
    img.save(out_path, "PNG")
    return out_path

def _bit_from_rgb(rgb) -> int:
    if isinstance(rgb, (list, tuple)) and len(rgb) >= 3:
        r,g,b = rgb[:3]
    else:
        # grayscale scalar
        r = g = b = int(rgb)
    return 1 if (r+g+b) > 382 else 0  # > 1.5 * 255

def decode_from_png(path: str, spec: Spec=Spec()) -> Dict[str, Any]:
    """Decode a BitPack v1 PNG file and return dict with fields: lang, tile, bpp, content."""
    if Image is None:
        raise RuntimeError("Pillow not available. pip install pillow")
    img = Image.open(path).convert("RGB")
    return decode_from_pillow(img, spec)

def decode_from_pillow(img, spec: Spec=Spec()) -> Dict[str, Any]:
    W,H = img.size
    fx, fy = spec.margin, spec.margin
    origin_x = fx + spec.finder
    origin_y = fy + spec.finder
    cols = (W - spec.margin - spec.finder - fx) // spec.cell
    rows = (H - spec.margin - spec.finder - fy) // spec.cell

    bits = []
    for r in range(rows):
        for c in range(cols):
            ox = origin_x + c*spec.cell
            oy = origin_y + r*spec.cell
            for y in range(spec.tile_h):
                for x in range(spec.tile_w):
                    px = ox + 1 + x
                    py = oy + 1 + y
                    bits.append(_bit_from_rgb(img.getpixel((px, py))))

    by = bytearray()
    for i in range(0, len(bits), 8):
        b = 0
        for j in range(8):
            b = (b << 1) | (bits[i+j] if i+j < len(bits) else 0)
        by.append(b)

    magic = bytes(by[0:8])
    if magic != MAGIC:
        raise ValueError("Bad magic in BitPack image")
    lang = bytes(by[8:16]).rstrip(b"\0").decode("ascii", errors="ignore")
    content_len = int.from_bytes(by[16:20], "little")
    digest = bytes(by[20:52])
    tw, th, bpp = by[52], by[53], by[54]
    content = bytes(by[55:55+content_len])
    if sha256(content).digest() != digest:
        raise ValueError("SHA-256 mismatch in BitPack image")
    return {"lang": lang, "tile": (tw,th), "bpp": bpp, "content": content}

def decode_from_numpy(px, spec: Spec=Spec()) -> Dict[str, Any]:
    """Decode from a numpy pixel buffer (H,W,3|4; float32 0..1 or uint8)."""
    import numpy as np
    H, W = px.shape[:2]
    fx, fy = spec.margin, spec.margin
    origin_x = fx + spec.finder
    origin_y = fy + spec.finder
    cols = (W - spec.margin - spec.finder - fx) // spec.cell
    rows = (H - spec.margin - spec.finder - fy) // spec.cell

    if px.dtype != np.uint8:
        arr = (np.clip(px, 0, 1) * 255).astype(np.uint8)
    else:
        arr = px

    bits = []
    for r in range(rows):
        for c in range(cols):
            ox = origin_x + c*spec.cell
            oy = origin_y + r*spec.cell
            # payload bits
            for y in range(spec.tile_h):
                for x in range(spec.tile_w):
                    py = oy + 1 + y
                    px_ = ox + 1 + x
                    rgb = arr[py, px_, :3]
                    bits.append(1 if int(rgb.sum()) > 382 else 0)

    by = bytearray()
    for i in range(0, len(bits), 8):
        b = 0
        for j in range(8):
            b = (b << 1) | (bits[i+j] if i+j < len(bits) else 0)
        by.append(b)

    from hashlib import sha256 as _sha256
    magic = bytes(by[0:8])
    if magic != MAGIC:
        raise ValueError("Bad magic in BitPack buffer")
    lang = bytes(by[8:16]).rstrip(b"\0").decode("ascii", errors="ignore")
    content_len = int.from_bytes(by[16:20], "little")
    digest = bytes(by[20:52])
    tw, th, bpp = by[52], by[53], by[54]
    content = bytes(by[55:55+content_len])
    if _sha256(content).digest() != digest:
        raise ValueError("SHA-256 mismatch in BitPack buffer")
    return {"lang": lang, "tile": (tw,th), "bpp": bpp, "content": content}
