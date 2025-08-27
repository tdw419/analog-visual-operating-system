#!/usr/bin/env python3
"""
Analog Code Workbench - 4-Pane Visual Development Environment

This creates a visual development environment with 4 synchronized panes:
1. Source Code (left) - Original Python/analog code (editable)
2. Pixel Sheet (top-right) - Tile-encoded program view (visual tiles)  
3. Analog IR (bottom-left) - CSV/IR representation (editable)
4. Result Canvas (bottom-right) - Live execution preview

The workbench demonstrates the complete source → analog → execution pipeline
and provides the foundation for turning any source code into analog-executable form.

Dependencies: tkinter (built-in), Pillow for image processing
Run: python analog_code_workbench.py
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
import csv
import io
import re
import time
import threading
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image, ImageTk, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: Pillow not available. Install with: pip install pillow")

# === Tile Encoding System ===
TILE_SIZE = 16
PAYLOAD_SIZE = 12
MARGIN = (TILE_SIZE - PAYLOAD_SIZE) // 2
MINI_CELL = PAYLOAD_SIZE // 4

@dataclass
class Opcodes:
    # Basic drawing
    NOP = 0x0
    CLEAR = 0x1
    SET_GRAY = 0x2
    MOVE_X = 0x3
    MOVE_Y = 0x4
    SET_W = 0x5
    SET_H = 0x6
    DRAW_RECT = 0x7
    # Frame control  
    COMMIT = 0x8
    SLEEP = 0x9
    # Analog I/O
    DAC_WRITE = 0xA
    ADC_READ = 0xB
    PWM_OUT = 0xC
    # Sync/timing
    SYNC_ROW = 0xD

class TileEncoder:
    """Encodes opcodes into visual tiles for analog execution"""
    
    def __init__(self):
        self.opcodes = Opcodes()
    
    def pack_bits(self, opcode: int, operand: int) -> List[int]:
        """Pack opcode and operand into 16 bits with parity"""
        opcode &= 0xF
        operand &= 0xFF
        
        hi_nibble = (operand >> 4) & 0xF
        lo_nibble = operand & 0xF
        parity = (opcode ^ hi_nibble ^ lo_nibble) & 0xF
        
        nibbles = [opcode, hi_nibble, lo_nibble, parity]
        bits = []
        for nibble in nibbles:
            for i in range(4):
                bits.append((nibble >> i) & 1)
        return bits
    
    def create_tile(self, opcode: int, operand: int) -> Image.Image:
        """Create a visual tile for the given opcode and operand"""
        if not PIL_AVAILABLE:
            return None
            
        img = Image.new('RGB', (TILE_SIZE, TILE_SIZE), 'white')
        draw = ImageDraw.Draw(img)
        
        bits = self.pack_bits(opcode, operand)
        
        # Draw the 4x4 bit pattern
        for bit_idx, bit in enumerate(bits):
            row = bit_idx // 4
            col = bit_idx % 4
            
            x = MARGIN + col * MINI_CELL
            y = MARGIN + row * MINI_CELL
            
            color = 'black' if bit else 'white'
            draw.rectangle([x, y, x + MINI_CELL - 1, y + MINI_CELL - 1], fill=color)
        
        # Draw border
        draw.rectangle([0, 0, TILE_SIZE-1, TILE_SIZE-1], outline='gray')
        
        return img
    
    def create_program_sheet(self, operations: List[Tuple[int, int]], cols: int = 8) -> Image.Image:
        """Create a complete program sheet from operations"""
        if not PIL_AVAILABLE or not operations:
            return None
            
        rows = (len(operations) + cols - 1) // cols
        sheet_width = cols * TILE_SIZE
        sheet_height = rows * TILE_SIZE
        
        sheet = Image.new('RGB', (sheet_width, sheet_height), 'white')
        
        for idx, (opcode, operand) in enumerate(operations):
            tile = self.create_tile(opcode, operand)
            if tile:
                row = idx // cols
                col = idx % cols
                x = col * TILE_SIZE
                y = row * TILE_SIZE
                sheet.paste(tile, (x, y))
        
        return sheet

class SimpleTranspiler:
    """Simple transpiler for converting Python-like code to analog operations"""
    
    def __init__(self):
        self.encoder = TileEncoder()
        self.opcodes = Opcodes()
    
    def parse_code(self, code: str) -> List[Dict[str, Any]]:
        """Parse simple drawing commands into IR operations"""
        operations = []
        
        # Simple regex patterns for basic commands
        patterns = [
            (r'clear\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', 'clear'),
            (r'rect\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', 'rect'),
            (r'text\(\s*(\d+)\s*,\s*(\d+)\s*,\s*["\']([^"\']*)["\'].*\)', 'text'),
            (r'commit\(\s*\)', 'commit'),
            (r'sleep\(\s*(\d+)\s*\)', 'sleep'),
            (r'dac_write\(\s*(\d+)\s*,\s*(\d+)\s*\)', 'dac_write'),
        ]
        
        lines = code.split('\n')
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            matched = False
            for pattern, cmd_type in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    matched = True
                    if cmd_type == 'clear':
                        r, g, b = map(int, match.groups())
                        gray = int(0.299 * r + 0.587 * g + 0.114 * b)  # Convert to grayscale
                        operations.append({'op': 'CLEAR', 'opcode': self.opcodes.CLEAR, 'operand': gray, 'line': line_num})
                    elif cmd_type == 'rect':
                        x, y, w, h, gray = map(int, match.groups())
                        operations.extend([
                            {'op': 'MOVE_X', 'opcode': self.opcodes.MOVE_X, 'operand': x, 'line': line_num},
                            {'op': 'MOVE_Y', 'opcode': self.opcodes.MOVE_Y, 'operand': y, 'line': line_num},
                            {'op': 'SET_W', 'opcode': self.opcodes.SET_W, 'operand': w, 'line': line_num},
                            {'op': 'SET_H', 'opcode': self.opcodes.SET_H, 'operand': h, 'line': line_num},
                            {'op': 'SET_GRAY', 'opcode': self.opcodes.SET_GRAY, 'operand': gray, 'line': line_num},
                            {'op': 'DRAW_RECT', 'opcode': self.opcodes.DRAW_RECT, 'operand': 0, 'line': line_num},
                        ])
                    elif cmd_type == 'commit':
                        operations.append({'op': 'COMMIT', 'opcode': self.opcodes.COMMIT, 'operand': 0, 'line': line_num})
                    elif cmd_type == 'sleep':
                        ms = int(match.group(1))
                        operations.append({'op': 'SLEEP', 'opcode': self.opcodes.SLEEP, 'operand': min(ms, 255), 'line': line_num})
                    elif cmd_type == 'dac_write':
                        channel, value = int(match.group(1)), int(match.group(2))
                        operand = ((channel & 0x7) << 5) | ((value // 8) & 0x1F)
                        operations.append({'op': 'DAC_WRITE', 'opcode': self.opcodes.DAC_WRITE, 'operand': operand, 'line': line_num})
                    break
            
            if not matched and line.strip():
                # Unknown command - add as comment
                operations.append({'op': 'COMMENT', 'opcode': 0, 'operand': 0, 'line': line_num, 'text': line})
        
        return operations
    
    def ir_to_csv(self, operations: List[Dict[str, Any]]) -> str:
        """Convert IR operations to CSV format"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['frame', 'op', 'x', 'y', 'w', 'h', 'gray', 'text', 'line'])
        
        frame = 0
        x = y = w = h = gray = 0
        
        for op in operations:
            op_name = op['op']
            line_num = op.get('line', 0)
            
            if op_name == 'CLEAR':
                gray = op['operand']
                writer.writerow([frame, 'CLEAR', '', '', '', '', gray, '', line_num])
            elif op_name == 'MOVE_X':
                x = op['operand']
            elif op_name == 'MOVE_Y':
                y = op['operand']
            elif op_name == 'SET_W':
                w = op['operand']
            elif op_name == 'SET_H':
                h = op['operand']
            elif op_name == 'SET_GRAY':
                gray = op['operand']
            elif op_name == 'DRAW_RECT':
                writer.writerow([frame, 'RECT', x, y, w, h, gray, '', line_num])
            elif op_name == 'TEXT':
                text = op.get('text', '')
                writer.writerow([frame, 'TEXT', x, y, '', '', '', text, line_num])
            elif op_name == 'COMMIT':
                writer.writerow([frame, 'COMMIT', '', '', '', '', '', '', line_num])
                frame += 1
            elif op_name == 'SLEEP':
                writer.writerow([frame, 'SLEEP', op['operand'], '', '', '', '', '', line_num])
            elif op_name == 'DAC_WRITE':
                channel = (op['operand'] >> 5) & 0x7
                value = (op['operand'] & 0x1F) * 8
                writer.writerow([frame, 'DAC_WRITE', channel, value, '', '', '', '', line_num])
            elif op_name == 'COMMENT':
                text = op.get('text', '')
                writer.writerow([frame, 'COMMENT', '', '', '', '', '', f"# {text}", line_num])
        
        return output.getvalue()

class ResultRenderer:
    """Renders CSV operations as visual results"""
    
    def __init__(self, canvas_widget, width=300, height=200):
        self.canvas = canvas_widget
        self.width = width
        self.height = height
        self.canvas.configure(width=width, height=height, bg='black')
    
    def render_csv(self, csv_content: str):
        """Render CSV operations on the canvas"""
        self.canvas.delete("all")
        
        if not csv_content.strip():
            return
        
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            
            for row in reader:
                op = row.get('op', '').strip()
                if not op or op == 'COMMENT':
                    continue
                
                if op == 'CLEAR':
                    gray = int(row.get('gray', 0))
                    color = f"#{gray:02x}{gray:02x}{gray:02x}"
                    self.canvas.configure(bg=color)
                
                elif op == 'RECT':
                    x = int(row.get('x', 0))
                    y = int(row.get('y', 0))
                    w = int(row.get('w', 10))
                    h = int(row.get('h', 10))
                    gray = int(row.get('gray', 255))
                    
                    color = f"#{gray:02x}{gray:02x}{gray:02x}"
                    self.canvas.create_rectangle(x, y, x+w, y+h, fill=color, outline=color)
                
                elif op == 'TEXT':
                    x = int(row.get('x', 0))
                    y = int(row.get('y', 0))
                    text = row.get('text', '')
                    
                    self.canvas.create_text(x, y, text=text, fill='white', 
                                          font=('Courier', 8), anchor='nw')
                
        except Exception as e:
            self.canvas.create_text(self.width//2, self.height//2, 
                                  text=f"CSV Error: {str(e)}", 
                                  fill='red', font=('Courier', 10))

class AnalogCodeWorkbench:
    """Main 4-pane workbench application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Analog Code Workbench - Source to Analog Execution")
        self.root.geometry("1200x800")
        
        self.transpiler = SimpleTranspiler()
        self.encoder = TileEncoder()
        
        self.auto_update = tk.BooleanVar(value=True)
        self.use_viewer_mode = tk.BooleanVar(value=False)
        self.last_update_time = 0
        self.update_delay = 0.5
        
        # Import viewer adapter for VisualPython integration
        try:
            import viewer_adapter
            self.viewer_adapter = viewer_adapter
            self.has_viewer_adapter = True
        except ImportError:
            self.viewer_adapter = None
            self.has_viewer_adapter = False
        
        self.setup_ui()
        self.load_example_code()
        self.update_all_panes()
    
    def setup_ui(self):
        """Create the 4-pane UI"""
        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(toolbar, text="▶ Update", command=self.update_all_panes).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(toolbar, text="Auto-update", variable=self.auto_update).pack(side=tk.LEFT, padx=10)
        
        # Viewer mode controls
        if self.has_viewer_adapter:
            ttk.Separator(toolbar, orient='vertical').pack(side=tk.LEFT, fill='y', padx=5)
            ttk.Checkbutton(toolbar, text="Viewer Mode", variable=self.use_viewer_mode,
                          command=self.toggle_viewer_mode).pack(side=tk.LEFT, padx=5)
            ttk.Button(toolbar, text="Run with VisualPython", 
                      command=self.run_with_viewer).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(toolbar, text="Source → Pixel Tiles → CSV → Result").pack(side=tk.LEFT, padx=20)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready - Edit source code in Pane 1")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Main paned window (2x2 grid)
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left column (Panes 1 & 3)
        left_pane = ttk.PanedWindow(main_pane, orient=tk.VERTICAL)
        main_pane.add(left_pane, weight=1)
        
        # Right column (Panes 2 & 4)
        right_pane = ttk.PanedWindow(main_pane, orient=tk.VERTICAL)
        main_pane.add(right_pane, weight=1)
        
        # === Pane 1: Source Code (top-left) ===
        pane1_frame = ttk.LabelFrame(left_pane, text="Pane 1: Source Code (Analog Python)", padding=5)
        left_pane.add(pane1_frame, weight=1)
        
        self.source_text = scrolledtext.ScrolledText(pane1_frame, height=15, width=40, 
                                                   font=('Courier', 10))
        self.source_text.pack(fill=tk.BOTH, expand=True)
        self.source_text.bind('<KeyRelease>', self.on_source_change)
        
        # === Pane 3: Analog IR/CSV (bottom-left) ===
        pane3_frame = ttk.LabelFrame(left_pane, text="Pane 3: Analog IR (CSV Operations)", padding=5)
        left_pane.add(pane3_frame, weight=1)
        
        self.csv_text = scrolledtext.ScrolledText(pane3_frame, height=15, width=40, 
                                                font=('Courier', 9))
        self.csv_text.pack(fill=tk.BOTH, expand=True)
        self.csv_text.bind('<KeyRelease>', self.on_csv_change)
        
        # === Pane 2: Pixel Sheet (top-right) ===
        pane2_frame = ttk.LabelFrame(right_pane, text="Pane 2: Analog Pixel Tiles (Program Sheet)", padding=5)
        right_pane.add(pane2_frame, weight=1)
        
        self.pixel_canvas = tk.Canvas(pane2_frame, bg='white', width=400, height=300)
        self.pixel_canvas.pack(fill=tk.BOTH, expand=True)
        
        # === Pane 4: Result Canvas (bottom-right) ===
        pane4_frame = ttk.LabelFrame(right_pane, text="Pane 4: Execution Result (Live Preview)", padding=5)
        right_pane.add(pane4_frame, weight=1)
        
        self.result_canvas = tk.Canvas(pane4_frame, bg='black', width=400, height=300)
        self.result_canvas.pack(fill=tk.BOTH, expand=True)
        
        self.result_renderer = ResultRenderer(self.result_canvas, 400, 300)
    
    def load_example_code(self):
        """Load example code into the source pane"""
        example = '''# Analog Code Example - Edit and watch the magic!
# This creates visual operations for analog execution

# Method 1: Manual function calls (works in both modes)
clear(0, 20, 40)
rect(50, 30, 100, 40, 100)
rect(60, 80, 80, 30, 150)
rect(70, 130, 60, 25, 200)
text(55, 35, "ANALOG")
text(65, 85, "CODE")  
text(75, 135, "TILES")
commit()

# Animation sequence
for i in range(3):
    clear(0, 20, 40)
    offset = i * 50
    gray = 100 + i * 40
    rect(100 + offset, 50, 40, 40, gray)
    text(105 + offset, 60, f"F{i}")
    commit()
    sleep(100)

# Hardware control example
dac_write(2, 200)   # DAC channel 2, value 200
sync_row(1)         # Synchronization marker

# This code becomes pixel tiles → CSV → analog execution!
# 
# USAGE:
# 1. Edit this code and click Update (manual mode)
# 2. OR check "Viewer Mode" and click "Run with VisualPython"
#    to capture operations dynamically
'''
        self.source_text.delete(1.0, tk.END)
        self.source_text.insert(1.0, example)
    
    def on_source_change(self, event=None):
        """Handle source code changes"""
        if self.auto_update.get():
            self.schedule_update()
    
    def on_csv_change(self, event=None):
        """Handle CSV changes"""
        if self.auto_update.get():
            self.update_result_pane()
    
    def schedule_update(self):
        """Schedule an update with debouncing"""
        self.last_update_time = time.time()
        self.root.after(int(self.update_delay * 1000), self.delayed_update)
    
    def delayed_update(self):
        """Perform delayed update if no recent changes"""
        if time.time() - self.last_update_time >= self.update_delay:
            self.update_all_panes()
    
    def update_all_panes(self):
        """Update all panes based on source code"""
        try:
            source_code = self.source_text.get(1.0, tk.END)
            
            # Step 1: Transpile source to IR operations
            operations = self.transpiler.parse_code(source_code)
            op_count = len([op for op in operations if op['op'] != 'COMMENT'])
            
            # Step 2: Convert IR to CSV
            csv_content = self.transpiler.ir_to_csv(operations)
            
            # Step 3: Update CSV pane
            self.csv_text.delete(1.0, tk.END)
            self.csv_text.insert(1.0, csv_content)
            
            # Step 4: Create pixel sheet
            self.update_pixel_sheet(operations)
            
            # Step 5: Update result canvas
            self.result_renderer.render_csv(csv_content)
            
            self.status_var.set(f"Updated: {op_count} operations, {len(csv_content.split())} CSV lines")
            
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
    
    def update_pixel_sheet(self, operations: List[Dict[str, Any]]):
        """Update the pixel sheet display"""
        if not PIL_AVAILABLE:
            self.pixel_canvas.delete("all")
            self.pixel_canvas.create_text(200, 150, text="PIL not available\nInstall with: pip install pillow", 
                                        fill='red', font=('Arial', 12))
            return
        
        # Create tile operations (exclude comments and text for now)
        tile_ops = []
        for op in operations:
            if op['op'] not in ['COMMENT', 'TEXT']:
                tile_ops.append((op['opcode'], op['operand']))
        
        if not tile_ops:
            self.pixel_canvas.delete("all")
            self.pixel_canvas.create_text(200, 150, text="No operations to display", 
                                        fill='gray', font=('Arial', 12))
            return
        
        # Create program sheet
        sheet = self.encoder.create_program_sheet(tile_ops, cols=8)
        if sheet:
            # Scale up for better visibility
            scale_factor = 3
            scaled_sheet = sheet.resize((sheet.width * scale_factor, sheet.height * scale_factor), 
                                      Image.NEAREST)
            
            # Convert to PhotoImage
            self.pixel_photo = ImageTk.PhotoImage(scaled_sheet)
            
            # Clear canvas and add image
            self.pixel_canvas.delete("all")
            self.pixel_canvas.create_image(10, 10, anchor=tk.NW, image=self.pixel_photo)
    
    def update_result_pane(self):
        """Update only the result pane from CSV"""
        csv_content = self.csv_text.get(1.0, tk.END)
        self.result_renderer.render_csv(csv_content)
    
    def toggle_viewer_mode(self):
        """Toggle between manual code editing and viewer capture mode"""
        if self.use_viewer_mode.get():
            self.source_text.configure(state='disabled')
            self.status_var.set("Viewer Mode: Use 'Run with VisualPython' to capture operations")
        else:
            self.source_text.configure(state='normal')
            self.status_var.set("Manual Mode: Edit source code directly")
    
    def run_with_viewer(self):
        """Execute code using VisualPython viewer and capture operations"""
        if not self.has_viewer_adapter:
            messagebox.showerror("Viewer Error", "Viewer adapter not available")
            return
        
        try:
            # Reset adapter
            self.viewer_adapter.reset()
            
            # Get source code from Pane 1
            source_code = self.source_text.get(1.0, tk.END)
            
            # Execute the code in a context where adapter functions are available
            exec_globals = {
                'RECT': self.viewer_adapter.RECT,
                'TEXT': self.viewer_adapter.TEXT,
                'CLEAR': self.viewer_adapter.CLEAR,
                'COMMIT': self.viewer_adapter.COMMIT,
                'SLEEP': self.viewer_adapter.SLEEP,
                'DAC_WRITE': self.viewer_adapter.DAC_WRITE,
                'SYNC_ROW': self.viewer_adapter.SYNC_ROW,
                'clear': self.viewer_adapter.CLEAR,
                'rect': self.viewer_adapter.RECT,
                'text': self.viewer_adapter.TEXT,
                'commit': self.viewer_adapter.COMMIT,
                'sleep': self.viewer_adapter.SLEEP,
                'dac_write': self.viewer_adapter.DAC_WRITE,
                'sync_row': self.viewer_adapter.SYNC_ROW,
            }
            
            # Execute the code
            exec(source_code, exec_globals)
            
            # Get captured CSV and update Pane 3
            captured_csv = self.viewer_adapter.get_csv()
            self.csv_text.delete(1.0, tk.END)
            self.csv_text.insert(1.0, captured_csv)
            
            # Update displays
            operations = self.parse_captured_operations()
            self.update_pixel_sheet(operations)
            self.result_renderer.render_csv(captured_csv)
            
            # Show summary
            summary = self.viewer_adapter.get_operations_summary()
            self.status_var.set(f"Captured: {summary.split()[1]} operations via VisualPython")
            
        except Exception as e:
            messagebox.showerror("Execution Error", f"Error running with viewer:\n{str(e)}")
            self.status_var.set(f"Execution error: {str(e)}")
    
    def parse_captured_operations(self):
        """Parse operations from viewer adapter for tile encoding"""
        operations = []
        
        if not self.has_viewer_adapter:
            return operations
        
        for op in self.viewer_adapter._global_adapter.operations:
            op_type = op.op_type
            params = op.params
            
            if op_type == "CLEAR":
                operations.append({'op': 'CLEAR', 'opcode': self.transpiler.opcodes.CLEAR, 
                                 'operand': params.get('gray', 0), 'line': 0})
            elif op_type == "RECT":
                # Convert RECT to sequence of operations
                operations.extend([
                    {'op': 'MOVE_X', 'opcode': self.transpiler.opcodes.MOVE_X, 
                     'operand': params.get('x', 0), 'line': 0},
                    {'op': 'MOVE_Y', 'opcode': self.transpiler.opcodes.MOVE_Y, 
                     'operand': params.get('y', 0), 'line': 0},
                    {'op': 'SET_W', 'opcode': self.transpiler.opcodes.SET_W, 
                     'operand': params.get('w', 0), 'line': 0},
                    {'op': 'SET_H', 'opcode': self.transpiler.opcodes.SET_H, 
                     'operand': params.get('h', 0), 'line': 0},
                    {'op': 'SET_GRAY', 'opcode': self.transpiler.opcodes.SET_GRAY, 
                     'operand': params.get('gray', 128), 'line': 0},
                    {'op': 'DRAW_RECT', 'opcode': self.transpiler.opcodes.DRAW_RECT, 
                     'operand': 0, 'line': 0},
                ])
            elif op_type == "COMMIT":
                operations.append({'op': 'COMMIT', 'opcode': self.transpiler.opcodes.COMMIT, 
                                 'operand': 0, 'line': 0})
            elif op_type == "SLEEP":
                operations.append({'op': 'SLEEP', 'opcode': self.transpiler.opcodes.SLEEP, 
                                 'operand': params.get('duration_ms', 0), 'line': 0})
            elif op_type == "DAC_WRITE":
                channel = params.get('channel', 0)
                value = params.get('value', 0)
                operand = ((channel & 0x7) << 5) | ((value // 8) & 0x1F)
                operations.append({'op': 'DAC_WRITE', 'opcode': self.transpiler.opcodes.DAC_WRITE, 
                                 'operand': operand, 'line': 0})
        
        return operations
    
    def run(self):
        """Start the application"""
        print("🚀 Analog Code Workbench Starting...")
        print("💡 Edit the source code in Pane 1 and watch:")
        print("   - Pane 2: See your code as pixel tiles")
        print("   - Pane 3: View the CSV operations")
        print("   - Pane 4: Watch the live execution result")
        print("\n📖 Try editing the example code to see real-time updates!")
        
        self.root.mainloop()

if __name__ == "__main__":
    app = AnalogCodeWorkbench()
    app.run()