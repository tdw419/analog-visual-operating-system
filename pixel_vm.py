#!/usr/bin/env python3
"""
PixelVM: a tiny pixel-program virtual machine.

You author a program as an image. Each pixel encodes an instruction (and sometimes
an immediate "word" following it). The VM scans the image left-to-right, top-to-bottom
(row-major), and executes a small stack-based ISA.

- Works with PPM (P3 ASCII) natively (no deps) and with PNG if Pillow is installed.
- Includes an assembler to build programs from Python tuples and save to PPM/PNG.
- CLI:
    Run a pixel program:
        python pixel_vm.py run path/to/program.ppm
    Assemble an example (2 + 3 * 4 -> print 14):
        python pixel_vm.py assemble example_addmul.ppm
    Assemble from a small Python list demo (see __main__):

ISA (stack machine)
-------------------
Palette (exact RGBs):
  NOP    : (0,0,0)
  HALT   : (255,255,255)
  PUSHI  : (0,0,255)      # next word = signed 24-bit immediate (RGB two's complement)
  ADD    : (0,255,0)
  SUB    : (255,0,0)
  MUL    : (255,128,0)
  DIV    : (0,255,255)
  DUP    : (128,128,128)
  SWAP   : (255,0,255)
  PRINT  : (255,255,0)
  LOAD   : (0,0,128)      # next word = var index (0..16M-1) as 24-bit
  STORE  : (0,128,0)      # next word = var index
  JMP    : (128,0,0)      # next word = absolute IP (word index) as 24-bit
  JZ     : (0,128,128)    # jump if top == 0  (pops it)
  JNZ    : (128,128,0)    # jump if top != 0  (pops it)

Encoding of 24-bit signed integer in one pixel (R,G,B):
- value -> v (range -2^23..2^23-1)
- if v < 0: v = (1<<24) + v  (two's complement)
- R = v & 0xFF; G = (v>>8)&0xFF; B = (v>>16)&0xFF
- To decode, compose v, if v >= 2^23 then v -= 2^24

Author: you
"""
from __future__ import annotations

import sys, os, math, argparse
from typing import List, Tuple, Dict, Optional

# --- Palette (exact RGB) ---
NOP   = (0,0,0)
HALT  = (255,255,255)
PUSHI = (0,0,255)
ADD   = (0,255,0)
SUB   = (255,0,0)
MUL   = (255,128,0)
DIV   = (0,255,255)
MOD   = (128,0,255)
DUP   = (128,128,128)
SWAP  = (255,0,255)
PRINT = (255,255,0)
LOAD  = (0,0,128)
STORE = (0,128,0)
JMP   = (128,0,0)
JZ    = (0,128,128)
JNZ   = (128,128,0)

OPCODES = {
    NOP:   ('NOP',   0),
    HALT:  ('HALT',  0),
    PUSHI: ('PUSHI', 1),
    ADD:   ('ADD',   0),
    SUB:   ('SUB',   0),
    MUL:   ('MUL',   0),
    DIV:   ('DIV',   0),
    MOD:   ('MOD',   0),
    DUP:   ('DUP',   0),
    SWAP:  ('SWAP',  0),
    PRINT: ('PRINT', 0),
    LOAD:  ('LOAD',  1),
    STORE: ('STORE', 1),
    JMP:   ('JMP',   1),
    JZ:    ('JZ',    1),
    JNZ:   ('JNZ',   1),
}

# --- Utility: 24-bit signed value <-> RGB ---
def int_to_rgb24(v: int) -> Tuple[int,int,int]:
    if not (- (1<<23) <= v < (1<<23)):
        raise ValueError("Immediate out of 24-bit signed range")
    if v < 0:
        v = (1<<24) + v
    r = v & 0xFF
    g = (v>>8) & 0xFF
    b = (v>>16) & 0xFF
    return (r,g,b)

def rgb24_to_int(r:int,g:int,b:int) -> int:
    v = (b<<16) | (g<<8) | r
    if v >= (1<<23):
        v -= (1<<24)
    return v

# --- Image I/O ---
def load_image_pixels(path: str) -> Tuple[int,int,List[Tuple[int,int,int]]]:
    """
    Returns (width, height, pixels) where pixels is a flat list of (R,G,B) in row-major order.
    Supports PPM P3 ASCII natively. If Pillow is available, also supports PNG and others.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == '.ppm':
        return _load_ppm_p3(path)
    # Try Pillow for other formats
    try:
        from PIL import Image
    except Exception:
        raise RuntimeError("Non-PPM image provided but Pillow is not available. Install pillow or use .ppm (P3).")
    img = Image.open(path).convert('RGB')
    w,h = img.size
    pixels = list(img.getdata())
    return w,h,pixels

def save_image_pixels(path: str, w:int, h:int, pixels: List[Tuple[int,int,int]]) -> None:
    ext = os.path.splitext(path)[1].lower()
    if ext == '.ppm':
        _save_ppm_p3(path, w, h, pixels)
        return
    try:
        from PIL import Image
        img = Image.new('RGB', (w,h))
        img.putdata(pixels)
        img.save(path)
    except Exception as e:
        raise RuntimeError(f"Saving {path} failed; try .ppm instead. {e}")

def _load_ppm_p3(path: str) -> Tuple[int,int,List[Tuple[int,int,int]]]:
    with open(path, 'r') as f:
        toks = []
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            toks.extend(line.split())
    if not toks or toks[0] != 'P3':
        raise ValueError("PPM must be ASCII P3 format")
    i = 1
    w = int(toks[i]); i+=1
    h = int(toks[i]); i+=1
    maxv = int(toks[i]); i+=1
    if maxv <= 0 or maxv > 255:
        raise ValueError("PPM max value must be 1..255")
    vals = list(map(int, toks[i:]))
    if len(vals) != w*h*3:
        raise ValueError("PPM pixel data length mismatch")
    pixels = [(vals[j], vals[j+1], vals[j+2]) for j in range(0, len(vals), 3)]
    return w,h,pixels

def _save_ppm_p3(path: str, w:int, h:int, pixels: List[Tuple[int,int,int]]) -> None:
    with open(path, 'w') as f:
        f.write(f"P3\n{w} {h}\n255\n")
        c = 0
        for (r,g,b) in pixels:
            f.write(f"{r} {g} {b} ")
            c += 1
            if c % 5 == 0:
                f.write("\n")

# --- Decoder: exact match with small tolerance option ---
def nearest_opcode(rgb: Tuple[int,int,int], tol: int = 0) -> Optional[Tuple[str,int]]:
    if tol <= 0:
        return OPCODES.get(rgb, None)
    best = None
    bestd = 999999
    for key, val in OPCODES.items():
        d = abs(key[0]-rgb[0]) + abs(key[1]-rgb[1]) + abs(key[2]-rgb[2])
        if d < bestd:
            bestd = d
            best = val
    return best if bestd <= tol else None

# --- VM ---
class PixelVM:
    def __init__(self, pixels: List[Tuple[int,int,int]], width:int, height:int, tol:int=0):
        self.pixels = pixels
        self.width = width
        self.height = height
        self.ip = 0  # instruction pointer (word index)
        self.stack: List[int] = []
        self.vars: Dict[int,int] = {}
        self.tol = tol
        self.halted = False

    def fetch(self) -> Tuple[str, Optional[int]]:
        if self.ip >= len(self.pixels):
            return ('HALT', None)
        rgb = self.pixels[self.ip]
        info = nearest_opcode(rgb, self.tol)
        if info is None:
            raise RuntimeError(f"Unknown opcode color at word {self.ip}: {rgb}")
        name, nargs = info
        imm = None
        if nargs == 1:
            if self.ip+1 >= len(self.pixels):
                raise RuntimeError("Truncated immediate")
            r,g,b = self.pixels[self.ip+1]
            imm = rgb24_to_int(r,g,b)
        return (name, imm)

    def step(self) -> None:
        name, imm = self.fetch()
        # advance ip by words consumed (1 or 2)
        consumed = 1 + (1 if imm is not None and name in ('PUSHI','LOAD','STORE','JMP','JZ','JNZ') else 0)
        self.ip += consumed

        if name == 'NOP':
            return
        if name == 'HALT':
            self.halted = True
            return
        if name == 'PUSHI':
            self.stack.append(imm)
            return
        if name == 'ADD':
            b = self.stack.pop(); a = self.stack.pop(); self.stack.append(a+b); return
        if name == 'SUB':
            b = self.stack.pop(); a = self.stack.pop(); self.stack.append(a-b); return
        if name == 'MUL':
            b = self.stack.pop(); a = self.stack.pop(); self.stack.append(a*b); return
        if name == 'DIV':
            b = self.stack.pop(); a = self.stack.pop(); self.stack.append(int(a/b)); return
        if name == 'MOD':
            b = self.stack.pop(); a = self.stack.pop(); self.stack.append(a % b); return
        if name == 'DUP':
            self.stack.append(self.stack[-1]); return
        if name == 'SWAP':
            self.stack[-1], self.stack[-2] = self.stack[-2], self.stack[-1]; return
        if name == 'PRINT':
            v = self.stack.pop(); print(v); return
        if name == 'LOAD':
            idx = imm
            self.stack.append(self.vars.get(idx, 0)); return
        if name == 'STORE':
            idx = imm
            val = self.stack.pop(); self.vars[idx] = val; return
        if name == 'JMP':
            self.ip = imm; return
        if name == 'JZ':
            v = self.stack.pop()
            if v == 0:
                self.ip = imm
            return
        if name == 'JNZ':
            v = self.stack.pop()
            if v != 0:
                self.ip = imm
            return

        raise RuntimeError(f"Unhandled opcode {name}")

    def run(self, max_steps:int=100000):
        steps = 0
        while not self.halted and steps < max_steps:
            self.step()
            steps += 1
        if steps >= max_steps:
            raise RuntimeError("Max steps exceeded (infinite loop?)")

# --- Assembler ---
OP_RGB = {
    'NOP': NOP, 'HALT': HALT, 'PUSHI': PUSHI, 'ADD': ADD, 'SUB': SUB, 'MUL': MUL, 'DIV': DIV,
    'MOD': MOD,
    'DUP': DUP, 'SWAP': SWAP, 'PRINT': PRINT, 'LOAD': LOAD, 'STORE': STORE,
    'JMP': JMP, 'JZ': JZ, 'JNZ': JNZ
}

def assemble(program: List[Tuple], width:int=None) -> Tuple[int,int,List[Tuple[int,int,int]]]:
    """
    program: list of tuples, e.g. ('PUSHI', 2), ('PUSHI', 3), ('MUL',), ('PRINT',), ('HALT',)
    Returns: (w,h,pixels)
    """
    pixels: List[Tuple[int,int,int]] = []
    for ins in program:
        op = ins[0].upper()
        if op not in OP_RGB:
            raise ValueError(f"Unknown op {op}")
        pixels.append(OP_RGB[op])
        if op in ('PUSHI','LOAD','STORE','JMP','JZ','JNZ'):
            if len(ins) < 2:
                raise ValueError(f"{op} needs an immediate")
            imm = int(ins[1])
            pixels.append(int_to_rgb24(imm))
    # shape the image
    n = len(pixels)
    if width is None:
        width = min(64, n)  # simple wrap
    height = (n + width - 1) // width
    # pad with NOPs to fill rectangle
    total = width*height
    if total > n:
        pixels.extend([NOP] * (total - n))
    return width, height, pixels

def assemble_to_file(program: List[Tuple], path:str, width:int=None):
    w,h,pix = assemble(program, width=width)
    save_image_pixels(path, w, h, pix)

# --- CLI ---
def main():
    ap = argparse.ArgumentParser(description="PixelVM runner / assembler")
    sub = ap.add_subparsers(dest='cmd', required=True)

    runp = sub.add_parser('run', help='Run a pixel program image')
    runp.add_argument('image', help='Path to .ppm (P3) or .png')
    runp.add_argument('--tol', type=int, default=0, help='Color tolerance (for hand-edited images)')

    asmp = sub.add_parser('assemble', help='Assemble a tiny demo or from hardcoded example')
    asmp.add_argument('out', help='Output image (.ppm or .png)')
    asmp.add_argument('--demo', choices=['addmul','sum1to5', 'mod_test'], default='addmul')
    asmp.add_argument('--width', type=int, default=None)

    args = ap.parse_args()

    if args.cmd == 'run':
        w,h,pixels = load_image_pixels(args.image)
        vm = PixelVM(pixels, w, h, tol=args.tol)
        vm.run()
        return

    if args.cmd == 'assemble':
        if args.demo == 'addmul':
            prog = [
                ('PUSHI', 2),
                ('PUSHI', 3),
                ('PUSHI', 4),
                ('MUL',),
                ('ADD',),
                ('PRINT',),
                ('HALT',),
            ]
        elif args.demo == 'mod_test':
            prog = [
                ('PUSHI', 10),
                ('PUSHI', 3),
                ('MOD',),
                ('PRINT',),
                ('HALT',),
            ]
        else:  # sum1to5
            # sum = 0; i = 1; while i <= 5: sum += i; i += 1; print(sum)
            # We'll use var 0 for sum, var 1 for i
            # Layout with labels (addresses computed after assembly; here we compute manually by positions)
            # We'll assemble linear then fill jump addresses.
            prog = [
                ('PUSHI', 0), ('STORE', 0),       # sum = 0
                ('PUSHI', 1), ('STORE', 1),       # i = 1
                # loop_start:
                ('LOAD', 1), ('PUSHI', 5), ('SUB',),    # i - 5
                ('JZ', 0),                         # if i-5 == 0 -> jump to end  (placeholder 0)
                # body:
                ('LOAD', 0), ('LOAD', 1), ('ADD',), ('STORE', 0),  # sum += i
                ('LOAD', 1), ('PUSHI', 1), ('ADD',), ('STORE', 1), # i += 1
                ('JMP', 0),                       # jump to loop_start (placeholder 0)
                # end:
                ('LOAD', 0), ('PRINT',), ('HALT',),
            ]
            # Resolve labels by computing word indices
            # Compute instruction word offsets
            words = []
            for ins in prog:
                words.append(ins)
                if ins[0] in ('PUSHI','LOAD','STORE','JMP','JZ','JNZ'):
                    words.append(('IMM',))  # placeholder for word count

            # loop_start is at index after first 4 instructions (2*2 words) => word index 4? Let's compute properly.
            # Let's actually compute iteratively:
            ip = 0
            loop_start_ip = None
            jz_pos = None
            jmp_pos = None
            i = 0
            while i < len(prog):
                op = prog[i][0]
                if loop_start_ip is None and i == 4:  # after: (sum=0, i=1) => instruction index 4
                    loop_start_ip = ip
                if op in ('JZ','JMP','JNZ'):
                    if jz_pos is None and op == 'JZ':
                        jz_pos = ip
                    elif jmp_pos is None and op == 'JMP':
                        jmp_pos = ip
                # advance ip by words consumed by this instruction
                ip += 1 + (1 if op in ('PUSHI','LOAD','STORE','JMP','JZ','JNZ') else 0)
                i += 1
            # 'end' is the start ip of ('LOAD',0) before PRINT,HALT
            # Find that start ip by recomputing positions list
            positions = []
            ip = 0
            for ins in prog:
                positions.append(ip)
                ip += 1 + (1 if ins[0] in ('PUSHI','LOAD','STORE','JMP','JZ','JNZ') else 0)
            end_ip = positions[-3]  # ('LOAD',0) position

            # Patch the placeholders
            # Replace the ('JZ', 0) with correct end_ip
            for idx, ins in enumerate(prog):
                if ins[0] == 'JZ' and ins[1] == 0:
                    prog[idx] = ('JZ', end_ip)
                if ins[0] == 'JMP' and ins[1] == 0:
                    prog[idx] = ('JMP', loop_start_ip)

        assemble_to_file(prog, args.out, width=args.width)
        print(f"Wrote {args.out}")

if __name__ == '__main__':
    main()
