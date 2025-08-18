from typing import List, Tuple
import struct

# Opcodes must match strict_runner.py
class OP:
    HALT=0x00; PXSET=0x01; FILL=0x02
    TEXT=0x10; SET_POOLPOS=0x12
    LD=0x06; ST=0x07; CMP=0x09
    JMP=0x0A; JZ=0x0B; JNZ=0x0C; JL=0x0D; JG=0x0E; JB=0x0F; JA=0x11
    READ_KEY=0x10
    ADD=0x13; SUB=0x14; MUL=0x15; MOV=0x16; MOD=0x17

class CartBuilder:
    def __init__(self):
        self.code: List[Tuple[int, List[int]]] = []
        self.pool = bytearray()

    def emit(self, op: int, *args: int):
        # Pad args to 5 elements to match runner's expectation
        padded_args = list(args) + [0] * (5 - len(args))
        self.code.append((op, padded_args))

    def str_id(self, s: str) -> int:
        i = len(self.pool)
        self.pool += s.encode("ascii") + b"\x00"
        return i

    def assemble(self) -> bytes:
        out = bytearray()
        # Header: magic, num_instructions, pool_length
        out += struct.pack("<4sII", b"PXL1", len(self.code), len(self.pool))
        # Code: instruction by instruction
        for op, args in self.code:
            out += struct.pack("<I", op)
            out += struct.pack("<IIIII", *args) # 5 args
        # Pool
        out += self.pool
        return bytes(out)

def text_at(a: CartBuilder, x: int, y: int, s: str):
    idx = a.str_id(s)
    a.emit(OP.SET_POOLPOS, idx)
    a.emit(OP.TEXT, x, y, len(s))

def build_pxweb_cart() -> bytes:
    a = CartBuilder()
    # Colors (RRGGBBAA)
    BG = 0x1E1E28FF
    TOPBAR = 0x2D2D3AFF
    CONTENTBG = 0x0F0F14FF
    TAB_BG = 0x404060FF

    # Registers for map offset
    REG_MAP_X = 0  # r0
    REG_MAP_Y = 1  # r1

    # Static UI
    a.emit(OP.FILL, 0, 0, 640, 480, BG)
    a.emit(OP.FILL, 0, 0, 640, 40, TOPBAR)
    a.emit(OP.FILL, 18, 58, 604, 364, TAB_BG)
    a.emit(OP.FILL, 20, 60, 600, 360, CONTENTBG)

    # Title and tabs
    text_at(a, 10, 12, "pxweb -- pxmap://0,0 [1] Home [2] Docs [3] About")

    # Main loop
    loop_start = len(a.code)
    a.emit(OP.READ_KEY, 2)  # Use r2 for key input to not conflict with map regs

    # Page switching
    a.emit(OP.CMP, 2, ord('1')); j1 = len(a.code); a.emit(OP.JZ, 0)
    a.emit(OP.CMP, 2, ord('2')); j2 = len(a.code); a.emit(OP.JZ, 0)
    a.emit(OP.CMP, 2, ord('3')); j3 = len(a.code); a.emit(OP.JZ, 0)

    # Map panning (WASD)
    a.emit(OP.CMP, 2, ord('w')); j_up = len(a.code); a.emit(OP.JZ, 0)
    a.emit(OP.CMP, 2, ord('a')); j_left = len(a.code); a.emit(OP.JZ, 0)
    a.emit(OP.CMP, 2, ord('s')); j_down = len(a.code); a.emit(OP.JZ, 0)
    a.emit(OP.CMP, 2, ord('d')); j_right = len(a.code); a.emit(OP.JZ, 0)

    a.emit(OP.JMP, loop_start)

    # Page: Home
    page1_pos = len(a.code)
    a.emit(OP.FILL, 20, 60, 600, 360, CONTENTBG)
    text_at(a, 30, 70, "Home - Welcome to pxweb")
    text_at(a, 30, 86, "Press 1/2/3 to switch pages. Use WASD to pan map.")
    a.emit(OP.JMP, loop_start)

    # Page: Docs
    page2_pos = len(a.code)
    a.emit(OP.FILL, 20, 60, 600, 360, CONTENTBG)
    text_at(a, 30, 70, "Docs - PXOS Quick Tour")
    text_at(a, 30, 86, "- MAILBOX protocol for I/O")
    text_at(a, 30, 102, "- PXL1 cartridge format")
    a.emit(OP.JMP, loop_start)

    # Page: About
    page3_pos = len(a.code)
    a.emit(OP.FILL, 20, 60, 600, 360, CONTENTBG)
    text_at(a, 30, 70, "About - pxweb")
    text_at(a, 30, 86, "Pixel-native browser for PXOS.")
    a.emit(OP.JMP, loop_start)

    # Map Panning Handlers
    # Note: Panning isn't visualized yet, just updating registers
    pan_up_pos = len(a.code)
    a.emit(OP.SUB, REG_MAP_Y, 10); a.emit(OP.JMP, loop_start)

    pan_left_pos = len(a.code)
    a.emit(OP.SUB, REG_MAP_X, 10); a.emit(OP.JMP, loop_start)

    pan_down_pos = len(a.code)
    a.emit(OP.ADD, REG_MAP_Y, 10); a.emit(OP.JMP, loop_start)

    pan_right_pos = len(a.code)
    a.emit(OP.ADD, REG_MAP_X, 10); a.emit(OP.JMP, loop_start)

    # Backpatch jump targets
    a.code[j1] = (OP.JZ, [page1_pos, 0, 0, 0, 0])
    a.code[j2] = (OP.JZ, [page2_pos, 0, 0, 0, 0])
    a.code[j3] = (OP.JZ, [page3_pos, 0, 0, 0, 0])
    a.code[j_up] = (OP.JZ, [pan_up_pos, 0, 0, 0, 0])
    a.code[j_left] = (OP.JZ, [pan_left_pos, 0, 0, 0, 0])
    a.code[j_down] = (OP.JZ, [pan_down_pos, 0, 0, 0, 0])
    a.code[j_right] = (OP.JZ, [pan_right_pos, 0, 0, 0, 0])

    return a.assemble()
