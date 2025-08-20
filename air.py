"""
Analog Intermediate Representation (AIR) Schema
Defines the data structures for the analog compiler's instruction set.
Includes serialization/deserialization for JSON and a compact bytecode format.
"""
import json
import struct
import zlib
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Union, Tuple

# ---------- Types ----------
Color = Tuple[int, int, int]

@dataclass
class TextOp:
    op: str = field(default="TEXT", init=False)
    text: str
    x: int
    y: int
    color: Color
    scale: int = 2

@dataclass
class RectOp:
    op: str = field(default="RECT", init=False)
    x: int
    y: int
    w: int
    h: int
    color: Color

@dataclass
class LineOp:
    op: str = field(default="LINE", init=False)
    x1: int
    y1: int
    x2: int
    y2: int
    color: Color

@dataclass
class CursorOp:
    op: str = field(default="CURSOR", init=False)
    x: int
    y: int
    color: Color
    w: int = 2
    h: int = 14
    blink_hz: int = 0

@dataclass
class MoveOp:
    op: str = field(default="MOVE", init=False)
    x: int
    y: int

@dataclass
class BlankOp:
    op: str = field(default="BLANK", init=False)
    enable: bool

IROp = Union[TextOp, RectOp, LineOp, CursorOp, MoveOp, BlankOp]

@dataclass
class AIR:
    """The top-level container for an analog program."""
    ops: List[IROp]
    timing: Dict[str, int] = field(default_factory=lambda: {"dt_us": 1})

# ---------- Serialization / Deserialization ----------

def air_to_json(air: AIR) -> str:
    """Serializes an AIR object to a JSON string."""
    return json.dumps(asdict(air), indent=2)

def air_from_json(json_str: str) -> AIR:
    """Deserializes a JSON string into an AIR object."""
    data = json.loads(json_str)
    ops = []
    op_map = {
        "TEXT": TextOp, "RECT": RectOp, "LINE": LineOp,
        "CURSOR": CursorOp, "MOVE": MoveOp, "BLANK": BlankOp
    }
    for op_data in data.get("ops", []):
        op_class = op_map.get(op_data.get("op"))
        if op_class:
            # Remove 'op' key as it's not in the dataclass __init__
            params = {k: v for k, v in op_data.items() if k != 'op'}
            ops.append(op_class(**params))
    return AIR(ops=ops, timing=data.get("timing", {"dt_us": 1}))

# ---------- Bytecode (AIRB format) ----------

OP_MAP = {
    TextOp: 0x01, RectOp: 0x02, LineOp: 0x03,
    CursorOp: 0x04, MoveOp: 0x05, BlankOp: 0x06,
}
OP_END = 0xFF

def pack_airb(air: AIR) -> bytes:
    """Packs an AIR object into the compact AIRB bytecode format."""
    body = b''
    for op in air.ops:
        op_code = OP_MAP.get(type(op))
        if op_code is None: continue

        body += struct.pack('<B', op_code)
        if isinstance(op, TextOp):
            text_bytes = op.text.encode('ascii', 'ignore')[:255]
            body += struct.pack('<HHBBBB', op.x, op.y, *op.color, op.scale)
            body += struct.pack('<B', len(text_bytes)) + text_bytes
        elif isinstance(op, RectOp):
            body += struct.pack('<HHHHBBB', op.x, op.y, op.w, op.h, *op.color)
        elif isinstance(op, LineOp):
            body += struct.pack('<HHHHBBB', op.x1, op.y1, op.x2, op.y2, *op.color)
        elif isinstance(op, CursorOp):
            body += struct.pack('<HHBBBBBB', op.x, op.y, op.w, op.h, *op.color, op.blink_hz)
        elif isinstance(op, MoveOp):
            body += struct.pack('<HH', op.x, op.y)
        elif isinstance(op, BlankOp):
            body += struct.pack('<B', 1 if op.enable else 0)

    body += struct.pack('<B', OP_END)
    crc = zlib.crc32(body)
    header = b'AIRB' + struct.pack('<BII', 1, crc, len(air.ops)) # Version 1
    return header + body

def unpack_airb(data: bytes) -> AIR:
    """Unpacks AIRB bytecode into an AIR object."""
    if data[:4] != b'AIRB' or data[4] != 1:
        raise ValueError("Invalid AIRB magic or version")

    crc, op_count = struct.unpack('<II', data[5:13])
    body = data[13:]

    if zlib.crc32(body) != crc:
        raise ValueError("CRC mismatch in AIRB payload")

    ops = []
    i = 0
    while i < len(body):
        op_code = body[i]; i += 1
        if op_code == OP_END: break

        if op_code == 0x01: # TEXT
            x,y,r,g,b,scale = struct.unpack('<HHBBBB', body[i:i+8]); i+=8
            ln = body[i]; i+=1
            s = body[i:i+ln].decode('ascii', 'ignore'); i+=ln
            ops.append(TextOp(text=s, x=x, y=y, color=(r,g,b), scale=scale))
        # ... Implement unpacking for other op types ...

    return AIR(ops=ops)
