from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple
from PIL import Image, ImageDraw, ImageStat

# Layout: a 24px tall band at the top; bits as 4x4 cells with 1-cell spacers.
CELL = 4
MARGIN = 4
CTRL_HEIGHT = MARGIN*2 + CELL
CTRL_Y0 = 0

# Field order is part of the protocol. Keep stable.
FIELDS: List[Tuple[str, int]] = [
    ("SCREEN_ID", 12),
    ("PC", 12),
    ("MAILBOX_IN", 8),
    ("MAILBOX_OUT", 8),
    ("CRC16", 16),
]

def crc16_ccitt(buf: bytes, poly: int = 0x1021, init: int = 0xFFFF) -> int:
    c = init
    for b in buf:
        c ^= (b << 8) & 0xFFFF
        for _ in range(8):
            c = ((c << 1) ^ poly) & 0xFFFF if (c & 0x8000) else (c << 1) & 0xFFFF
    return c & 0xFFFF

def _pack_fields(fields: Dict[str, int]) -> bytes:
    # Pack all but CRC16 in order, MSB-first, then return bytes for CRC calc.
    bits: List[int] = []
    for name, nbits in FIELDS:
        if name == "CRC16":
            continue
        val = int(fields.get(name, 0)) & ((1 << nbits) - 1)
        for i in range(nbits-1, -1, -1):
            bits.append((val >> i) & 1)
    # to bytes
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            if i+j < len(bits):
                byte = (byte << 1) | bits[i+j]
            else:
                byte <<= 1
        out.append(byte)
    return bytes(out)

def draw_control(draw: ImageDraw.ImageDraw, fields: Dict[str, int], *, x0: int = MARGIN, y0: int = CTRL_Y0 + MARGIN) -> None:
    # Compute CRC over non-CRC fields and paint all fields as bit cells.
    payload = _pack_fields(fields)
    crc = crc16_ccitt(payload)
    fields = dict(fields)
    fields["CRC16"] = crc

    x = x0
    for name, nbits in FIELDS:
        val = int(fields.get(name, 0)) & ((1 << nbits) - 1)
        for i in range(nbits-1, -1, -1):
            bit = (val >> i) & 1
            draw.rectangle([x, y0, x+CELL-1, y0+CELL-1],
                           fill=(255,255,255) if bit else (0,0,0))
            x += CELL
        x += CELL  # spacer

def read_control(img: Image.Image, *, x0: int = MARGIN, y0: int = CTRL_Y0 + MARGIN) -> Dict[str, int]:
    from math import floor
    res: Dict[str, int] = {}
    x = x0
    for name, nbits in FIELDS:
        val = 0
        for _ in range(nbits):
            roi = img.crop((x, y0, x+CELL, y0+CELL))
            mean = ImageStat.Stat(roi).mean[0]
            bit = 1 if mean > 127 else 0
            val = (val << 1) | bit
            x += CELL
        res[name] = val
        x += CELL  # spacer

    # Verify CRC
    provided = res.get("CRC16", 0)
    payload = _pack_fields(res)  # uses all fields except CRC16 internally
    expect = crc16_ccitt(payload)
    res["_crc_ok"] = (expect == provided)
    return res
