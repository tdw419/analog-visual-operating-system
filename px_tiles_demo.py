# px_tiles_demo.py
# Encode/decode pixel-executable "program sheets" made of 16x16 opcode tiles.
# Requires: Pillow (pip install pillow)

from PIL import Image, ImageDraw
import json, sys, math, argparse, os
from typing import List, Tuple

TILE = 16
PAYLOAD = 12  # central 12x12 area
MARGIN = (TILE - PAYLOAD) // 2  # 2 px padding all around
MINICELL = PAYLOAD // 4  # 3 px per payload bit (4x4 bits grid)

BLACK = 0
WHITE = 255

# ---- Bit packing helpers ----

def u8(n): return n & 0xFF
def to_int8(u):  # 0..255 → -128..127
    return u - 256 if u > 127 else u

def parity_nibble(opcode_nib, hi_nib, lo_nib):
    return (opcode_nib ^ hi_nib ^ lo_nib) & 0xF

def split_u8(n):
    return ((n >> 4) & 0xF, n & 0xF)

def join_u8(hi, lo):
    return ((hi & 0xF) << 4) | (lo & 0xF)

# Payload bit order: row-major over a 4x4 grid = 16 bits
# Bits 0..3   → opcode (low to high)
# Bits 4..7   → operand_hi nibble
# Bits 8..11  → operand_lo nibble
# Bits 12..15 → parity nibble

def pack_tile_bits(op, operand):
    op = op & 0xF
    hi, lo = split_u8(operand & 0xFF)
    par = parity_nibble(op, hi, lo)
    nibbles = [op, hi, lo, par]  # 4 nibbles
    bits = []
    for nib in nibbles:
        for i in range(4):
            bits.append((nib >> i) & 1)  # low→high within each nibble
    return bits  # len 16

def unpack_tile_bits(bits):
    # bits is length 16
    def nib_at(idx):
        base = idx*4
        v = 0
        for i in range(4):
            v |= (bits[base + i] & 1) << i
        return v & 0xF
    op = nib_at(0)
    hi = nib_at(1)
    lo = nib_at(2)
    par = nib_at(3)
    expect = parity_nibble(op, hi, lo)
    ok = (par == expect)
    return op, join_u8(hi, lo), ok

# ---- Tile rasterization / sampling ----

def draw_tile(op, operand) -> Image.Image:
    """Return a 16x16 tile image encoding (op, operand)."""
    img = Image.new('L', (TILE, TILE), WHITE)
    draw = ImageDraw.Draw(img)
    # payload bits
    bits = pack_tile_bits(op, operand)
    # payload origin
    x0 = MARGIN; y0 = MARGIN
    # draw per-bit mini-cells
    for bi, b in enumerate(bits):
        r = bi // 4
        c = bi % 4
        px = x0 + c * MINICELL
        py = y0 + r * MINICELL
        if b:
            draw.rectangle([px, py, px+MINICELL-1, py+MINICELL-1], fill=BLACK)
        else:
            draw.rectangle([px, py, px+MINICELL-1, py+MINICELL-1], fill=WHITE)
    # thin boundary box (optional visual aid)
    draw.rectangle([0,0,TILE-1,TILE-1], outline=0)
    return img

def sample_tile(img: Image.Image, tx: int, ty: int) -> Tuple[int,int,bool]:
    """Read tile at grid (tx,ty) and return (opcode, operand, parity_ok)."""
    # crop the tile
    x = tx*TILE
    y = ty*TILE
    tile = img.crop((x, y, x+TILE, y+TILE)).convert('L')
    bits = []
    x0 = MARGIN; y0 = MARGIN
    for r in range(4):
        for c in range(4):
            px = x0 + c * MINICELL
            py = y0 + r * MINICELL
            cx = px + MINICELL//2
            cy = py + MINICELL//2
            val = tile.getpixel((cx, cy))
            bits.append(1 if val < 128 else 0)
    return unpack_tile_bits(bits)

# ---- Page layout ----

def make_page(ops: List[Tuple[int,int]], cols=16) -> Image.Image:
    if cols < 1: cols = 1
    rows = math.ceil(len(ops) / cols)
    W = cols * TILE
    H = rows * TILE
    page = Image.new('L', (W, H), WHITE)
    # draw fiducials at four corners (solid black 16x16 blocks)
    draw = ImageDraw.Draw(page)
    def fid(x, y):
        draw.rectangle([x, y, x+TILE-1, y+TILE-1], fill=BLACK)
    if W >= TILE and H >= TILE:
        fid(0,0); fid(W-TILE,0); fid(0,H-TILE); fid(W-TILE,H-TILE)
    # lay tiles
    for i, (op, operand) in enumerate(ops):
        tx = i % cols
        ty = i // cols
        timg = draw_tile(op, operand)
        page.paste(timg, (tx*TILE, ty*TILE))
    return page

def read_page(img: Image.Image, cols=None) -> List[Tuple[int,int,bool]]:
    # Infer grid by trimming to multiples of TILE
    w, h = img.size
    cols_inf = w // TILE
    rows_inf = h // TILE
    if cols is None: cols = cols_inf
    out = []
    for ty in range(rows_inf):
        for tx in range(cols):
            op, operand, ok = sample_tile(img, tx, ty)
            out.append((op, operand, ok))
    return out

# ---- IR → CSV lowering ----

# Opcodes
NOP=0x0; SET_GRAY=0x1; MOVE_X=0x2; MOVE_Y=0x3; SET_W=0x4; SET_H=0x5; DRAW_RECT=0x6; COMMIT=0x7

def lower_to_csv(ops: List[Tuple[int,int]]) -> List[str]:
    x=y=w=h=gray=0
    csv = []
    for op, operand in ops:
        if op == NOP:
            continue
        elif op == SET_GRAY:
            gray = operand
        elif op == MOVE_X:
            x = (x + to_int8(operand)) & 0xFF
        elif op == MOVE_Y:
            y = (y + to_int8(operand)) & 0xFF
        elif op == SET_W:
            w = operand
        elif op == SET_H:
            h = operand
        elif op == DRAW_RECT:
            if w>0 and h>0:
                csv.append(f"RECT,{x},{y},{w},{h},{gray},{gray},{gray}")
        elif op == COMMIT:
            csv.append("COMMIT")
        else:
            # reserved / unknown
            pass
    return csv

# ---- Demo program ----

def demo_program() -> List[Tuple[int,int]]:
    # Draw three rectangles of different shades, then COMMIT.
    program = []
    def emit(op, arg=0): program.append((op, u8(arg)))
    # rect 1
    emit(SET_GRAY, 64); emit(SET_W, 40); emit(SET_H, 20)
    emit(MOVE_X, 20); emit(MOVE_Y, 20); emit(DRAW_RECT, 0)
    # rect 2
    emit(SET_GRAY, 160); emit(MOVE_X, 60); emit(DRAW_RECT, 0)
    # rect 3
    emit(SET_GRAY, 220); emit(MOVE_Y, 40); emit(DRAW_RECT, 0)
    emit(COMMIT, 0)
    return program

# ---- CLI ----

def cmd_encode(args):
    if args.demo:
        ops = demo_program()
    else:
        # Load IR from JSON: [{"op":int,"arg":int}, ...]
        with open(args.ir_json, "r", encoding="utf-8") as f:
            raw = json.load(f)
        ops = [(u8(x["op"]), u8(x.get("arg",0))) for x in raw]
    img = make_page(ops, cols=args.cols)
    img.save(args.out_png)
    with open(args.truth_json, "w", encoding="utf-8") as f:
        json.dump([{"op":op, "arg":arg} for op,arg in ops], f, indent=2)
    print(f"Wrote {args.out_png} and {args.truth_json}")

def cmd_decode(args):
    img = Image.open(args.in_png).convert('L')
    read = read_page(img, cols=args.cols)
    # parity check & strip reserved
    ops = []
    bad = 0
    for (op, arg, ok) in read:
        if op > 7:  # reserved tiles are ignored
            continue
        if not ok:
            bad += 1
            # you can choose to skip or include with a marker; we skip
            continue
        ops.append((op, arg))
    if bad:
        print(f"[warn] parity failures on {bad} tiles; skipped those ops.")
    csv_lines = lower_to_csv(ops)
    with open(args.out_csv, "w", encoding="utf-8") as f:
        for line in csv_lines:
            f.write(line + "\n")
    print(f"Wrote {args.out_csv} with {len(csv_lines)} CSV ops.")

def main():
    ap = argparse.ArgumentParser(description="Pixel-executable opcode tiles: encode/decode.")
    sp = ap.add_subparsers(dest="cmd", required=True)

    a = sp.add_parser("encode", help="IR → PNG page (program sheet)")
    a.add_argument("--demo", action="store_true", help="encode built-in demo program")
    a.add_argument("--ir-json", type=str, help="JSON IR file if not --demo")
    a.add_argument("--cols", type=int, default=16, help="tiles per row")
    a.add_argument("--out-png", type=str, default="program_sheet.png")
    a.add_argument("--truth-json", type=str, default="program_truth.json")
    a.set_defaults(func=cmd_encode)

    b = sp.add_parser("decode", help="PNG page → CSV")
    b.add_argument("in_png", type=str)
    b.add_argument("--cols", type=int, default=None, help="tiles per row (auto if omitted)")
    b.add_argument("--out-csv", type=str, default="program_out.csv")
    b.set_defaults(func=cmd_decode)

    args = ap.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
