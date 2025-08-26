# dvc_v01_verified.py
from PIL import Image, ImageDraw
import zlib

# ===== ISA Palette =====
PALETTE_VERSION = 1
ISA_VERSION = (0,1)  # major, minor

PALETTE = {
    "NOP": (0,0,0),
    "HALT": (255,255,255),
    "PUSHI": (0,0,255),
    "ADD": (0,255,0),
    "SUB": (255,0,0),
    "MUL": (255,128,0),
    "DIV": (0,255,255),
    "PRINT": (255,255,0),
    "FIDUCIAL": (10,10,10)
}
COLOR_TO_OP = {v:k for k,v in PALETTE.items()}

# ===== Geometry =====
TILE = 16
CODE_COLS, CODE_ROWS = 8, 8
DATA_COLS, DATA_ROWS = 8, 4
HEADER_TILES = 12

# ===== Assembler =====
def assemble(program, out_png):
    words = []
    for line in program:
        parts = line.strip().split()
        if not parts: continue
        op = parts[0].upper()
        if op not in PALETTE:
            raise ValueError(f"Unknown op {op}")
        words.append(PALETTE[op])
        if op == "PUSHI":
            imm = int(parts[1])
            r = imm & 0xFF
            g = (imm >> 8) & 0xFF
            b = (imm >> 16) & 0xFF
            words.append((r,g,b))
    while len(words) < CODE_COLS*CODE_ROWS:
        words.append(PALETTE["NOP"])
    data_words = [(0,0,0)]*(DATA_COLS*DATA_ROWS)

    # Compute CRC over code+data
    crc_data = bytes([c for rgb in words+data_words for c in rgb])
    crc_val = zlib.crc32(crc_data) & 0xFFFFFFFF

    # Build header
    header_words = [
        (68,86,67),  # "DVC"
        (ISA_VERSION[0], ISA_VERSION[1], 0),
        (PALETTE_VERSION, 0, 0),
        ((crc_val>>0)&0xFF,0,0),
        ((crc_val>>8)&0xFF,0,0),
        ((crc_val>>16)&0xFF,0,0),
        ((crc_val>>24)&0xFF,0,0),
        (CODE_COLS, CODE_ROWS, 0),
        (DATA_COLS, DATA_ROWS, 0),
        PALETTE["FIDUCIAL"],
        PALETTE["FIDUCIAL"],
        PALETTE["FIDUCIAL"]
    ]

    # Layout image
    total_cols = max(CODE_COLS, DATA_COLS)
    total_rows = 1 + CODE_ROWS + DATA_ROWS
    img = Image.new("RGB", (total_cols*TILE, total_rows*TILE), (0,0,0))
    d = ImageDraw.Draw(img)

    def put_tile(ix, iy, color):
        x0, y0 = ix*TILE, iy*TILE
        d.rectangle([x0,y0,x0+TILE-1,y0+TILE-1], fill=color)

    for i, rgb in enumerate(header_words):
        put_tile(i, 0, rgb)
    for idx, rgb in enumerate(words):
        put_tile(idx % CODE_COLS, 1 + idx // CODE_COLS, rgb)
    for idx, rgb in enumerate(data_words):
        put_tile(idx % DATA_COLS, 1 + CODE_ROWS + idx // DATA_COLS, rgb)

    img.save(out_png)
    print(f"Saved verified program to {out_png}")

# ===== Emulator =====
def emulate(png_path):
    img = Image.open(png_path).convert("RGB")
    pixels = img.load()

    def get_tile(ix, iy):
        x0, y0 = ix*TILE, iy*TILE
        return pixels[x0,y0]

    # Read header
    magic = get_tile(0,0)
    if magic != (68,86,67):
        raise ValueError("Bad magic — not a DVC frame")
    isa_ver = get_tile(1,0)
    if (isa_ver[0], isa_ver[1]) != ISA_VERSION:
        raise ValueError("ISA version mismatch")
    palette_ver = get_tile(2,0)[0]
    if palette_ver != PALETTE_VERSION:
        raise ValueError("Palette version mismatch")

    # Read CRC from header
    crc_bytes = [
        get_tile(3,0)[0],
        get_tile(4,0)[0],
        get_tile(5,0)[0],
        get_tile(6,0)[0]
    ]
    header_crc = crc_bytes[0] | (crc_bytes[1]<<8) | (crc_bytes[2]<<16) | (crc_bytes[3]<<24)

    # Read code+data
    code_words = []
    for idx in range(CODE_COLS*CODE_ROWS):
        ix, iy = idx % CODE_COLS, 1 + idx // CODE_COLS
        code_words.append(get_tile(ix, iy))
    data_words = []
    for idx in range(DATA_COLS*DATA_ROWS):
        ix, iy = idx % DATA_COLS, 1 + CODE_ROWS + idx // DATA_COLS
        data_words.append(get_tile(ix, iy))

    # Verify CRC
    crc_data = bytes([c for rgb in code_words+data_words for c in rgb])
    calc_crc = zlib.crc32(crc_data) & 0xFFFFFFFF
    if calc_crc != header_crc:
        raise ValueError("CRC mismatch — frame corrupted")

    # Execute
    stack = []
    ip = 0
    while ip < len(code_words):
        op_color = code_words[ip]
        op = COLOR_TO_OP.get(op_color, None)
        if op is None:
            print(f"Unknown opcode color {op_color} at {ip}")
            break
        if op == "NOP":
            ip += 1
        elif op == "HALT":
            print("HALT")
            break
        elif op == "PUSHI":
            imm_color = code_words[ip+1]
            imm = imm_color[0] | (imm_color[1]<<8) | (imm_color[2]<<16)
            stack.append(imm)
            ip += 2
        elif op == "ADD":
            b, a = stack.pop(), stack.pop()
            stack.append(a+b)
            ip += 1
        elif op == "SUB":
            b, a = stack.pop(), stack.pop()
            stack.append(a-b)
            ip += 1
        elif op == "MUL":
            b, a = stack.pop(), stack.pop()
            stack.append(a*b)
            ip += 1
        elif op == "DIV":
            b, a = stack.pop(), stack.pop()
            stack.append(a//b)
            ip += 1
        elif op == "PRINT":
            val = stack.pop()
            print(f"PRINT: {val}")
            ip += 1

# ===== Example =====
if __name__ == "__main__":
    program = [
        "PUSHI 7",
        "PUSHI 5",
        "MUL",
        "PUSHI 2",
        "ADD",
        "PRINT",
        "HALT"
    ]
    assemble(program, "first_light_verified.png")
    emulate("first_light_verified.png")
