#!/usr/bin/env python3
# PXOS v0.1 - Final Cleaned Version with All Fixes & Enhancements

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional
import struct
import numpy as np
from PIL import Image

# ===== Constants =====
class VK:
    F9 = 0x78
    F10 = 0x79

# ===== Opcodes =====
class OP:
    HALT=0x00
    PXSET=0x01
    FILL=0x02
    TEXT=0x10
    SET_POOLPOS=0x12
    LD=0x06
    ST=0x07
    CMP=0x09
    JMP=0x0A
    JZ=0x0B
    JNZ=0x0C
    JL=0x0D  # signed <
    JG=0x0E  # signed >
    READ_KEY=0x0F
    ADD=0x20
    SUB=0x21
    MUL=0x22
    MOV=0x23
    MOD=0x29
    JB=0x30  # unsigned <
    JA=0x31  # unsigned >

# ===== Memory Map =====
class MEM:
    CUR_X   = 0x0100
    CUR_Y   = 0x0101
    DIRTY   = 0x0103
    FRAME   = 0x0104
    MAILBOX_BASE = 0x1900
    EDITOR_X=20; EDITOR_Y=60; EDITOR_W=600; EDITOR_H=360

# ===== MAILBOX =====
CMD_NOP=0x00
CMD_KEY=0x01
CMD_MOUSECLICK=0x02

# ===== True 5x7 bitmap font =====
FONT_5X7 = {
    ord(' '): [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    ord('!'): [0x10, 0x10, 0x10, 0x10, 0x00, 0x10, 0x00],
    ord('"'): [0x14, 0x14, 0x00, 0x00, 0x00, 0x00, 0x00],
    ord('#'): [0x14, 0x14, 0x1F, 0x14, 0x14, 0x1F, 0x14],
    ord('$'): [0x04, 0x1E, 0x05, 0x0C, 0x1A, 0x0E, 0x04],
    ord('%'): [0x18, 0x19, 0x02, 0x04, 0x08, 0x13, 0x03],
    ord('&'): [0x0C, 0x12, 0x14, 0x0A, 0x12, 0x0D, 0x00],
    ord("'"): [0x04, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00],
    ord('('): [0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02],
    ord(')'): [0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08],
    ord('*'): [0x00, 0x00, 0x08, 0x1C, 0x08, 0x00, 0x00],
    ord('+'): [0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00],
    ord(','): [0x00, 0x00, 0x00, 0x00, 0x10, 0x08, 0x00],
    ord('-'): [0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00],
    ord('.'): [0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0x00],
    ord('/'): [0x02, 0x04, 0x08, 0x10, 0x00, 0x00, 0x00],
    ord('0'): [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    ord('1'): [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
    ord('2'): [0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F],
    ord('3'): [0x1F, 0x01, 0x02, 0x04, 0x04, 0x11, 0x0E],
    ord('4'): [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02],
    ord('5'): [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
    ord('6'): [0x0E, 0x10, 0x1E, 0x11, 0x11, 0x11, 0x0E],
    ord('7'): [0x1F, 0x01, 0x02, 0x04, 0x04, 0x04, 0x04],
    ord('8'): [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E],
    ord('9'): [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x01, 0x0E],
    ord(':'): [0x00, 0x04, 0x04, 0x00, 0x04, 0x04, 0x00],
    ord(';'): [0x00, 0x04, 0x04, 0x00, 0x04, 0x04, 0x08],
    ord('<'): [0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02],
    ord('='): [0x00, 0x00, 0x1F, 0x00, 0x1F, 0x00, 0x00],
    ord('>'): [0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08],
    ord('?'): [0x0E, 0x11, 0x01, 0x02, 0x04, 0x00, 0x04],
    ord('@'): [0x0E, 0x11, 0x17, 0x15, 0x11, 0x11, 0x0E],
    ord('A'): [0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    ord('B'): [0x1F, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x1F],
    ord('C'): [0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E],
    ord('D'): [0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E],
    ord('E'): [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F],
    ord('F'): [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10],
    ord('G'): [0x0E, 0x11, 0x10, 0x13, 0x11, 0x11, 0x0E],
    ord('H'): [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    ord('I'): [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x1F],
    ord('J'): [0x01, 0x01, 0x01, 0x01, 0x01, 0x11, 0x0E],
    ord('K'): [0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11],
    ord('L'): [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F],
    ord('M'): [0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11],
    ord('N'): [0x11, 0x11, 0x19, 0x15, 0x13, 0x11, 0x11],
    ord('O'): [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    ord('P'): [0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10],
    ord('Q'): [0x0E, 0x11, 0x11, 0x15, 0x13, 0x11, 0x0E],
    ord('R'): [0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11],
    ord('S'): [0x0E, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E],
    ord('T'): [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04],
    ord('U'): [0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    ord('V'): [0x11, 0x11, 0x11, 0x11, 0x0A, 0x04, 0x04],
    ord('W'): [0x11, 0x11, 0x15, 0x1B, 0x15, 0x11, 0x11],
    ord('X'): [0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11],
    ord('Y'): [0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04],
    ord('Z'): [0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F],
    ord('['): [0x1F, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F],
    ord('\\'): [0x01, 0x02, 0x04, 0x08, 0x10, 0x10, 0x10],
    ord(']'): [0x1F, 0x01, 0x01, 0x01, 0x01, 0x01, 0x1F],
    ord('^'): [0x04, 0x0A, 0x11, 0x00, 0x00, 0x00, 0x00],
    ord('_'): [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1F],
    ord('`'): [0x04, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00],
    ord('a'): [0x00, 0x00, 0x0E, 0x01, 0x0F, 0x11, 0x0F],
    ord('b'): [0x10, 0x10, 0x1E, 0x11, 0x11, 0x11, 0x1E],
    ord('c'): [0x00, 0x00, 0x0E, 0x10, 0x10, 0x10, 0x0E],
    ord('d'): [0x01, 0x01, 0x0F, 0x11, 0x11, 0x11, 0x0F],
    ord('e'): [0x00, 0x00, 0x0E, 0x11, 0x1F, 0x10, 0x0E],
    ord('f'): [0x06, 0x08, 0x04, 0x1E, 0x04, 0x04, 0x04],
    ord('g'): [0x00, 0x00, 0x0E, 0x11, 0x0F, 0x01, 0x1E],
    ord('h'): [0x10, 0x10, 0x1E, 0x11, 0x11, 0x11, 0x11],
    ord('i'): [0x04, 0x00, 0x0C, 0x04, 0x04, 0x04, 0x0E],
    ord('j'): [0x02, 0x00, 0x06, 0x02, 0x02, 0x12, 0x0C],
    ord('k'): [0x10, 0x10, 0x12, 0x0A, 0x08, 0x12, 0x11],
    ord('l'): [0x1C, 0x04, 0x04, 0x04, 0x04, 0x04, 0x1E],
    ord('m'): [0x00, 0x00, 0x1A, 0x15, 0x15, 0x11, 0x11],
    ord('n'): [0x00, 0x00, 0x1E, 0x11, 0x11, 0x11, 0x11],
    ord('o'): [0x00, 0x00, 0x0E, 0x11, 0x11, 0x11, 0x0E],
    ord('p'): [0x00, 0x00, 0x1E, 0x11, 0x11, 0x1E, 0x10],
    ord('q'): [0x00, 0x00, 0x0F, 0x11, 0x11, 0x0F, 0x01],
    ord('r'): [0x00, 0x00, 0x1E, 0x11, 0x10, 0x10, 0x10],
    ord('s'): [0x00, 0x00, 0x0F, 0x10, 0x0E, 0x01, 0x1E],
    ord('t'): [0x08, 0x08, 0x1C, 0x08, 0x08, 0x08, 0x06],
    ord('u'): [0x00, 0x00, 0x11, 0x11, 0x11, 0x11, 0x0F],
    ord('v'): [0x00, 0x00, 0x11, 0x11, 0x11, 0x0A, 0x04],
    ord('w'): [0x00, 0x00, 0x11, 0x11, 0x15, 0x15, 0x0A],
    ord('x'): [0x00, 0x00, 0x11, 0x0A, 0x04, 0x0A, 0x11],
    ord('y'): [0x00, 0x00, 0x11, 0x11, 0x0F, 0x01, 0x1E],
    ord('z'): [0x00, 0x00, 0x1F, 0x02, 0x04, 0x08, 0x1F],
    ord('{'): [0x0C, 0x08, 0x08, 0x08, 0x08, 0x08, 0x0C],
    ord('|'): [0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04],
    ord('}'): [0x06, 0x02, 0x02, 0x02, 0x02, 0x02, 0x06],
    ord('~'): [0x00, 0x00, 0x00, 0x0A, 0x11, 0x00, 0x00],
    ord('•'): [0x00, 0x00, 0x00, 0x0E, 0x0E, 0x0E, 0x00]
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
            out += struct.pack(f'<{len(args)}I', *args)
        out += self.pool
        return bytes(out)

# ===== VM Runner =====
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
        self.code = []
        self.pool = b''
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
        return (cmd, arg, x, y)

    def _argc(self, op:int)->int:
        return {
            OP.HALT:0, OP.PXSET:3, OP.FILL:5, OP.TEXT:3, OP.SET_POOLPOS:1,
            OP.LD:2, OP.ST:2, OP.CMP:2, OP.JMP:1, OP.JZ:1, OP.JNZ:1,
            OP.JL:1, OP.JG:1, OP.JB:1, OP.JA:1, OP.READ_KEY:1,
            OP.ADD:2, OP.SUB:2, OP.MUL:2, OP.MOV:2, OP.MOD:2
        }.get(op, 0)

    def load_cart_bytes(self, data:bytes)->None:
        if data[:4] != b'PXL1':
            raise ValueError("Bad cart magic")
        n_ops, pool_size = struct.unpack_from('<II', data, 4)
        off = 12
        self.code.clear()
        for _ in range(n_ops):
            op = struct.unpack_from('<I', data, off)[0]; off +=4
            argc = self._argc(op)
            args = list(struct.unpack_from(f'<{argc}I', data, off)) if argc else []
            off += 4*argc
            self.code.append((op, args))
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
            a=color &0xFF; b=(color>>8)&0xFF; g=(color>>16)&0xFF; r=(color>>24)&0xFF
            self.fb[y][x] = [r,g,b,a]

    def _fill(self,x:int,y:int,w:int,h:int,color:int)->None:
        x0=max(0,x); y0=max(0,y)
        x1=min(self.cfg.width, x+w); y1=min(self.cfg.height, y+h)
        if x0>=x1 or y0>=y1: return
        a=color &0xFF; b=(color>>8)&0xFF; g=(color>>16)&0xFF; r=(color>>24)&0xFF
        rowpix = [r,g,b,a]
        for yy in range(y0,y1):
            for xx in range(x0,x1):
                self._put(xx, yy, color)

    def _text(self, x:int, y:int, length:int)->None:
        if self.pool_pos + length > len(self.pool): return
        text_bytes = self.pool[self.pool_pos:self.pool_pos + length]

        char_width = 6
        char_height = 7

        for i, byte_val in enumerate(text_bytes):
            if byte_val == 0: break
            char_x = x + i * char_width
            if char_x + 5 > self.cfg.width: break

            font_data = FONT_5X7.get(byte_val, FONT_5X7.get(ord('?')))

            for row in range(char_height):
                if y + row >= self.cfg.height: break
                row_data = font_data[row]
                for col in range(5):
                    if char_x + col >= self.cfg.width: break
                    if row_data & (1 << (4-col)):
                        self._put(char_x + col, y + row, 0xFFFFFFFF)

    def export_png(self, filename:str)->None:
        try:
            img = Image.new('RGBA', (self.cfg.width, self.cfg.height))
            img.putdata([tuple(px) for row in self.fb for px in row])
            img.save(filename)
            print(f"Exported framebuffer to {filename}")
        except ImportError:
            print("PIL not available - install with: pip install Pillow")
        except Exception as e:
            print(f"Export failed: {e}")

    def step(self)->None:
        op,args = self.code[self.pc]
        def jump(to:int): self.pc = to-1

        if op == OP.HALT: self.running = False
        elif op == OP.PXSET: x,y,c = args; self._put(x,y,c)
        elif op == OP.FILL: x,y,w,h,c = args; self._fill(x,y,w,h,c)
        elif op == OP.TEXT: x,y,L = args; self._text(x,y,L)
        elif op == OP.SET_POOLPOS: (idx,) = args; self.pool_pos = min(idx, len(self.pool))
        elif op == OP.LD: r, addr = args; self.reg[r] = self.mem[addr] if 0<=addr<len(self.mem) else 0
        elif op == OP.ST: addr, imm = args; self.mem[addr] = self._val(imm) & 0xFFFFFFFF
        elif op == OP.CMP:
            a,b = self._val(args[0]), self._val(args[1])
            self.zero = (a == b)
            self.less_unsigned = ((a & 0xFFFFFFFF) < (b & 0xFFFFFFFF))
            self.less_signed = (self._s32(a) < self._s32(b))
        elif op == OP.JMP: jump(args[0])
        elif op == OP.JZ: jump(args[0]) if self.zero else None
        elif op == OP.JNZ: jump(args[0]) if not self.zero else None
        elif op == OP.JL: jump(args[0]) if self.less_signed else None
        elif op == OP.JG: jump(args[0]) if not self.less_signed and not self.zero else None
        elif op == OP.JB: jump(args[0]) if self.less_unsigned else None
        elif op == OP.JA: jump(args[0]) if not self.less_unsigned and not self.zero else None
        elif op == OP.READ_KEY:
            (dst,) = args
            evt = self.mb_read()
            if evt and evt[0]==CMD_KEY: self.last_key = evt[1] & 0xFF
            self.reg[dst] = self.last_key
            self.last_key = 0
        elif op == OP.ADD: r,v = args; self.reg[r] = (self.reg[r] + self._val(v)) & 0xFFFFFFFF
        elif op == OP.SUB: r,v = args; self.reg[r] = (self.reg[r] - self._val(v)) & 0xFFFFFFFF
        elif op == OP.MUL: r,v = args; self.reg[r] = (self.reg[r] * self._val(v)) & 0xFFFFFFFF
        elif op == OP.MOV: d,s = args; self.reg[d] = self._val(s) if 0<=d<8 else 0
        elif op == OP.MOD: r,den = args; dv = self._val(den) or 1; self.reg[r] %= dv
        else: self.running = False; raise RuntimeError(f"Unknown opcode {op:#x} at pc={self.pc}")

    def run(self, max_steps:int=100000)->int:
        steps=0
        while self.running and 0<=self.pc<len(self.code) and steps<max_steps:
            self.step()
            self.pc +=1
            steps +=1
        return steps

# ===== Helpers =====
def mb_write_key(mem:List[int], keycode:int)->None:
    i = MEM.MAILBOX_BASE
    mem[i:i+4] = [CMD_KEY, keycode & 0xFF, 0, 0]

def text_at(a: CartBuilder, x:int, y:int, s:str):
    idx = a.str_id(s)
    a.emit(OP.SET_POOLPOS, idx)
    a.emit(OP.TEXT, x, y, len(s))

def jmp_here(a: CartBuilder, op: int = OP.JZ) -> int:
    idx = len(a.code)
    a.emit(op, 0)
    return idx

def patch(a: CartBuilder, at_idx: int, target: int):
    op, _ = a.code[at_idx]
    a.code[at_idx] = (op, [target])

# ===== Demo Cart =====
def build_bootstrap() -> bytes:
    a = CartBuilder()
    a.emit(OP.FILL, 0,0, 640,480, 0x1E1E28FF)
    a.emit(OP.FILL, 0,0, 640,40,  0x2D2D3AFF)
    text_at(a, 10, 12, "[PXOS v0.1] F9=Assemble  F10=Run")
    text_at(a, 10,465, "Ready. Use F9/F10 keys to test.")
    text_at(a, 10, 50, "This is PXOS v0.1 - a minimal pixel-based OS")
    loop = len(a.code)
    a.emit(OP.READ_KEY, 0)
    a.emit(OP.CMP, 0, VK.F9)
    j_f9 = jmp_here(a)
    a.emit(OP.CMP, 0, VK.F10)
    j_f10 = jmp_here(a)
    a.emit(OP.JMP, loop)
    f9_handler = len(a.code)
    text_at(a, 300, 12, "[F9] Assembling code... (demo)")
    a.emit(OP.JMP, loop)
    f10_handler = len(a.code)
    text_at(a, 300, 12, "[F10] Running code... (demo)")
    a.emit(OP.JMP, loop)
    patch(a, j_f9, f9_handler)
    patch(a, j_f10, f10_handler)
    return a.assemble()

# ===== Main =====
if __name__ == "__main__":
    print("PXOS v0.1 - Final Cleaned Version with Enhancements")
    cart = build_bootstrap()
    vm = StrictRunner()
    vm.load_cart_bytes(cart)
    mb_write_key(vm.mem, VK.F9)
    vm.run(2000)
    mb_write_key(vm.mem, VK.F10)
    vm.run(2000)
    vm.export_png("pxos_screenshot.png")
    print("Test complete! Check pxos_screenshot.png")
