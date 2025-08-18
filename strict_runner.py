# strict_runner.py
from typing import List, Tuple, Optional, Dict, Any
import struct

class OP:
    HALT = 0x00; PXSET = 0x01; FILL = 0x02
    TEXT = 0x10; SET_POOLPOS = 0x12
    LD = 0x06; ST = 0x07; CMP = 0x09
    JMP = 0x0A; JZ = 0x0B; JNZ = 0x0C; JL = 0x0D; JG = 0x0E; JB = 0x0F; JA = 0x11
    READ_KEY = 0x10
    ADD = 0x13; SUB = 0x14; MUL = 0x15; MOV = 0x16; MOD = 0x17

class MEM:
    MAILBOX_BASE = 0x1900
    PROFILE_BASE = 0x1A00

CMD_NOP = 0x00
CMD_KEY = 0x01

class VMConfig:
    def __init__(self, width=640, height=480, mem_size=0x10000):
        self.width = width
        self.height = height
        self.mem_size = mem_size

class StrictRunner:
    def __init__(self, cfg: VMConfig = VMConfig()):
        self.cfg = cfg
        self.mem = [0] * cfg.mem_size
        self.pc = 0
        self.running = False
        self.code: List[Tuple[int, List[int]]] = []
        self.pool: bytes = b''
        self.pool_pos = 0
        self.reg = [0] * 8
        self.fb = [[[0, 0, 0, 255] for _ in range(cfg.width)] for __ in range(cfg.height)]
        self.last_key = 0
        self.zero = False
        self.less_signed = False
        self.less_unsigned = False
        self.font = self.load_font()

    def load_font(self):
        # Simple 5x7 font placeholder
        # In a real scenario, this would load from a file e.g. font_5x7.py
        return {
            'A': [0x7E, 0x11, 0x11, 0x11, 0x7E], 'B': [0x7F, 0x49, 0x49, 0x49, 0x36],
            'C': [0x3E, 0x41, 0x41, 0x41, 0x22], 'D': [0x7F, 0x41, 0x41, 0x22, 0x1C],
            'E': [0x7F, 0x49, 0x49, 0x41, 0x41], 'F': [0x7F, 0x09, 0x09, 0x01, 0x01],
            'G': [0x3E, 0x41, 0x49, 0x49, 0x2E], 'H': [0x7F, 0x08, 0x08, 0x08, 0x7F],
            'I': [0x00, 0x41, 0x7F, 0x41, 0x00], 'J': [0x20, 0x40, 0x41, 0x3F, 0x01],
            'K': [0x7F, 0x08, 0x14, 0x22, 0x41], 'L': [0x7F, 0x40, 0x40, 0x40, 0x40],
            'M': [0x7F, 0x02, 0x0C, 0x02, 0x7F], 'N': [0x7F, 0x04, 0x08, 0x10, 0x7F],
            'O': [0x3E, 0x41, 0x41, 0x41, 0x3E], 'P': [0x7F, 0x09, 0x09, 0x09, 0x06],
            'Q': [0x3E, 0x41, 0x51, 0x21, 0x5E], 'R': [0x7F, 0x09, 0x19, 0x29, 0x46],
            'S': [0x26, 0x49, 0x49, 0x49, 0x32], 'T': [0x01, 0x01, 0x7F, 0x01, 0x01],
            'U': [0x3F, 0x40, 0x40, 0x40, 0x3F], 'V': [0x1F, 0x20, 0x40, 0x20, 0x1F],
            'W': [0x3F, 0x40, 0x38, 0x40, 0x3F], 'X': [0x63, 0x14, 0x08, 0x14, 0x63],
            'Y': [0x07, 0x08, 0x70, 0x08, 0x07], 'Z': [0x61, 0x51, 0x49, 0x45, 0x43],
            '0': [0x3E, 0x51, 0x49, 0x45, 0x3E], '1': [0x00, 0x21, 0x7F, 0x01, 0x00],
            '2': [0x21, 0x43, 0x45, 0x49, 0x31], '3': [0x22, 0x41, 0x49, 0x49, 0x36],
            '4': [0x18, 0x14, 0x12, 0x7F, 0x10], '5': [0x27, 0x45, 0x45, 0x45, 0x39],
            '6': [0x3C, 0x4A, 0x49, 0x49, 0x30], '7': [0x01, 0x71, 0x09, 0x05, 0x03],
            '8': [0x36, 0x49, 0x49, 0x49, 0x36], '9': [0x06, 0x49, 0x49, 0x29, 0x1E],
            ' ': [0x00, 0x00, 0x00, 0x00, 0x00],
            '.': [0x00, 0x60, 0x60, 0x00, 0x00], '-': [0x08, 0x08, 0x08, 0x08, 0x08],
            '[': [0x1C, 0x10, 0x10, 0x10, 0x1C], ']': [0x07, 0x01, 0x01, 0x01, 0x07], # Corrected to 5x5
            '/': [0x20, 0x10, 0x08, 0x04, 0x02],
            ':': [0x00, 0x36, 0x36, 0x00, 0x00],
        }

    def _val(self, x): return self.reg[x] if x < 8 else x
    def _s32(self, x): return x if x < 0x80000000 else x - 0x100000000

    def _put(self, x, y, c):
        if 0 <= x < self.cfg.width and 0 <= y < self.cfg.height:
            self.fb[y][x] = [(c >> 24) & 0xFF, (c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF]

    def _fill(self, x, y, w, h, c):
        for dy in range(h):
            for dx in range(w):
                self._put(x + dx, y + dy, c)

    def _text(self, x, y, length):
        s = self.pool[self.pool_pos:self.pool_pos + length].decode('ascii', errors='ignore')
        char_width = 6
        char_height = 5  # Temporarily changed to 5 to match the 5x5 font data
        for i, char in enumerate(s):
            if char.upper() in self.font:
                glyph = self.font[char.upper()]
                for row in range(char_height):
                    for col in range(5):
                        if (glyph[row] >> (4 - col)) & 1:
                            self._put(x + i * char_width + col, y + row, 0xFFFFFFFF)

    def mb_read(self) -> Optional[Tuple[int, int, int, int]]:
        i = MEM.MAILBOX_BASE
        cmd = self.mem[i]
        if cmd == CMD_NOP: return None
        arg, x, y = self.mem[i+1], self.mem[i+2], self.mem[i+3]
        self.mem[i] = CMD_NOP
        return (cmd, arg, x, y)

    def step(self) -> None:
        if not (0 <= self.pc < len(self.code)): self.running = False; return
        op, args = self.code[self.pc]
        self.pc += 1

        def jump(to: int): self.pc = to

        if op == OP.HALT: self.running = False
        elif op == OP.PXSET: self._put(args[0], args[1], args[2])
        elif op == OP.FILL: self._fill(args[0], args[1], args[2], args[3], args[4])
        elif op == OP.TEXT: self._text(args[0], args[1], args[2])
        elif op == OP.SET_POOLPOS: self.pool_pos = args[0]
        elif op == OP.LD: self.reg[args[0]] = self.mem[args[1]]
        elif op == OP.ST: self.mem[args[0]] = self._val(args[1])
        elif op == OP.CMP:
            a, b = self._val(args[0]), self._val(args[1])
            self.zero = (a == b)
            self.less_signed = (self._s32(a) < self._s32(b))
            self.less_unsigned = (a < b)
        elif op == OP.JMP: jump(args[0])
        elif op == OP.JZ:
            if self.zero: jump(args[0])
        elif op == OP.JNZ:
            if not self.zero: jump(args[0])
        elif op == OP.JL:
            if self.less_signed: jump(args[0])
        elif op == OP.JG:
            if not self.less_signed and not self.zero: jump(args[0])
        elif op == OP.READ_KEY:
            (dst,) = args
            evt = self.mb_read()
            self.reg[dst] = 0 # Default to 0
            if evt and evt[0] == CMD_KEY:
                self.reg[dst] = evt[1] & 0xFF
        elif op == OP.ADD: self.reg[args[0]] = (self._val(args[0]) + self._val(args[1])) & 0xFFFFFFFF
        elif op == OP.SUB: self.reg[args[0]] = (self._val(args[0]) - self._val(args[1])) & 0xFFFFFFFF
        elif op == OP.MOV: self.reg[args[0]] = self._val(args[1])

    def run(self, steps: int = -1):
        self.running = True
        count = 0
        while self.running and (steps == -1 or count < steps):
            self.step()
            count += 1

    def load_cart_bytes(self, cart_bytes: bytes):
        try:
            magic, num_instr, pool_len = struct.unpack("<4sII", cart_bytes[:12])
            if magic != b'PXL1': raise ValueError("Invalid cartridge magic")

            self.code = []
            offset = 12
            for _ in range(num_instr):
                op, = struct.unpack("<I", cart_bytes[offset:offset+4])
                args = list(struct.unpack("<IIIII", cart_bytes[offset+4:offset+24]))[:5]
                self.code.append((op, args))
                offset += 24

            self.pool = cart_bytes[offset:offset+pool_len]
            self.pc = 0
            self.running = True
        except (struct.error, ValueError) as e:
            print(f"Failed to load cartridge: {e}")
            self.running = False

    def dump_regs(self):
        return " ".join(f"r{i}={v:#010x}" for i, v in enumerate(self.reg))
