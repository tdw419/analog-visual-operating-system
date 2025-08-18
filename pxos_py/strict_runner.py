import struct
from typing import List, Tuple, Optional

# --- Constants ---
class OP:
    HALT = 0x00
    PXSET = 0x01
    FILL = 0x02
    TEXT = 0x10
    SET_POOLPOS = 0x12
    LD = 0x06
    ST = 0x07
    CMP = 0x09
    JMP = 0x0A
    JZ = 0x0B
    JNZ = 0x0C
    JL = 0x0D
    JG = 0x0E
    JB = 0x1D
    JA = 0x1E
    READ_KEY = 0x0F
    ADD = 0x13
    SUB = 0x14
    MUL = 0x15
    MOV = 0x1B
    MOD = 0x1A

class MEM:
    MAILBOX_BASE = 0x1900

# Note: The user's prototype used CMD_NOP, CMD_KEY. I'll stick to that.
CMD_NOP = 0x00
CMD_KEY = 0x01

# --- VM Configuration ---
class VMConfig:
    def __init__(self, width=640, height=480, mem_size=1024 * 1024):
        self.width = width
        self.height = height
        self.mem_size = mem_size

# --- The Virtual Machine ---
class StrictRunner:
    def __init__(self, cfg: VMConfig = VMConfig()):
        self.cfg = cfg
        self.mem = [0] * cfg.mem_size
        self.reg = [0] * 16
        self.pc = 0
        self.running = False
        self.code: List[Tuple[int, List[int]]] = []
        self.pool: bytes = b''
        self.zero = False
        self.less_signed = False
        self.less_unsigned = False
        self.fb = [[[0, 0, 0, 255] for _ in range(cfg.width)] for __ in range(cfg.height)]
        self.font = self._load_font()
        self.pool_pos = 0 # For SET_POOLPOS and TEXT

    def _load_font(self):
        # Using the superior 5x7 font for readability
        return [
            0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x18,0x3C,0x3C,0x18,0x18,0x00,0x18,
            0x66,0x66,0x24,0x00,0x00,0x00,0x00,0x24,0x7E,0x24,0x7E,0x24,0x00,0x00,
            0x18,0x3E,0x60,0x3C,0x06,0x7C,0x18,0x40,0x46,0x0C,0x18,0x30,0x62,0x02,
            0x38,0x6C,0x38,0x30,0x6C,0x38,0x00,0x18,0x18,0x0C,0x00,0x00,0x00,0x00,
            0x0C,0x18,0x30,0x30,0x30,0x18,0x0C,0x30,0x18,0x0C,0x0C,0x0C,0x18,0x30,
            0x00,0x66,0x3C,0xFF,0x3C,0x66,0x00,0x00,0x18,0x18,0x7E,0x18,0x18,0x00,
            0x00,0x00,0x00,0x00,0x0C,0x18,0x30,0x00,0x00,0x7E,0x00,0x00,0x00,0x00,
            0x00,0x00,0x00,0x00,0x0C,0x18,0x00,0x02,0x06,0x0C,0x18,0x30,0x60,0x40,
            0x3C,0x66,0x6E,0x76,0x66,0x66,0x3C,0x18,0x38,0x18,0x18,0x18,0x18,0x3C,
            0x3C,0x66,0x06,0x0C,0x18,0x30,0x7E,0x3C,0x66,0x06,0x1C,0x06,0x66,0x3C,
            0x0C,0x1C,0x2C,0x4C,0x7E,0x0C,0x0C,0x7E,0x60,0x60,0x7C,0x06,0x66,0x3C,
            0x3C,0x60,0x60,0x7C,0x66,0x66,0x3C,0x7E,0x06,0x0C,0x18,0x18,0x18,0x18,
            0x3C,0x66,0x66,0x3C,0x66,0x66,0x3C,0x3C,0x66,0x66,0x3E,0x06,0x0C,0x38,
            0x00,0x18,0x18,0x00,0x18,0x18,0x00,0x00,0x18,0x18,0x00,0x18,0x30,0x18,
            0x0C,0x18,0x30,0x60,0x30,0x18,0x0C,0x00,0x00,0x3C,0x00,0x3C,0x00,0x00,
            0x60,0x30,0x18,0x0C,0x18,0x30,0x60,0x3C,0x66,0x0C,0x18,0x18,0x00,0x18,
            0x3C,0x66,0x7E,0x7E,0x7E,0x60,0x3C,0x3C,0x66,0x66,0x7E,0x66,0x66,0x66,
            0x7C,0x66,0x66,0x7C,0x66,0x66,0x7C,0x3C,0x66,0x60,0x60,0x60,0x66,0x3C,
            0x78,0x6C,0x66,0x66,0x66,0x6C,0x78,0x7E,0x60,0x60,0x7C,0x60,0x60,0x7E,
            0x7E,0x60,0x60,0x7C,0x60,0x60,0x60,0x3C,0x66,0x60,0x6E,0x66,0x66,0x3C,
            0x66,0x66,0x66,0x7E,0x66,0x66,0x66,0x3C,0x18,0x18,0x18,0x18,0x18,0x3C,
            0x0E,0x06,0x06,0x06,0x66,0x66,0x3C,0x66,0x6C,0x78,0x60,0x78,0x6C,0x66,
            0x60,0x60,0x60,0x60,0x60,0x60,0x7E,0x42,0x66,0x7E,0x7E,0x66,0x66,0x66,
            0x66,0x66,0x76,0x7E,0x6E,0x66,0x66,0x3C,0x66,0x66,0x66,0x66,0x66,0x3C,
            0x7C,0x66,0x66,0x7C,0x60,0x60,0x60,0x3C,0x66,0x66,0x66,0x6E,0x3C,0x0E,
            0x7C,0x66,0x66,0x7C,0x6C,0x66,0x66,0x3C,0x66,0x60,0x3C,0x06,0x66,0x3C,
            0x7E,0x18,0x18,0x18,0x18,0x18,0x18,0x66,0x66,0x66,0x66,0x66,0x66,0x3C,
            0x66,0x66,0x66,0x66,0x66,0x3C,0x18,0x66,0x66,0x66,0x66,0x7E,0x7E,0x42,
            0x66,0x66,0x3C,0x18,0x3C,0x66,0x66,0x66,0x66,0x3C,0x18,0x18,0x18,0x18,
            0x7E,0x06,0x0C,0x18,0x30,0x60,0x7E
        ]

    def _s32(self, v): return (v + 2**31) % 2**32 - 2**31
    def _val(self, v): return self.reg[v] if v < 16 else v

    def _put(self, x, y, c):
        if 0 <= x < self.cfg.width and 0 <= y < self.cfg.height:
            r, g, b, a = (c >> 24) & 0xFF, (c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF
            self.fb[y][x] = [r, g, b, a]

    def _fill(self, x, y, w, h, c):
        x,y,w,h = int(x),int(y),int(w),int(h)
        r,g,b,a = (c>>24)&0xFF, (c>>16)&0xFF, (c>>8)&0xFF, c&0xFF
        for i in range(y, y + h):
            for j in range(x, x + w):
                if 0 <= j < self.cfg.width and 0 <= i < self.cfg.height:
                    self.fb[i][j] = [r, g, b, a]

    def _text(self, x, y, length):
        color = 0xFFFFFFFF
        pool_slice = self.pool[self.pool_pos : self.pool_pos + length]
        s = pool_slice.decode('ascii', errors='ignore')
        char_w, char_h = 5, 7
        for i, char in enumerate(s):
            char_code = ord(char)
            if 32 <= char_code <= 122:
                font_char_idx = (char_code - 32) * char_h
                for row in range(char_h):
                    bits = self.font[font_char_idx + row]
                    for col in range(char_w):
                        if (bits >> (char_w - 1 - col)) & 1:
                            self._put(x + i * (char_w + 1) + col, y + row, color)

    def mb_read(self) -> Optional[Tuple[int, int, int, int]]:
        i = MEM.MAILBOX_BASE
        cmd = self.mem[i]
        if cmd == CMD_NOP: return None
        arg, x, y = self.mem[i + 1], self.mem[i + 2], self.mem[i + 3]
        self.mem[i] = CMD_NOP
        return (cmd, arg, x, y)

    def load_cart_bytes(self, cart_bytes: bytes):
        header = struct.unpack("<4sII", cart_bytes[:12])
        if header[0] != b'PXL1': raise ValueError("Invalid cartridge magic")

        num_instr, pool_size = header[1], header[2]
        self.code = []
        offset = 12

        op_arg_count = {
            OP.HALT: 0, OP.PXSET: 3, OP.FILL: 5, OP.TEXT: 3, OP.SET_POOLPOS: 1,
            OP.LD: 2, OP.ST: 2, OP.CMP: 2, OP.JMP: 1, OP.JZ: 1, OP.JNZ: 1,
            OP.READ_KEY: 1, OP.ADD: 2, OP.SUB: 2, OP.MUL: 2, OP.MOV: 2, OP.MOD: 2,
            OP.JL: 1, OP.JG: 1, OP.JB: 1, OP.JA: 1
        }

        for _ in range(num_instr):
            op, = struct.unpack("<I", cart_bytes[offset:offset+4])
            offset += 4
            num_args = op_arg_count.get(op, 0)
            args = []
            if num_args > 0:
                args = list(struct.unpack(f"<{num_args}I", cart_bytes[offset:offset + 4 * num_args]))
                offset += 4 * num_args
            self.code.append((op, args))

        self.pool = cart_bytes[-pool_size:]
        self.pc = 0
        self.running = True

    def step(self):
        if not self.running or self.pc >= len(self.code):
            self.running = False
            return

        op, args = self.code[self.pc]
        def jump(to: int): self.pc = to - 1

        if op == OP.HALT: self.running = False
        elif op == OP.PXSET: x, y, c = args; self._put(x, y, c)
        elif op == OP.FILL: x, y, w, h, c = args; self._fill(x, y, w, h, c)
        elif op == OP.TEXT: x, y, L = args; self._text(x, y, L)
        elif op == OP.SET_POOLPOS: idx, = args; self.pool_pos = idx
        elif op == OP.LD: r, a = args; self.reg[r] = self.mem[a]
        elif op == OP.ST: a, r = args; self.mem[a] = self.reg[r]
        elif op == OP.CMP: r, v = args; a = self.reg[r]; b = self._val(v); self.zero=(a==b); self.less_signed=(self._s32(a)<self._s32(b)); self.less_unsigned=(a<b)
        elif op == OP.JMP: to, = args; jump(to)
        elif op == OP.JZ: (to,) = args; self.zero and jump(to)
        elif op == OP.JNZ: (to,) = args; not self.zero and jump(to)
        elif op == OP.JL: (to,) = args; self.less_signed and jump(to)
        elif op == OP.JG: (to,) = args; not self.less_signed and not self.zero and jump(to)
        elif op == OP.JB: (to,) = args; self.less_unsigned and jump(to)
        elif op == OP.JA: (to,) = args; not self.less_unsigned and not self.zero and jump(to)
        elif op == OP.READ_KEY: dst, = args; evt = self.mb_read(); self.reg[dst] = evt[1] if evt and evt[0] == CMD_KEY else 0
        elif op == OP.ADD: r_dst, r_src = args; self.reg[r_dst] = (self.reg[r_dst] + self.reg[r_src]) & 0xFFFFFFFF
        elif op == OP.SUB: r_dst, r_src = args; self.reg[r_dst] = (self.reg[r_dst] - self.reg[r_src]) & 0xFFFFFFFF
        elif op == OP.MUL: r_dst, r_src = args; self.reg[r_dst] = (self.reg[r_dst] * self.reg[r_src]) & 0xFFFFFFFF
        elif op == OP.MOV: r_dst, r_src = args; self.reg[r_dst] = self.reg[r_src]
        elif op == OP.MOD: r_dst, r_src = args; self.reg[r_dst] = (self.reg[r_dst] % self.reg[r_src]) & 0xFFFFFFFF
        self.pc += 1

    def run(self, max_steps):
        for _ in range(max_steps):
            if not self.running: break
            self.step()

# --- Cartridge Builder ---
class CartBuilder:
    def __init__(self):
        self.code: List[Tuple[int, List[int]]] = []
        self.pool = bytearray()

    def emit(self, op: int, *args: int):
        self.code.append((op, list(args)))

    def str_id(self, s: str) -> int:
        i = len(self.pool)
        self.pool += s.encode("ascii") + b"\x00"
        return i

    def assemble(self) -> bytes:
        out = bytearray()
        num_instr = len(self.code)
        pool_size = len(self.pool)
        out += struct.pack("<4sII", b"PXL1", num_instr, pool_size)

        for op, args in self.code:
            out += struct.pack("<I", op)
            for a in args:
                out += struct.pack("<I", a)

        out += self.pool
        return bytes(out)

# --- Mailbox Helper ---
def mb_write_key(mem: List[int], keycode: int) -> None:
    i = MEM.MAILBOX_BASE
    mem[i + 0] = CMD_KEY
    mem[i + 1] = keycode & 0xFF
    mem[i + 2] = 0
    mem[i + 3] = 0
