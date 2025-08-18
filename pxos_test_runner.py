#!/usr/bin/env python3
"""
PXOS Test Runner - Execute the complete bootstrap system
Save this file and run it to see PXOS in action!

This combines all components from your paste.txt file into one executable test.
"""

import numpy as np
import struct
import time
from pathlib import Path
from PIL import Image, ImageDraw
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any

# ============================================================================
# Your Complete PXOS Bootstrap System (from paste.txt)
# ============================================================================

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

from pxos.pixel_runner import PixelRunner, MemoryRegions

class PXLAssembler:
    """Assembles PXL instructions to bytecode"""

    def __init__(self):
        self.instructions = []
        self.string_pool = []

    def emit(self, opcode: int, *args) -> None:
        """Emit a PXL instruction"""
        self.instructions.append((opcode, list(args)))

    def emit_string(self, text: str) -> int:
        """Add string to pool and return its ID"""
        string_id = len(self.string_pool)
        ascii_chars = [ord(c) for c in text] + [0]  # null-terminated
        self.string_pool.extend(ascii_chars)
        return string_id

    def assemble(self) -> bytes:
        """Assemble to binary format"""
        # Header: magic + instruction count + string pool size
        header = struct.pack('<4sII', b'PXL1', len(self.instructions), len(self.string_pool))

        # Instructions section
        instruction_data = b''
        for opcode, args in self.instructions:
            instruction_data += struct.pack('<I', opcode)
            for arg in args:
                instruction_data += struct.pack('<I', arg)

        # String pool section
        string_data = b''
        if self.string_pool:
            string_data = struct.pack(f'<{len(self.string_pool)}B', *self.string_pool)

        return header + instruction_data + string_data

# ============================================================================
# Demo Programs (Your Working Examples)
# ============================================================================

def create_pxedit_demo() -> bytes:
    """Create a demo PXEdit program"""
    asm = PXLAssembler()

    # Clear screen with dark background
    asm.emit(PXLOpcodes.FILL, 0, 0, 640, 480, 0x1E1E28FF)

    # Draw title bar
    asm.emit(PXLOpcodes.FILL, 0, 0, 640, 40, 0x2D2D3AFF)
    title_str = asm.emit_string("PXEdit v1.0 - Pixel Native Text Editor")
    asm.emit(PXLOpcodes.TEXT, 20, 15, len("PXEdit v1.0 - Pixel Native Text Editor"))

    # Draw editor area
    asm.emit(PXLOpcodes.FILL, 10, 50, 620, 400, 0x0F0F14FF)

    # Draw border
    asm.emit(PXLOpcodes.FILL, 8, 48, 624, 2, 0x404060FF)   # Top
    asm.emit(PXLOpcodes.FILL, 8, 450, 624, 2, 0x404060FF)  # Bottom
    asm.emit(PXLOpcodes.FILL, 8, 48, 2, 404, 0x404060FF)   # Left
    asm.emit(PXLOpcodes.FILL, 630, 48, 2, 404, 0x404060FF) # Right

    # Draw status bar
    asm.emit(PXLOpcodes.FILL, 0, 460, 640, 20, 0x2D2D3AFF)
    status_str = asm.emit_string("F1:Help F2:Save F3:Load F9:Compile ESC:Exit")
    asm.emit(PXLOpcodes.TEXT, 10, 465, len("F1:Help F2:Save F3:Load F9:Compile ESC:Exit"))

    # Sample text content
    sample_str = asm.emit_string("; Welcome to PXOS - Pixel Native Computing!")
    asm.emit(PXLOpcodes.TEXT, 20, 70, len("; Welcome to PXOS - Pixel Native Computing!"))

    code_str = asm.emit_string("FILL 100 100 200 100 0xFF0000FF")
    asm.emit(PXLOpcodes.TEXT, 20, 90, len("FILL 100 100 200 100 0xFF0000FF"))

    comment_str = asm.emit_string("; This draws a red rectangle")
    asm.emit(PXLOpcodes.TEXT, 20, 110, len("; This draws a red rectangle"))

    # Draw cursor
    asm.emit(PXLOpcodes.FILL, 20, 130, 2, 12, 0xFFFFFFFF)

    asm.emit(PXLOpcodes.HALT)
    return asm.assemble()

def create_simple_demo() -> bytes:
    """Create a simple demo showing basic graphics"""
    asm = PXLAssembler()

    # Blue background
    asm.emit(PXLOpcodes.FILL, 0, 0, 640, 480, 0x002244FF)

    # Red rectangle
    asm.emit(PXLOpcodes.FILL, 100, 100, 200, 100, 0xFF0000FF)

    # Green rectangle
    asm.emit(PXLOpcodes.FILL, 350, 200, 150, 80, 0x00FF00FF)

    # Yellow text
    hello_str = asm.emit_string("Hello, PXOS!")
    asm.emit(PXLOpcodes.TEXT, 120, 130, len("Hello, PXOS!"))

    # White text
    welcome_str = asm.emit_string("Welcome to Pixel Computing")
    asm.emit(PXLOpcodes.TEXT, 200, 300, len("Welcome to Pixel Computing"))

    asm.emit(PXLOpcodes.HALT)
    return asm.assemble()

def create_interactive_pxedit_program() -> bytes:
    """Creates a PXL program for a basic interactive text editor."""
    asm = PXLAssembler()

    # Memory addresses for editor state
    CURSOR_X = 0
    CURSOR_Y = 1
    TEXT_BUFFER_START = 100

    # --- Initialization ---
    # Draw static UI
    asm.emit(PXLOpcodes.FILL, 0, 0, 640, 480, 0x1E1E28FF)  # Dark background
    asm.emit(PXLOpcodes.FILL, 10, 10, 620, 460, 0x2D2D3AFF) # Editor frame
    title_len = asm.emit_string("Interactive PXEdit v1.0")
    asm.emit(PXLOpcodes.TEXT, 20, 20, title_len)

    # Initialize state in DATA region
    asm.emit(PXLOpcodes.LD, 0, 50)          # r0 = 50 (initial cursor x)
    asm.emit(PXLOpcodes.ST, CURSOR_X, 0)   # Store initial cursor_x
    asm.emit(PXLOpcodes.LD, 0, 50)          # r0 = 50 (initial cursor y)
    asm.emit(PXLOpcodes.ST, CURSOR_Y, 0)   # Store initial cursor_y

    # --- Main Loop ---
    loop_start_addr = len(asm.instructions)
    asm.emit(PXLOpcodes.READ_KEY, 0)        # Read key into r0
    asm.emit(PXLOpcodes.LD, 1, 0)           # r1 = 0
    asm.emit(PXLOpcodes.CMP, 0, 1)          # if r0 == r1 (no key pressed)

    # If key was pressed, jump to handle_key. Otherwise, continue to loop.
    # We need to know the address of handle_key first, so we'll patch this later.
    handle_key_jump_instr_index = len(asm.instructions)
    asm.emit(PXLOpcodes.JZ, 0) # Placeholder, will be patched

    # No key was pressed, just loop
    asm.emit(PXLOpcodes.JMP, loop_start_addr)

    # --- Handle Key Press Subroutine ---
    handle_key_addr = len(asm.instructions)
    # For now, just draw the character at the cursor position
    # (This is a simplified demo of interactivity)
    asm.emit(PXLOpcodes.LD, 1, CURSOR_X)    # r1 = cursor_x
    asm.emit(PXLOpcodes.LD, 2, CURSOR_Y)    # r2 = cursor_y

    # We can't pass the character directly to TEXT yet, so we just draw a block
    asm.emit(PXLOpcodes.FILL, 1, 2, 8, 12, 0xFFFFFFFF) # Draw a white block for the char

    # Move cursor right
    asm.emit(PXLOpcodes.LD, 1, CURSOR_X)    # r1 = cursor_x
    asm.emit(PXLOpcodes.LD, 2, 8)           # r2 = 8
    # A real program would have an ADD opcode. We simulate by storing and reloading.
    # This part is a placeholder for real arithmetic.
    asm.emit(PXLOpcodes.ST, CURSOR_X, 1) # Store updated cursor_x

    asm.emit(PXLOpcodes.JMP, loop_start_addr) # Go back to main loop

    # Patch the jump instruction
    asm.instructions[handle_key_jump_instr_index] = (PXLOpcodes.JZ, [handle_key_addr])

    asm.emit(PXLOpcodes.HALT)
    return asm.assemble()


# ============================================================================
# Test Suite
# ============================================================================

class PXOSTestSuite:
    """Complete test suite for PXOS Bootstrap"""

    def __init__(self):
        self.framebuffer = np.zeros((480, 640, 4), dtype=np.uint8)
        self.runner = PixelRunner(self.framebuffer)
        self.output_dir = Path("pxos_test_output")
        self.output_dir.mkdir(exist_ok=True)

    def run_all_tests(self):
        """Run the complete test suite"""
        print("🌟" * 50)
        print("🌟 PXOS BOOTSTRAP TEST SUITE")
        print("🌟" * 50)

        tests = [
            ("Simple Graphics", self.test_simple_graphics),
            ("PXEdit Interface", self.test_pxedit_interface),
            ("Interactive Editor", self.test_interactive_editor),
            ("Performance Test", self.test_performance),
        ]

        results = []
        for test_name, test_func in tests:
            print(f"\n🧪 Running: {test_name}")
            try:
                result = test_func()
                results.append((test_name, "✅ PASS", result))
                print(f"✅ {test_name}: PASSED")
            except Exception as e:
                results.append((test_name, "❌ FAIL", str(e)))
                print(f"❌ {test_name}: FAILED - {e}")

        self.print_summary(results)
        return results

    def test_simple_graphics(self):
        """Test basic graphics rendering"""
        bytecode = create_simple_demo()

        if not self.runner.load_program(bytecode):
            raise Exception("Failed to load simple graphics program")

        result = self.runner.execute(max_ops=100)

        if "error" in result:
            raise Exception(f"Execution error: {result['error']}")

        # Save output
        self.save_frame("simple_graphics_test.png")

        return {
            "ops_executed": result["ops"],
            "program_halted": not result["running"]
        }

    def test_pxedit_interface(self):
        """Test PXEdit interface rendering"""
        bytecode = create_pxedit_demo()

        # Reset framebuffer
        self.framebuffer.fill(0)

        if not self.runner.load_program(bytecode):
            raise Exception("Failed to load PXEdit program")

        result = self.runner.execute(max_ops=200)

        if "error" in result:
            raise Exception(f"Execution error: {result['error']}")

        # Save output
        self.save_frame("pxedit_interface_test.png")

        return {
            "ops_executed": result["ops"],
            "program_halted": not result["running"]
        }

    def test_interactive_editor(self):
        """Test the interactive editor program."""
        bytecode = create_interactive_pxedit_program()

        self.runner.framebuffer.fill(0)
        if not self.runner.load_program(bytecode):
            raise Exception("Failed to load interactive PXEdit program")

        # Inject a key press (e.g., ASCII for 'A')
        self.runner.inject_mailbox_event({'cmd': 1, 'a': 65})

        # Run the program for a few cycles to process the key
        result = self.runner.execute(max_ops=100)

        if "error" in result:
            raise Exception(f"Execution error in interactive editor: {result['error']}")

        # This test primarily ensures the interactive loop runs without crashing.
        # A more advanced test would check the framebuffer or memory state.
        self.save_frame("interactive_editor_test.png")

        return {
            "ops_executed": result["ops"],
            "program_running": result["running"]
        }

    def test_performance(self):
        """Test execution performance"""
        bytecode = create_simple_demo()

        # Reset framebuffer
        self.framebuffer.fill(0)

        start_time = time.time()

        if not self.runner.load_program(bytecode):
            raise Exception("Failed to load performance test program")

        result = self.runner.execute(max_ops=1000)

        end_time = time.time()
        execution_time = end_time - start_time

        if "error" in result:
            raise Exception(f"Execution error: {result['error']}")

        ops_per_second = result["ops"] / execution_time if execution_time > 0 else 0

        return {
            "ops_executed": result["ops"],
            "execution_time": execution_time,
            "ops_per_second": ops_per_second
        }

    def save_frame(self, filename):
        """Save current framebuffer to file"""
        img = Image.fromarray(self.framebuffer, 'RGBA')
        output_path = self.output_dir / filename
        img.save(output_path)
        print(f"💾 Saved: {output_path}")

    def print_summary(self, results):
        """Print test summary"""
        print("\n" + "🌟" * 50)
        print("🌟 TEST SUMMARY")
        print("🌟" * 50)

        passed = sum(1 for _, status, _ in results if "PASS" in status)
        total = len(results)

        for test_name, status, details in results:
            print(f"{status} {test_name}")
            if isinstance(details, dict):
                for key, value in details.items():
                    print(f"    {key}: {value}")

        print(f"\n🎯 Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 ALL TESTS PASSED! PXOS IS OPERATIONAL! 🎉")
        else:
            print("⚠️  Some tests failed. Check output for details.")

# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main entry point - run PXOS bootstrap tests"""
    print("🔥 PXOS BOOTSTRAP - LIGHTING THE FIRST FIRE OF PIXEL COMPUTING! 🔥")

    # Run complete test suite
    test_suite = PXOSTestSuite()
    results = test_suite.run_all_tests()

    print(f"\n📁 Check '{test_suite.output_dir}' for visual output!")
    print("\n🚀 NEXT STEPS:")
    print("   1. Review the generated images to see PXOS in action")
    print("   2. Modify the demo programs to experiment")
    print("   3. Build more complex pixel programs")
    print("   4. Work toward self-hosting (assembler in pixels)")

    return results

if __name__ == "__main__":
    main()
