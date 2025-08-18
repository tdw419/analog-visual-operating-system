#!/usr/bin/env python3
# PXOS v0.1 - Cleaned with fixes + SET_POOLPOS enhancement

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional
import struct

# ===== Opcodes (extended set) =====
class OP:
    HALT=0x00
    PXSET=0x01
    FILL=0x02
    TEXT=0x10          # TEXT x,y,len (len bytes starting at pool_pos)
    SET_POOLPOS=0x12   # SET_POOLPOS idx
    LD=0x06            # LD r, addr
    ST=0x07            # ST addr, imm
    CMP=0x09           # CMP a,b (reg if <8 else imm)
    JMP=0x0A
    JZ=0x0B
    JNZ=0x0C
    JL=0x0D            # signed <
    JG=0x0E            # signed >
    READ_KEY=0x0F
    # arithmetic
    ADD=0x20
    SUB=0x21
    MUL=0x22
    MOV=0x23
    MOD=0x29
    # unsigned comparisons
    JB=0x30            # unsigned <
    JA=0x31            # unsigned >

# ===== Memory map =====
class MEM:
    # Editor-ish state
    CUR_X   = 0x0100
    CUR_Y   = 0x0101
    DIRTY   = 0x0103
    FRAME   = 0x0104

    # MAILBOX v0 (must be contiguous 4 bytes)
    MAILBOX_BASE = 0x1900  # +0 CMD, +1 ARG, +2 X, +3 Y

    # Screen layout
    EDITOR_X=20; EDITOR_Y=60; EDITOR_W=600; EDITOR_H=360

# ===== MAILBOX constants =====
CMD_NOP=0x00
CMD_KEY=0x01
CMD_MOUSECLICK=0x02  # ignored in v0

# ===== 5x5 bitmap font =====
FONT_5X5 = {
    ord(' '): [0x00,0x00,0x00,0x00,0x00], ord('!'): [0x04,0x04,0x04,0x00,0x04],
    ord('"'): [0x0a,0x0a,0x00,0x00,0x00], ord('#'): [0x0a,0x1f,0x0a,0x1f,0x0a],
    ord('$'): [0x04,0x0f,0x14,0x0e,0x05], ord('%'): [0x18,0x19,0x02,0x04,0x13],
    ord('&'): [0x0c,0x12,0x14,0x09,0x16], ord("'"): [0x04,0x04,0x00,0x00,0x00],
    ord('('): [0x02,0x04,0x04,0x04,0x02], ord(')'): [0x08,0x04,0x04,0x04,0x08],
    ord('*'): [0x00,0x0a,0x04,0x0a,0x00], ord('+'): [0x00,0x04,0x0e,0x04,0x00],
    ord(','): [0x00,0x00,0x00,0x04,0x08], ord('-'): [0x00,0x00,0x0e,0x00,0x00],
    ord('.'): [0x00,0x00,0x00,0x00,0x04], ord('/'): [0x01,0x02,0x04,0x08,0x10],
    ord('0'): [0x0e,0x11,0x13,0x15,0x0e], ord('1'): [0x04,0x0c,0x04,0x04,0x0e],
    ord('2'): [0x0e,0x11,0x02,0x04,0x1f], ord('3'): [0x1f,0x02,0x06,0x01,0x1e],
    ord('4'): [0x02,0x06,0x0a,0x1f,0x02], ord('5'): [0x1f,0x10,0x1e,0x01,0x1e],
    ord('6'): [0x06,0x08,0x1e,0x11,0x0e], ord('7'): [0x1f,0x01,0x02,0x04,0x04],
    ord('8'): [0x0e,0x11,0x0e,0x11,0x0e], ord('9'): [0x0e,0x11,0x0f,0x02,0x0c],
    ord(':'): [0x00,0x04,0x00,0x04,0x00], ord(';'): [0x00,0x04,0x00,0x04,0x08],
    ord('<'): [0x02,0x04,0x08,0x04,0x02], ord('='): [0x00,0x0e,0x00,0x0e,0x00],
    ord('>'): [0x08,0x04,0x02,0x04,0x08], ord('?'): [0x0e,0x11,0x02,0x00,0x04],
    ord('@'): [0x0e,0x11,0x17,0x15,0x0e], ord('A'): [0x0e,0x11,0x1f,0x11,0x11],
    ord('B'): [0x1e,0x11,0x1e,0x11,0x1e], ord('C'): [0x0e,0x11,0x10,0x11,0x0e],
    ord('D'): [0x1c,0x12,0x11,0x12,0x1c], ord('E'): [0x1f,0x10,0x1e,0x10,0x1f],
    ord('F'): [0x1f,0x10,0x1e,0x10,0x10], ord('G'): [0x0e,0x11,0x17,0x11,0x0f],
    ord('H'): [0x11,0x11,0x1f,0x11,0x11], ord('I'): [0x0e,0x04,0x04,0x04,0x0e],
    ord('J'): [0x07,0x02,0x02,0x12,0x0c], ord('K'): [0x11,0x12,0x1c,0x12,0x11],
    ord('L'): [0x10,0x10,0x10,0x10,0x1f], ord('M'): [0x11,0x1b,0x15,0x11,0x11],
    ord('N'): [0x11,0x19,0x15,0x13,0x11], ord('O'): [0x0e,0x11,0x11,0x11,0x0e],
    ord('P'): [0x1e,0x11,0x1e,0x10,0x10], ord('Q'): [0x0e,0x11,0x15,0x12,0x0d],
    ord('R'): [0x1e,0x11,0x1e,0x14,0x12], ord('S'): [0x0f,0x10,0x0e,0x01,0x1e],
    ord('T'): [0x1f,0x04,0x04,0x04,0x04], ord('U'): [0x11,0x11,0x11,0x11,0x0e],
    ord('V'): [0x11,0x11,0x11,0x0a,0x04], ord('W'): [0x11,0x11,0x15,0x1b,0x11],
    ord('X'): [0x11,0x0a,0x04,0x0a,0x11], ord('Y'): [0x11,0x0a,0x04,0x04,0x04],
    ord('Z'): [0x1f,0x02,0x04,0x08,0x1f], ord('['): [0x0e,0x08,0x08,0x08,0x0e],
    ord('\\'):[0x10,0x08,0x04,0x02,0x01], ord(']'): [0x0e,0x02,0x02,0x02,0x0e],
    ord('^'): [0x04,0x0a,0x11,0x00,0x00], ord('_'): [0x00,0x00,0x00,0x00,0x1f],
}

# ===== Cartridge builder =====
class CartBuilder:
    def __init__(self):
        self.code: List[Tuple[int,List[int]]] = []
        self.pool: bytearray = bytearray()

    def emit(self, op:int, *args:int)->None:
        self.code.append((op, list(args)))

    def str_id(self, s:str)->int:
        start = len(self.pool)
        self.pool += s.encode('ascii') + b'\x00'
        return start

    def assemble(self)->bytes:
        out = bytearray()
        out += struct.pack('<4sII', b'PXL1', len(self.code), len(self.pool))
        for op,args in self.code:
            out += struct.pack('<I', op)
            for a in args:
                out += struct.pack('<I', a)
        out += self.pool
        return bytes(out)

# ===== Runner =====
@dataclass
class VMConfig:
    width:int=640
    height:int=480
    mem_size:int=0x20000

class StrictRunner:
    def __init__(self, cfg:VMConfig=VMConfig()):
        self.cfg = cfg
        self.mem = [0]*(cfg.mem_size)
        self.reg = [0]*8
        self.pc = 0
        self.running = False
        self.code: List[Tuple[int,List[int]]] = []
        self.pool: bytes = b''
        self.pool_pos = 0
        self.zero = False
        self.less_signed = False
        self.less_unsigned = False
        self.fb = [[[0,0,0,255] for _ in range(cfg.width)] for __ in range(cfg.height)]
        self.last_key = 0

    def mb_read(self)->Optional[Tuple[int,int,int,int]]:
        i = MEM.MAILBOX_BASE
        cmd = self.mem[i]
        if cmd == CMD_NOP: return None
        arg, x, y = self.mem[i+1], self.mem[i+2], self.mem[i+3]
        self.mem[i] = CMD_NOP
        return (cmd,arg,x,y)

    def _argc(self, op:int)->int:
        return {
            OP.HALT:0, OP.PXSET:3, OP.FILL:5, OP.TEXT:3, OP.SET_POOLPOS:1,
            OP.LD:2, OP.ST:2, OP.CMP:2, OP.JMP:1, OP.JZ:1, OP.JNZ:1,
            OP.JL:1, OP.JG:1, OP.JB:1, OP.JA:1, OP.READ_KEY:1,
            OP.ADD:2, OP.SUB:2, OP.MUL:2, OP.MOV:2, OP.MOD:2
        }.get(op, 0)

    def load_cart_bytes(self, data:bytes)->None:
        if data[:4] != b'PXL1': raise ValueError("Bad cart magic")
        n_ops, pool_size = struct.unpack_from('<II', data, 4)
        off = 12
        self.code.clear()
        for _ in range(n_ops):
            (op,) = struct.unpack_from('<I', data, off); off += 4
            argc = self._argc(op)
            args = list(struct.unpack_from('<'+'I'*argc, data, off)) if argc else []
            off += 4*argc
            self.code.append((op,args))
        self.pool = data[off:off+pool_size]
        self.pool_pos = 0
        self.pc = 0
        self.running = True

    @staticmethod
    def _s32(x:int)->int:
        x &= 0xFFFFFFFF
        return x-0x100000000 if (x & 0x80000000) else x

    def _val(self, x:int)->int:
        return self.reg[x] if 0 <= x < 8 else x

    def _put(self, x:int,y:int,color:int)->None:
        if 0 <= x < self.cfg.width and 0 <= y < self.cfg.height:
            a = color & 0xFF; b = (color >> 8) & 0xFF; g = (color >> 16) & 0xFF; r = (color >> 24) & 0xFF
            self.fb[y][x] = [r,g,b,a]

    def _fill(self,x:int,y:int,w:int,h:int,color:int)->None:
        x0, y0 = max(0,x), max(0,y)
        x1, y1 = min(self.cfg.width, x+w), min(self.cfg.height, y+h)
        if x0>=x1 or y0>=y1: return
        a = color & 0xFF; b = (color >> 8) & 0xFF; g = (color >> 16) & 0xFF; r = (color >> 24) & 0xFF
        rowpix = [r,g,b,a]
        for yy in range(y0,y1):
            row = self.fb[yy]
            for xx in range(x0,x1): row[xx] = rowpix[:]

    def _text(self, x:int, y:int, length:int)->None:
        text_bytes = self.pool[self.pool_pos : self.pool_pos + length]
        chars_rendered = 0
        char_width, char_height = 6, 5
        for i, byte_val in enumerate(text_bytes):
            if byte_val == 0:
                chars_rendered = i + 1
                break

            char_x = x + i * char_width
            if char_x + 5 > self.cfg.width:
                chars_rendered = i
                break

            font_data = FONT_5X5.get(byte_val, [0x1f, 0x11, 0x11, 0x11, 0x1f])

            for row in range(char_height):
                if y + row >= self.cfg.height: break
                row_data = font_data[row]
                for col in range(5):
                    if char_x + col >= self.cfg.width: break
                    if row_data & (1 << (4-col)):
                        self._put(char_x + col, y + row, 0xFFFFFFFF)

            chars_rendered = i + 1

        # With SET_POOLPOS, we don't need to manually advance the pool position here,
        # as each text_at call will reset it. However, if TEXT were ever called
        # without a preceding SET_POOLPOS, this would be necessary.
        # For now, we rely on the text_at helper to manage the pool position.

    def export_png(self, filename:str)->None:
        try:
            from PIL import Image
            import numpy as np
            img = Image.fromarray(np.array(self.fb, dtype=np.uint8), 'RGBA')
            img.save(filename)
            print(f"Exported framebuffer to {filename}")
        except ImportError: print("PIL/numpy not available. pip install Pillow numpy")
        except Exception as e: print(f"Export failed: {e}")

    def step(self)->None:
        op,args = self.code[self.pc]
        def jump(to:int): self.pc = to-1
        if op == OP.HALT: self.running = False
        elif op == OP.PXSET: x,y,c = args; self._put(x,y,c)
        elif op == OP.FILL: x,y,w,h,c = args; self._fill(x,y,w,h,c)
        elif op == OP.TEXT: x,y,L = args; self._text(x,y,L)
        elif op == OP.SET_POOLPOS: (idx,) = args; self.pool_pos = min(idx, len(self.pool))
        elif op == OP.LD: r, addr = args; self.reg[r] = self.mem[addr] if 0<=addr<len(self.mem) else 0
        elif op == OP.ST: addr, imm = args; self.mem[addr] = imm & 0xFFFFFFFF
        elif op == OP.CMP:
            a,b = self._val(args[0]), self._val(args[1])
            self.zero = (a == b)
            self.less_unsigned = ((a & 0xFFFFFFFF) < (b & 0xFFFFFFFF))
            self.less_signed = (self._s32(a) < self._s32(b))
        elif op == OP.JMP: (to,) = args; jump(to)
        elif op == OP.JZ: (to,) = args; self.zero and jump(to)
        elif op == OP.JNZ: (to,) = args; not self.zero and jump(to)
        elif op == OP.JL: (to,) = args; self.less_signed and jump(to)
        elif op == OP.JG: (to,) = args; not self.less_signed and not self.zero and jump(to)
        elif op == OP.JB: (to,) = args; self.less_unsigned and jump(to)
        elif op == OP.JA: (to,) = args; not self.less_unsigned and not self.zero and jump(to)
        elif op == OP.READ_KEY:
            (dst,) = args
            evt = self.mb_read()
            if evt and evt[0]==CMD_KEY: self.last_key = evt[1] & 0xFF
            self.reg[dst] = self.last_key
            self.last_key = 0
        elif op == OP.ADD: r,v = args; self.reg[r] = (self.reg[r] + self._val(v)) & 0xFFFFFFFF
        elif op == OP.SUB: r,v = args; self.reg[r] = (self.reg[r] - self._val(v)) & 0xFFFFFFFF
        elif op == OP.MUL: r,v = args; self.reg[r] = (self.reg[r] * self._val(v)) & 0xFFFFFFFF
        elif op == OP.MOV: d,s = args; self.reg[d] = self._val(s)
        elif op == OP.MOD: r,den = args; self.reg[r] = self.reg[r] % (self._val(den) or 1)
        else: self.running = False; raise RuntimeError(f"Unknown opcode {op:#x} at pc={self.pc}")

    def run(self, max_steps:int=100000)->int:
        steps=0
        while self.running and 0<=self.pc<len(self.code) and steps<max_steps:
            self.step()
            self.pc += 1
            steps += 1
        return steps

def mb_write_key(mem:List[int], keycode:int)->None:
    i = MEM.MAILBOX_BASE
    mem[i:i+4] = [CMD_KEY, keycode & 0xFF, 0, 0]

def text_at(a: CartBuilder, x:int, y:int, s:str):
    idx = a.str_id(s)
    a.emit(OP.SET_POOLPOS, idx)
    a.emit(OP.TEXT, x, y, len(s))

def build_bootstrap()->bytes:
    a = CartBuilder()
    # Background + title bar
    a.emit(OP.FILL, 0,0, 640,480, 0x1E1E28FF)
    a.emit(OP.FILL, 0,0, 640,40,  0x2D2D3AFF)
    # Status strip
    a.emit(OP.FILL, 0,460,640,20, 0x2D2D3AFF)

    # Title and text using helper
    text_at(a, 10, 12, "[PXOS v0.1] F9=Assemble  F10=Run")
    text_at(a, 10, 465, "Ready. Use F9/F10 keys to test.")
    text_at(a, 10, 50, "This is PXOS v0.1 - a minimal pixel-based OS")

    # Main loop: wait for key, react to F9/F10, keep looping
    loop = len(a.code)
    a.emit(OP.READ_KEY, 0)           # reg0 = last_key; clears after read

    # if key==F9 (0x78)
    a.emit(OP.CMP, 0, 0x78)
    j_f9 = len(a.code);  a.emit(OP.JZ, 0)
    # if key==F10 (0x79)
    a.emit(OP.CMP, 0, 0x79)
    j_f10 = len(a.code); a.emit(OP.JZ, 0)
    # else -> loop
    a.emit(OP.JMP, loop)

    # --- F9 handler ---
    f9_handler = len(a.code)
    text_at(a, 300, 12, "[F9] Assembling code... (demo)")
    a.emit(OP.JMP, loop)

    # --- F10 handler ---
    f10_handler = len(a.code)
    text_at(a, 300, 12, "[F10] Running code... (demo)")
    a.emit(OP.JMP, loop)

    # Backpatch jump targets
    a.code[j_f9]  = (OP.JZ, [f9_handler])
    a.code[j_f10] = (OP.JZ, [f10_handler])

    return a.assemble()

if __name__ == "__main__":
    print("PXOS v0.1 - Cleaned with enhancements")
    cart = build_bootstrap()
    vm = StrictRunner()
    vm.load_cart_bytes(cart)
    print(f"Loaded cart: {len(vm.code)} opcodes, {len(vm.pool)} pool bytes")
    mb_write_key(vm.mem, 0x78)
    vm.run(2000)
    mb_write_key(vm.mem, 0x79)
    vm.run(2000)
    vm.export_png("pxos_screenshot.png")
    print("Test complete! Check pxos_screenshot.png")
