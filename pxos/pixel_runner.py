import numpy as np
import struct
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any

class PXLOpcodes:
    """PXL instruction opcodes - the language of pixels"""
    HALT = 0x00      # Stop execution
    PXSET = 0x01     # Set pixel at (x,y) to color
    FILL = 0x02      # Fill rectangle
    TEXT = 0x10      # Draw text
    LD = 0x06        # Load from memory
    ST = 0x07        # Store to memory
    CMP = 0x09       # Compare values
    JMP = 0x0A       # Jump to address
    JZ = 0x0B        # Jump if zero
    READ_KEY = 0x0F  # Read keyboard input

@dataclass
class MemoryRegions:
    """PXOS Memory Map - everything lives in pixels"""
    code_start: Tuple[int, int] = (8, 8)      # CODE region
    code_size: int = 4096
    data_start: Tuple[int, int] = (8, 16)     # DATA region
    data_size: Tuple[int, int] = (256, 48)
    fb_start: Tuple[int, int] = (0, 0)        # Framebuffer
    fb_size: Tuple[int, int] = (640, 480)
    mailbox_base: int = 0x1900 # Base address for the mailbox

class PixelRunner:
    """Virtual machine that executes pixel programs"""

    def __init__(self, framebuffer: np.ndarray):
        self.framebuffer = framebuffer
        self.regions = MemoryRegions()

        # CPU state
        self.pc = 0
        self.running = False
        self.registers = [0] * 8
        self.zero_flag = False

        # Program storage
        self.code = []
        self.string_pool = []

        # Memory
        self.data_memory = [0] * 4096 # Simulate 4KB of data memory

        print("🔥 PixelRunner initialized - Ready for pixel computing!")

    def inject_mailbox_event(self, packet: Dict[str, int]):
        """Injects an event packet into the mailbox in data_memory."""
        base = self.regions.mailbox_base
        self._write_memory(base, packet.get('cmd', 0))
        self._write_memory(base + 1, packet.get('a', 0))
        self._write_memory(base + 2, packet.get('b', 0))
        self._write_memory(base + 3, packet.get('c', 0))

    def load_program(self, bytecode: bytes) -> bool:
        """Load PXL program from bytecode"""
        try:
            if len(bytecode) < 12 or bytecode[:4] != b'PXL1':
                print("❌ Invalid PXL program")
                return False

            instr_count, string_pool_size = struct.unpack('<II', bytecode[4:12])
            print(f"📋 Loading: {instr_count} instructions, {string_pool_size} string bytes")

            offset = 12
            self.code = []
            for i in range(instr_count):
                if offset >= len(bytecode): break
                opcode = struct.unpack('<I', bytecode[offset:offset+4])[0]
                offset += 4
                arg_count = self._get_arg_count(opcode)
                args = []
                for j in range(arg_count):
                    if offset + 4 <= len(bytecode):
                        arg = struct.unpack('<I', bytecode[offset:offset+4])[0]
                        args.append(arg)
                        offset += 4
                self.code.append((opcode, args))

            if string_pool_size > 0:
                self.string_pool = list(bytecode[offset:offset+string_pool_size])

            print("✅ Program loaded successfully")
            return True

        except Exception as e:
            print(f"❌ Failed to load program: {e}")
            return False

    def _get_arg_count(self, opcode: int) -> int:
        """Get argument count for opcode"""
        return {
            PXLOpcodes.HALT: 0, PXLOpcodes.PXSET: 3, PXLOpcodes.FILL: 5,
            PXLOpcodes.TEXT: 3, PXLOpcodes.LD: 2, PXLOpcodes.ST: 2,
            PXLOpcodes.CMP: 2, PXLOpcodes.JMP: 1, PXLOpcodes.JZ: 1,
            PXLOpcodes.READ_KEY: 1,
        }.get(opcode, 0)

    def execute(self, max_ops: int = 1000) -> Dict[str, Any]:
        """Execute program"""
        if not self.code:
            return {"error": "No program loaded", "ops": 0}

        self.running = True
        ops_executed = 0

        while self.running and ops_executed < max_ops and self.pc < len(self.code):
            try:
                opcode, args = self.code[self.pc]
                self._execute_instruction(opcode, args)
                self.pc += 1
                ops_executed += 1
            except Exception as e:
                return {"error": f"Runtime error at PC {self.pc}: {e}", "ops": ops_executed}

        return {"ops": ops_executed, "running": self.running, "pc": self.pc}

    def _execute_instruction(self, opcode: int, args: List[int]):
        """Execute a single pixel instruction"""
        if opcode == PXLOpcodes.HALT: self.running = False
        elif opcode == PXLOpcodes.READ_KEY:
            reg = args[0]
            if reg < len(self.registers): self.registers[reg] = self._read_key()
        elif opcode == PXLOpcodes.LD:
            reg, addr = args
            if reg < len(self.registers): self.registers[reg] = self._read_memory(addr)
        elif opcode == PXLOpcodes.ST:
            addr, reg = args
            if reg < len(self.registers): self._write_memory(addr, self.registers[reg])
        elif opcode == PXLOpcodes.CMP:
            reg1, reg2 = args
            if reg1 < len(self.registers) and reg2 < len(self.registers):
                self.zero_flag = (self.registers[reg1] == self.registers[reg2])
        elif opcode == PXLOpcodes.JZ:
            if self.zero_flag: self.pc = args[0] - 1
        elif opcode == PXLOpcodes.PXSET: self._set_pixel(*args)
        elif opcode == PXLOpcodes.FILL: self._fill_rect(*args)
        elif opcode == PXLOpcodes.TEXT: self._draw_text(*args)
        elif opcode == PXLOpcodes.JMP: self.pc = args[0] - 1
        else: print(f"⚠️ Unknown opcode: {opcode:02x}")

    def _set_pixel(self, x: int, y: int, color: int):
        if 0 <= x < self.framebuffer.shape[1] and 0 <= y < self.framebuffer.shape[0]:
            r, g, b, a = color & 0xFF, (color >> 8) & 0xFF, (color >> 16) & 0xFF, (color >> 24) & 0xFF
            self.framebuffer[y, x] = [r, g, b, a]

    def _fill_rect(self, x: int, y: int, w: int, h: int, color: int):
        x2, y2 = min(x + w, self.framebuffer.shape[1]), min(y + h, self.framebuffer.shape[0])
        if x < x2 and y < y2:
            r, g, b, a = color & 0xFF, (color >> 8) & 0xFF, (color >> 16) & 0xFF, (color >> 24) & 0xFF
            self.framebuffer[y:y2, x:x2] = [r, g, b, a]

    def _draw_text(self, x: int, y: int, length: int):
        text = ""
        pool_pos = 0
        for i in range(min(length, len(self.string_pool))):
            if pool_pos < len(self.string_pool):
                char_code = self.string_pool[pool_pos]
                if char_code == 0: break
                text += chr(char_code)
                pool_pos += 1
        for i, char in enumerate(text):
            char_x, char_y = x + i * 8, y
            if char_x + 8 < self.framebuffer.shape[1] and char_y + 12 < self.framebuffer.shape[0]:
                self.framebuffer[char_y:char_y+12, char_x:char_x+7] = [220, 220, 230, 255]

    def _read_memory(self, addr: int) -> int:
        if 0 <= addr < len(self.data_memory): return self.data_memory[addr]
        return 0

    def _write_memory(self, addr: int, value: int):
        if 0 <= addr < len(self.data_memory): self.data_memory[addr] = value

    def _read_key(self) -> int:
        base = self.regions.mailbox_base
        cmd = self._read_memory(base)
        if cmd == 1: # KeyPress
            keycode = self._read_memory(base + 1)
            self._write_memory(base, 0) # Clear command
            return keycode
        return 0
