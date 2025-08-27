#!/usr/bin/env python3
"""
Pixel-Executable Transpiler for VisualPython AVOS

Converts Python source code to executable pixel sheets that can be "run" by
the analog computer through visual pattern recognition and correlation.

This implements the vision where source code becomes pixels on screen,
and those pixels are directly executable by the analog environment.

Integrates with:
- VisualPython Direct Execution Model
- Universal Visual Intermediate Representation (UVIR)  
- Infinite Visual Computer Architecture
- Visual Memory System

Usage:
    python pixel_executable_transpiler.py --src demo.py --out program_sheet.png
    python pixel_executable_transpiler.py --decode program_sheet.png --csv output.csv
"""

import ast
import json
import math
import argparse
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Add visualpython to path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
sys.path.insert(0, str(src_path))

# Tile configuration for analog-friendly encoding
TILE_SIZE = 32  # Larger tiles for better analog correlation
PAYLOAD_SIZE = 24  # Central payload area
MARGIN = (TILE_SIZE - PAYLOAD_SIZE) // 2
BIT_CELL_SIZE = PAYLOAD_SIZE // 6  # 6x6 bit grid = 36 bits per tile
FIDUCIAL_SIZE = TILE_SIZE

# Colors for high analog contrast
BLACK = 0
WHITE = 255
GRAY = 128

# Enhanced opcode set for AVOS integration
class Opcodes:
    # Core execution
    NOP = 0x00
    HALT = 0x01
    
    # Memory operations (Visual Memory System)
    LOAD_VAR = 0x02
    STORE_VAR = 0x03
    SET_IMM = 0x04
    
    # Arithmetic (analog-friendly operations)
    ADD = 0x05
    SUB = 0x06
    MUL = 0x07
    DIV = 0x08
    
    # Control flow
    JUMP = 0x09
    JUMP_IF_ZERO = 0x0A
    LOOP_START = 0x0B
    LOOP_END = 0x0C
    
    # Visual operations (UVIR integration)
    CLEAR_SCREEN = 0x10
    SET_PIXEL = 0x11
    DRAW_RECT = 0x12
    DRAW_TEXT = 0x13
    SET_COLOR = 0x14
    
    # Infinite canvas operations
    SET_CHUNK_X = 0x15
    SET_CHUNK_Y = 0x16
    LOAD_CHUNK = 0x17
    STORE_CHUNK = 0x18
    
    # Temporal operations
    COMMIT_FRAME = 0x19
    SET_TIME = 0x1A
    
    # Hardware integration (Tool Registry Pattern)
    PWM_WRITE = 0x20
    ADC_READ = 0x21
    DAC_WRITE = 0x22
    SERIAL_OUT = 0x23
    
    # Advanced visual operations
    BEGIN_PATH = 0x30
    LINE_TO = 0x31
    CURVE_TO = 0x32
    FILL_PATH = 0x33
    
    # Debug and monitoring
    PRINT_VAR = 0x40
    DEBUG_MARKER = 0x41
    
    @classmethod
    def name(cls, opcode):
        for name, value in cls.__dict__.items():
            if not name.startswith('_') and value == opcode:
                return name
        return f"UNK_{opcode:02X}"


class PixelTile:
    """Encodes opcodes and operands as correlation-friendly pixel patterns"""
    
    def __init__(self):
        self.patterns = self._generate_correlation_patterns()
    
    def _generate_correlation_patterns(self) -> Dict[int, np.ndarray]:
        """Generate unique correlation patterns for each opcode"""
        patterns = {}
        
        for opcode in range(64):  # Support up to 64 opcodes
            # Create a unique pattern using deterministic noise
            np.random.seed(opcode + 12345)  # Deterministic seed
            
            # Generate pattern with good autocorrelation properties
            pattern = np.random.choice([0, 1], size=(6, 6), p=[0.5, 0.5])
            
            # Ensure pattern has good contrast and structure
            pattern = self._enhance_pattern(pattern)
            
            patterns[opcode] = pattern
        
        return patterns
    
    def _enhance_pattern(self, pattern: np.ndarray) -> np.ndarray:
        """Enhance pattern for better analog correlation"""
        # Add structure to improve correlation SNR
        enhanced = pattern.copy()
        
        # Add corner markers for orientation
        enhanced[0, 0] = 1
        enhanced[0, -1] = 0
        enhanced[-1, 0] = 0
        enhanced[-1, -1] = 1
        
        return enhanced
    
    def encode_tile(self, opcode: int, operand_hi: int, operand_lo: int) -> Image.Image:
        """Encode opcode and operands into a tile image"""
        tile = Image.new('L', (TILE_SIZE, TILE_SIZE), WHITE)
        draw = ImageDraw.Draw(tile)
        
        # Draw border for alignment
        draw.rectangle([0, 0, TILE_SIZE-1, TILE_SIZE-1], outline=BLACK, width=1)
        
        # Get base pattern for opcode
        if opcode in self.patterns:
            pattern = self.patterns[opcode]
        else:
            # Default pattern for unknown opcodes
            pattern = np.zeros((6, 6))
        
        # Encode operands in the pattern (modify specific bits)
        encoded_pattern = pattern.copy()
        
        # Encode high operand in top-right 3x3
        for i in range(3):
            for j in range(3):
                bit_idx = i * 3 + j
                if bit_idx < 8:  # 8 bits for hi operand
                    bit_val = (operand_hi >> bit_idx) & 1
                    encoded_pattern[i, j + 3] = bit_val
        
        # Encode low operand in bottom-left 3x3  
        for i in range(3):
            for j in range(3):
                bit_idx = i * 3 + j
                if bit_idx < 8:  # 8 bits for lo operand
                    bit_val = (operand_lo >> bit_idx) & 1
                    encoded_pattern[i + 3, j] = bit_val
        
        # Render pattern to tile
        for i in range(6):
            for j in range(6):
                x = MARGIN + j * BIT_CELL_SIZE
                y = MARGIN + i * BIT_CELL_SIZE
                
                color = BLACK if encoded_pattern[i, j] else WHITE
                draw.rectangle([x, y, x + BIT_CELL_SIZE - 1, y + BIT_CELL_SIZE - 1], 
                             fill=color)
        
        return tile
    
    def decode_tile(self, tile_img: Image.Image) -> Tuple[int, int, int, float]:
        """Decode tile using correlation matching"""
        # Convert to numpy array
        tile_array = np.array(tile_img.convert('L'))
        
        # Extract payload region
        payload = tile_array[MARGIN:MARGIN+PAYLOAD_SIZE, MARGIN:MARGIN+PAYLOAD_SIZE]
        
        # Downsample to 6x6 bit pattern
        bit_pattern = np.zeros((6, 6))
        for i in range(6):
            for j in range(6):
                y = i * BIT_CELL_SIZE
                x = j * BIT_CELL_SIZE
                cell = payload[y:y+BIT_CELL_SIZE, x:x+BIT_CELL_SIZE]
                bit_pattern[i, j] = 1 if np.mean(cell) < 128 else 0
        
        # Find best matching opcode using correlation
        best_opcode = 0
        best_correlation = -1
        
        for opcode, pattern in self.patterns.items():
            # Correlate against base pattern (ignoring operand regions)
            mask = np.ones((6, 6))
            mask[0:3, 3:6] = 0  # Mask out hi operand region
            mask[3:6, 0:3] = 0  # Mask out lo operand region
            
            masked_bit = bit_pattern * mask
            masked_pattern = pattern * mask
            
            correlation = np.corrcoef(masked_bit.flatten(), masked_pattern.flatten())[0, 1]
            if not np.isnan(correlation) and correlation > best_correlation:
                best_correlation = correlation
                best_opcode = opcode
        
        # Decode operands
        operand_hi = 0
        operand_lo = 0
        
        # Decode hi operand from top-right 3x3
        for i in range(3):
            for j in range(3):
                bit_idx = i * 3 + j
                if bit_idx < 8:
                    bit_val = int(bit_pattern[i, j + 3])
                    operand_hi |= (bit_val << bit_idx)
        
        # Decode lo operand from bottom-left 3x3
        for i in range(3):
            for j in range(3):
                bit_idx = i * 3 + j
                if bit_idx < 8:
                    bit_val = int(bit_pattern[i + 3, j])
                    operand_lo |= (bit_val << bit_idx)
        
        return best_opcode, operand_hi, operand_lo, best_correlation


class VisualPythonCompiler:
    """Compiles Python AST to pixel-executable opcodes"""
    
    def __init__(self):
        self.variables = {}
        self.constants = {}
        self.instructions = []
        self.labels = {}
        self.current_pos = (0, 0)  # Current drawing position
        self.current_color = (255, 255, 255)
        self.chunk_coords = (0, 0)  # Current infinite canvas chunk
        
    def compile_source(self, source_code: str) -> List[Tuple[int, int, int]]:
        """Compile Python source to opcode sequence"""
        try:
            tree = ast.parse(source_code)
            self._visit_node(tree)
            
            # Add final halt
            self.instructions.append((Opcodes.HALT, 0, 0))
            
            return self.instructions
            
        except Exception as e:
            raise CompilerError(f"Compilation failed: {e}")
    
    def _visit_node(self, node: ast.AST):
        """Visit AST nodes and emit opcodes"""
        if isinstance(node, ast.Module):
            for child in node.body:
                self._visit_node(child)
                
        elif isinstance(node, ast.Assign):
            self._compile_assignment(node)
            
        elif isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Call):
                self._compile_function_call(node.value)
                
        elif isinstance(node, ast.For):
            self._compile_for_loop(node)
            
        elif isinstance(node, ast.If):
            self._compile_if_statement(node)
            
        else:
            # Unknown node type - emit debug marker
            self.instructions.append((Opcodes.DEBUG_MARKER, 0, 0))
    
    def _compile_assignment(self, node: ast.Assign):
        """Compile variable assignment"""
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            
            if isinstance(node.value, ast.Constant):
                # Direct constant assignment
                value = int(node.value.value)
                var_id = self._get_var_id(var_name)
                self.instructions.extend([
                    (Opcodes.SET_IMM, (value >> 8) & 0xFF, value & 0xFF),
                    (Opcodes.STORE_VAR, var_id, 0)
                ])
                
            elif isinstance(node.value, ast.BinOp):
                # Arithmetic operation
                self._compile_arithmetic(node.value)
                var_id = self._get_var_id(var_name)
                self.instructions.append((Opcodes.STORE_VAR, var_id, 0))
    
    def _compile_function_call(self, node: ast.Call):
        """Compile function calls to visual operations"""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            
            if func_name == 'print':
                self._compile_print(node)
            elif func_name == 'rect':
                self._compile_rect(node)
            elif func_name == 'clear':
                self._compile_clear(node)
            elif func_name == 'commit':
                self.instructions.append((Opcodes.COMMIT_FRAME, 0, 0))
            elif func_name == 'pwm_write':
                self._compile_pwm_write(node)
    
    def _compile_print(self, node: ast.Call):
        """Compile print statement to visual text"""
        if node.args:
            # For simplicity, just emit a debug marker
            # Full implementation would render text
            self.instructions.append((Opcodes.PRINT_VAR, 0, 0))
    
    def _compile_rect(self, node: ast.Call):
        """Compile rect() call to DRAW_RECT opcodes"""
        if len(node.args) >= 4:
            # Extract coordinates - simplified for demo
            self.instructions.extend([
                (Opcodes.DRAW_RECT, 0, 0),  # Placeholder
                (Opcodes.COMMIT_FRAME, 0, 0)
            ])
    
    def _compile_clear(self, node: ast.Call):
        """Compile clear() to screen clear"""
        self.instructions.append((Opcodes.CLEAR_SCREEN, 0, 0))
    
    def _compile_pwm_write(self, node: ast.Call):
        """Compile PWM hardware operation"""
        if len(node.args) >= 2:
            # PWM channel and value - simplified
            self.instructions.append((Opcodes.PWM_WRITE, 0, 0))
    
    def _compile_for_loop(self, node: ast.For):
        """Compile for loop with LOOP opcodes"""
        self.instructions.append((Opcodes.LOOP_START, 0, 0))
        
        for stmt in node.body:
            self._visit_node(stmt)
            
        self.instructions.append((Opcodes.LOOP_END, 0, 0))
    
    def _compile_if_statement(self, node: ast.If):
        """Compile if statement with conditional jumps"""
        # Simplified - just execute body for demo
        for stmt in node.body:
            self._visit_node(stmt)
    
    def _compile_arithmetic(self, node: ast.BinOp):
        """Compile arithmetic operations"""
        # Simplified - emit generic ADD operation
        self.instructions.append((Opcodes.ADD, 0, 0))
    
    def _get_var_id(self, var_name: str) -> int:
        """Get or create variable ID"""
        if var_name not in self.variables:
            self.variables[var_name] = len(self.variables)
        return self.variables[var_name]


class CompilerError(Exception):
    pass


def create_program_sheet(instructions: List[Tuple[int, int, int]], 
                        tiles_per_row: int = 16) -> Image.Image:
    """Create executable pixel sheet from instruction sequence"""
    
    if not instructions:
        return Image.new('L', (TILE_SIZE, TILE_SIZE), WHITE)
    
    # Calculate sheet dimensions
    num_tiles = len(instructions)
    num_rows = math.ceil(num_tiles / tiles_per_row)
    sheet_width = tiles_per_row * TILE_SIZE
    sheet_height = num_rows * TILE_SIZE
    
    # Create sheet image
    sheet = Image.new('L', (sheet_width, sheet_height), WHITE)
    
    # Add fiducials at corners for analog alignment
    draw = ImageDraw.Draw(sheet)
    fid_size = FIDUCIAL_SIZE
    
    # Corner fiducials (solid black squares)
    positions = [
        (0, 0), 
        (sheet_width - fid_size, 0),
        (0, sheet_height - fid_size),
        (sheet_width - fid_size, sheet_height - fid_size)
    ]
    
    for x, y in positions:
        draw.rectangle([x, y, x + fid_size - 1, y + fid_size - 1], fill=BLACK)
    
    # Create tile encoder
    encoder = PixelTile()
    
    # Encode each instruction as a tile
    for i, (opcode, operand_hi, operand_lo) in enumerate(instructions):
        row = i // tiles_per_row
        col = i % tiles_per_row
        
        tile_x = col * TILE_SIZE
        tile_y = row * TILE_SIZE
        
        # Skip if position conflicts with fiducials
        if (tile_x, tile_y) in positions:
            continue
            
        tile_img = encoder.encode_tile(opcode, operand_hi, operand_lo)
        sheet.paste(tile_img, (tile_x, tile_y))
    
    return sheet


def decode_program_sheet(sheet_img: Image.Image, 
                        tiles_per_row: Optional[int] = None) -> List[Tuple[int, int, int, float]]:
    """Decode executable pixel sheet back to instructions"""
    
    sheet_width, sheet_height = sheet_img.size
    
    if tiles_per_row is None:
        tiles_per_row = sheet_width // TILE_SIZE
    
    num_rows = sheet_height // TILE_SIZE
    
    # Create decoder
    decoder = PixelTile()
    instructions = []
    
    # Decode each tile position
    for row in range(num_rows):
        for col in range(tiles_per_row):
            tile_x = col * TILE_SIZE
            tile_y = row * TILE_SIZE
            
            # Extract tile image
            tile_img = sheet_img.crop((tile_x, tile_y, 
                                     tile_x + TILE_SIZE, 
                                     tile_y + TILE_SIZE))
            
            # Skip if this looks like a fiducial (all black)
            tile_array = np.array(tile_img.convert('L'))
            if np.mean(tile_array) < 64:  # Very dark = fiducial
                continue
            
            # Decode tile
            opcode, op_hi, op_lo, correlation = decoder.decode_tile(tile_img)
            instructions.append((opcode, op_hi, op_lo, correlation))
    
    return instructions


def instructions_to_uvir_csv(instructions: List[Tuple[int, int, int]]) -> List[str]:
    """Convert instruction sequence to UVIR CSV format"""
    
    csv_lines = ['frame,time,op,x,y,w,h,r,g,b,intensity,text,id']
    
    frame = 0
    time = 0.0
    
    # Execution state
    x = y = w = h = 0
    r = g = b = 255
    
    for opcode, op_hi, op_lo in instructions:
        op_name = Opcodes.name(opcode)
        
        if opcode == Opcodes.CLEAR_SCREEN:
            csv_lines.append(f"{frame},{time:.3f},CLEAR,,,,,{r},{g},{b},1.0,,")
            
        elif opcode == Opcodes.DRAW_RECT:
            csv_lines.append(f"{frame},{time:.3f},RECT,{x},{y},{w},{h},{r},{g},{b},1.0,,")
            
        elif opcode == Opcodes.DRAW_TEXT:
            csv_lines.append(f"{frame},{time:.3f},TEXT,{x},{y},,,,{r},{g},{b},1.0,Sample Text,")
            
        elif opcode == Opcodes.SET_COLOR:
            r, g, b = op_hi, op_lo, 128  # Simplified color setting
            
        elif opcode == Opcodes.COMMIT_FRAME:
            csv_lines.append(f"{frame},{time:.3f},COMMIT,,,,,,,1.0,,")
            frame += 1
            time += 0.016  # ~60 FPS
            
        elif opcode == Opcodes.PWM_WRITE:
            csv_lines.append(f"{frame},{time:.3f},PWM,{op_hi},{op_lo},,,,,,1.0,,")
            
        elif opcode == Opcodes.HALT:
            break
            
        # Add other opcode translations as needed
    
    return csv_lines


def main():
    parser = argparse.ArgumentParser(
        description="Pixel-Executable Transpiler for VisualPython AVOS",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Compile command
    compile_parser = subparsers.add_parser('compile', help='Compile Python to pixel sheet')
    compile_parser.add_argument('--src', required=True, help='Python source file')
    compile_parser.add_argument('--out', required=True, help='Output PNG file')
    compile_parser.add_argument('--tiles-per-row', type=int, default=16, help='Tiles per row')
    compile_parser.add_argument('--debug', action='store_true', help='Save debug info')
    
    # Decode command  
    decode_parser = subparsers.add_parser('decode', help='Decode pixel sheet to CSV')
    decode_parser.add_argument('--sheet', required=True, help='Input PNG file')
    decode_parser.add_argument('--csv', required=True, help='Output CSV file')
    decode_parser.add_argument('--tiles-per-row', type=int, help='Tiles per row (auto-detect if omitted)')
    
    # Demo command
    demo_parser = subparsers.add_parser('demo', help='Run built-in demo')
    demo_parser.add_argument('--out-dir', default='output', help='Output directory')
    
    args = parser.parse_args()
    
    if args.command == 'compile':
        compile_command(args)
    elif args.command == 'decode':
        decode_command(args)
    elif args.command == 'demo':
        demo_command(args)
    else:
        parser.print_help()


def compile_command(args):
    """Compile Python source to pixel sheet"""
    src_path = Path(args.src)
    
    if not src_path.exists():
        print(f"❌ Source file not found: {src_path}")
        return
    
    # Read source
    with open(src_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    print(f"📖 Compiling {src_path}...")
    
    # Compile to instructions
    compiler = VisualPythonCompiler()
    try:
        instructions = compiler.compile_source(source_code)
        print(f"✅ Generated {len(instructions)} instructions")
        
        # Create pixel sheet
        sheet = create_program_sheet(instructions, args.tiles_per_row)
        sheet.save(args.out)
        
        print(f"💾 Saved executable pixel sheet: {args.out}")
        
        if args.debug:
            # Save debug info
            debug_path = Path(args.out).with_suffix('.json')
            debug_info = {
                'source_file': str(src_path),
                'instructions': [
                    {'opcode': op, 'operand_hi': hi, 'operand_lo': lo, 'mnemonic': Opcodes.name(op)}
                    for op, hi, lo in instructions
                ],
                'variables': compiler.variables,
                'tiles_per_row': args.tiles_per_row
            }
            
            with open(debug_path, 'w') as f:
                json.dump(debug_info, f, indent=2)
            
            print(f"🐛 Saved debug info: {debug_path}")
        
    except CompilerError as e:
        print(f"❌ Compilation error: {e}")


def decode_command(args):
    """Decode pixel sheet to CSV"""
    sheet_path = Path(args.sheet)
    
    if not sheet_path.exists():
        print(f"❌ Sheet file not found: {sheet_path}")
        return
    
    print(f"🔍 Decoding {sheet_path}...")
    
    # Load and decode sheet
    sheet_img = Image.open(sheet_path).convert('L')
    decoded = decode_program_sheet(sheet_img, args.tiles_per_row)
    
    # Filter by correlation threshold
    threshold = 0.7
    good_instructions = []
    bad_count = 0
    
    for opcode, op_hi, op_lo, correlation in decoded:
        if correlation >= threshold:
            good_instructions.append((opcode, op_hi, op_lo))
        else:
            bad_count += 1
    
    print(f"📊 Decoded {len(good_instructions)} instructions ({bad_count} below threshold)")
    
    # Convert to CSV
    csv_lines = instructions_to_uvir_csv(good_instructions)
    
    # Save CSV
    with open(args.csv, 'w', encoding='utf-8') as f:
        f.write('\n'.join(csv_lines))
    
    print(f"💾 Saved UVIR CSV: {args.csv}")


def demo_command(args):
    """Run built-in demo"""
    output_dir = Path(args.out_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Create demo source
    demo_source = """
# VisualPython AVOS Pixel-Executable Demo
print("Hello Analog World!")

x = 100
y = 50
w = 200
h = 100

clear()
rect(x, y, w, h)
commit()

for i in range(3):
    x = x + 30
    rect(x, y, 60, 40)
    commit()

pwm_write(9, 128)  # Hardware control
"""
    
    demo_file = output_dir / 'demo.py'
    with open(demo_file, 'w') as f:
        f.write(demo_source)
    
    print(f"📝 Created demo source: {demo_file}")
    
    # Compile demo
    compiler = VisualPythonCompiler()
    instructions = compiler.compile_source(demo_source)
    
    # Create pixel sheet
    sheet_img = create_program_sheet(instructions, tiles_per_row=12)
    sheet_path = output_dir / 'demo_program_sheet.png'
    sheet_img.save(sheet_path)
    
    print(f"🎨 Created pixel sheet: {sheet_path}")
    
    # Decode back to CSV
    decoded = decode_program_sheet(sheet_img, tiles_per_row=12)
    good_instructions = [(op, hi, lo) for op, hi, lo, corr in decoded if corr >= 0.5]
    
    csv_lines = instructions_to_uvir_csv(good_instructions)
    csv_path = output_dir / 'demo_output.csv'
    
    with open(csv_path, 'w') as f:
        f.write('\n'.join(csv_lines))
    
    print(f"📊 Generated CSV: {csv_path}")
    
    print("\n🎯 Demo complete! Try:")
    print(f"   python visualpython_unified.py csv play {csv_path} --backend sim")


if __name__ == '__main__':
    main()