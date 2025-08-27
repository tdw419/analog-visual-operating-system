# simple_analog_workbench.py
"""
Simplified Analog Code Workbench - 4-pane development environment

This is a streamlined version that focuses on the core integration between
your Python viewer and the analog execution system.

Dependencies: tkinter (built-in), Pillow (pip install pillow)
Run: python simple_analog_workbench.py
"""

import tkinter as tk
from tkinter import scrolledtext, Button, Label, messagebox
import importlib.util
import traceback
import sys
import os
import inspect
import pathlib
import importlib
import re

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

try:
    from PIL import Image, ImageDraw, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: Pillow not available. Install with: pip install pillow")
    print("Tile visualization will be disabled.")

# Simple tile encoder for visualization
TILE_SIZE = 16
CELL_SIZE = 3

# PXOS Schema implementation
class PXOSSchema:
    """PXOS Native Op Schema v1.0 implementation"""
    
    SCHEMA_VERSION = "pxos-ops/1.0"
    
    def __init__(self):
        self.ops = []
        self.metadata = {
            "schemaVersion": self.SCHEMA_VERSION,
            "profile": "default",
            "cols": 16,
            "page": 0
        }
    
    def add_op(self, op_type, **kwargs):
        """Add an operation with validation"""
        op = {"op": op_type}
        op.update(kwargs)
        self.ops.append(op)
    
    def to_csv(self):
        """Convert to CSV format"""
        lines = [f"# {self.SCHEMA_VERSION}, profile={self.metadata['profile']}, cols={self.metadata['cols']}"]
        
        for op in self.ops:
            op_type = op["op"]
            if op_type == "RECT":
                line = f"RECT,{op['x']},{op['y']},{op['w']},{op['h']},{op.get('r',128)},{op.get('g',128)},{op.get('b',128)}"
            elif op_type == "SLEEP":
                line = f"SLEEP,{op['ms']}"
            elif op_type == "DAC_WRITE":
                line = f"DAC_WRITE,{op['ch']},{op['val']}"
            elif op_type == "FILTER":
                line = f"FILTER,{op['type']},{op['fc']},{op['src']},{op['dst']}"
            elif op_type == "INTEGRATE":
                line = f"INTEGRATE,{op['tau']},{op['src']},{op['dst']}"
            elif op_type == "SYNC_ROW":
                line = f"SYNC_ROW,{op['i']}"
            elif op_type == "COMMIT":
                line = "COMMIT"
            else:
                line = op_type  # Fallback for unknown ops
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def to_analog_text(self):
        """Convert to human-readable analog text representation"""
        lines = [f"# PXOS Analog Program - {self.metadata['profile']} profile"]
        lines.append(f"# Page {self.metadata['page']}, Tile grid: {self.metadata['cols']} columns")
        lines.append("")
        
        for i, op in enumerate(self.ops):
            op_type = op["op"]
            
            if op_type == "RECT":
                lines.append(f"draw_rectangle({op['x']}, {op['y']}, {op['w']}, {op['h']})")
                lines.append(f"  ├─ color: rgb({op.get('r',128)}, {op.get('g',128)}, {op.get('b',128)})")
            elif op_type == "SLEEP":
                lines.append(f"wait({op['ms']}ms)")
            elif op_type == "DAC_WRITE":
                voltage = op['val'] * 5.0 / 255  # Convert to 0-5V range
                lines.append(f"analog_output(channel_{op['ch']}, {voltage:.2f}V)")
            elif op_type == "FILTER":
                lines.append(f"analog_filter({op['type']}, {op['fc']}Hz)")
                lines.append(f"  ├─ input: channel_{op['src']}")
                lines.append(f"  └─ output: channel_{op['dst']}")
            elif op_type == "INTEGRATE":
                lines.append(f"analog_integrator(τ={op['tau']}ms)")
                lines.append(f"  ├─ input: channel_{op['src']}")
                lines.append(f"  └─ output: channel_{op['dst']}")
            elif op_type == "SYNC_ROW":
                lines.append(f"sync_marker(row_{op['i']})")
            elif op_type == "COMMIT":
                lines.append("commit_frame()")
                lines.append("")
        
        return "\n".join(lines)
    
    def from_csv(self, csv_text):
        """Parse from CSV format"""
        lines = csv_text.splitlines()
        self.ops = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                # Parse metadata from comments
                if "profile=" in line:
                    try:
                        self.metadata["profile"] = line.split("profile=")[1].split(",")[0].split()[0]
                    except:
                        pass
                if "cols=" in line:
                    try:
                        self.metadata["cols"] = int(line.split("cols=")[1].split(",")[0].split()[0])
                    except:
                        pass
                continue
            
            parts = line.split(',')
            if not parts:
                continue
                
            op_type = parts[0].strip().upper()
            
            try:
                if op_type == "RECT" and len(parts) >= 8:
                    self.add_op("RECT", 
                        x=int(parts[1]), y=int(parts[2]),
                        w=int(parts[3]), h=int(parts[4]),
                        r=int(parts[5]), g=int(parts[6]), b=int(parts[7])
                    )
                elif op_type == "SLEEP" and len(parts) >= 2:
                    self.add_op("SLEEP", ms=int(parts[1]))
                elif op_type == "DAC_WRITE" and len(parts) >= 3:
                    self.add_op("DAC_WRITE", ch=int(parts[1]), val=int(parts[2]))
                elif op_type == "FILTER" and len(parts) >= 5:
                    self.add_op("FILTER", type=parts[1], fc=int(parts[2]), src=int(parts[3]), dst=int(parts[4]))
                elif op_type == "INTEGRATE" and len(parts) >= 4:
                    self.add_op("INTEGRATE", tau=float(parts[1]), src=int(parts[2]), dst=int(parts[3]))
                elif op_type == "SYNC_ROW" and len(parts) >= 2:
                    self.add_op("SYNC_ROW", i=int(parts[1]))
                elif op_type == "COMMIT":
                    self.add_op("COMMIT")
            except (ValueError, IndexError):
                # Skip malformed lines
                continue
    
    def from_analog_text(self, analog_text):
        """Parse from analog text representation"""
        lines = analog_text.splitlines()
        self.ops = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('├─') or line.startswith('└─'):
                continue
            
            # Parse analog text format
            if line.startswith('draw_rectangle('):
                # Extract parameters: draw_rectangle(x, y, w, h)
                import re
                match = re.search(r'draw_rectangle\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)', line)
                if match:
                    self.add_op("RECT", 
                        x=int(match.group(1)), y=int(match.group(2)),
                        w=int(match.group(3)), h=int(match.group(4)),
                        r=128, g=128, b=128  # Default gray
                    )
            elif line.startswith('wait('):
                match = re.search(r'wait\((\d+)ms\)', line)
                if match:
                    self.add_op("SLEEP", ms=int(match.group(1)))
            elif line.startswith('analog_output('):
                match = re.search(r'analog_output\(channel_(\d+),\s*([\d.]+)V\)', line)
                if match:
                    ch = int(match.group(1))
                    voltage = float(match.group(2))
                    val = int(voltage * 255 / 5.0)  # Convert from voltage to 0-255
                    self.add_op("DAC_WRITE", ch=ch, val=val)
            elif line.startswith('commit_frame()'):
                self.add_op("COMMIT")

def create_simple_tile(opcode, operand):
    """Create a simple visual representation of an operation"""
    if not PIL_AVAILABLE:
        return None
    
    img = Image.new('RGB', (TILE_SIZE, TILE_SIZE), 'white')
    draw = ImageDraw.Draw(img)
    
    # Draw border
    draw.rectangle([0, 0, TILE_SIZE-1, TILE_SIZE-1], outline='black')
    
    # Simple encoding: opcode as color intensity, operand as pattern
    intensity = min(255, opcode * 30)
    color = (intensity, intensity, intensity)
    
    # Fill with pattern based on operand
    for y in range(2, TILE_SIZE-2, 2):
        for x in range(2, TILE_SIZE-2, 2):
            if (x + y + operand) % 4 == 0:
                draw.rectangle([x, y, x+1, y+1], fill=color)
    
    return img

def create_tile_sheet(operations, cols=8):
    """Create a sheet of tiles from operations"""
    if not PIL_AVAILABLE or not operations:
        return None
    
    rows = (len(operations) + cols - 1) // cols
    sheet_width = cols * TILE_SIZE
    sheet_height = rows * TILE_SIZE
    
    sheet = Image.new('RGB', (sheet_width, sheet_height), 'white')
    
    for i, (opcode, operand) in enumerate(operations):
        if i >= cols * rows:
            break
        
        tile = create_simple_tile(opcode, operand)
        if tile:
            row = i // cols
            col = i % cols
            x = col * TILE_SIZE
            y = row * TILE_SIZE
            sheet.paste(tile, (x, y))
    
    # Scale up for better visibility
    scale_factor = 3
    scaled_sheet = sheet.resize(
        (sheet_width * scale_factor, sheet_height * scale_factor), 
        Image.NEAREST
    )
    
    return scaled_sheet

# Simple opcode mapping
OPCODES = {
    'RECT': 1,
    'COMMIT': 2, 
    'SLEEP': 3,
    'SYNC_ROW': 4,
    'DAC_WRITE': 5
}

def csv_to_operations(csv_text):
    """Convert CSV text to simple operations for visualization"""
    operations = []
    
    for line in csv_text.strip().split('\n'):
        if not line.strip():
            continue
        
        parts = line.split(',')
        if not parts:
            continue
        
        op_name = parts[0].strip().upper()
        if op_name in OPCODES:
            opcode = OPCODES[op_name]
            # Use first parameter as operand, or 0 if none
            operand = int(parts[1]) if len(parts) > 1 and parts[1].strip() else 0
            operations.append((opcode, operand))
    
    return operations

class SimpleWorkbench(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PXOS Analog Code Workbench - 6-Pane Dual-Track View")
        self.geometry("1600x1000")
        
        # PXOS schema instance
        self.pxos_schema = PXOSSchema()
        
        # Track which pane was last edited to avoid circular updates
        self.last_edited = None
        
        self.create_widgets()
        self.load_example()
    
    def create_widgets(self):
        """Create the 6-pane UI with dual-track view"""
        
        # Title and instructions
        title_frame = tk.Frame(self)
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        Label(title_frame, text="PXOS Analog Code Workbench - 6-Pane Dual-Track View", 
              font=('Arial', 16, 'bold')).pack()
        Label(title_frame, text="Digital ↔ Analog Mirror → Tiles → CSV → Live Results", 
              font=('Arial', 10)).pack()
        
        # Main content frame with 6-pane layout
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Configure grid weights for 3x2 layout
        for i in range(3):
            main_frame.grid_columnconfigure(i, weight=1)
        for i in range(2):
            main_frame.grid_rowconfigure(i*2+1, weight=1)  # Rows 1 and 3
        
        # Top row labels
        Label(main_frame, text="1. Digital Source (Python)", font=('Arial', 10, 'bold')).grid(
            row=0, column=0, padx=5, pady=2, sticky='w')
        Label(main_frame, text="2. Analog Mirror (PXOS-Text)", font=('Arial', 10, 'bold')).grid(
            row=0, column=1, padx=5, pady=2, sticky='w')
        Label(main_frame, text="3. Analog Source Editor", font=('Arial', 10, 'bold')).grid(
            row=0, column=2, padx=5, pady=2, sticky='w')
        
        # Bottom row labels
        Label(main_frame, text="4. Analog Tiles (Visual Program)", font=('Arial', 10, 'bold')).grid(
            row=2, column=0, padx=5, pady=2, sticky='w')
        Label(main_frame, text="5. CSV/IR Operations", font=('Arial', 10, 'bold')).grid(
            row=2, column=1, padx=5, pady=2, sticky='w')
        Label(main_frame, text="6. Live Execution Results", font=('Arial', 10, 'bold')).grid(
            row=2, column=2, padx=5, pady=2, sticky='w')
        
        # Pane 1: Digital Python source (editable)
        self.digital_source_text = scrolledtext.ScrolledText(
            main_frame, width=30, height=12, font=('Courier', 9))
        self.digital_source_text.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')
        self.digital_source_text.bind('<KeyRelease>', self.on_digital_source_change)
        
        # Pane 2: Analog mirror text (generated from digital or editable)
        self.analog_mirror_text = scrolledtext.ScrolledText(
            main_frame, width=30, height=12, font=('Courier', 9))
        self.analog_mirror_text.grid(row=1, column=1, padx=5, pady=5, sticky='nsew')
        self.analog_mirror_text.bind('<KeyRelease>', self.on_analog_mirror_change)
        
        # Pane 3: Analog source editor (native PXOS programming)
        self.analog_source_text = scrolledtext.ScrolledText(
            main_frame, width=30, height=12, font=('Courier', 9))
        self.analog_source_text.grid(row=1, column=2, padx=5, pady=5, sticky='nsew')
        self.analog_source_text.bind('<KeyRelease>', self.on_analog_source_change)
        
        # Pane 4: Analog tiles visualization
        self.tiles_frame = tk.Frame(main_frame, bg='white', width=200, height=200)
        self.tiles_frame.grid(row=3, column=0, padx=5, pady=5, sticky='nsew')
        self.tiles_frame.grid_propagate(False)
        
        self.tiles_label = Label(self.tiles_frame, text="Tile sheet will appear here", 
                               bg='white')
        self.tiles_label.pack(expand=True)
        
        # Pane 5: CSV/IR operations (editable)
        self.csv_text = scrolledtext.ScrolledText(
            main_frame, width=30, height=12, font=('Courier', 9))
        self.csv_text.grid(row=3, column=1, padx=5, pady=5, sticky='nsew')
        self.csv_text.bind('<KeyRelease>', self.on_csv_change)
        
        # Pane 6: Live execution results
        self.result_canvas = tk.Canvas(main_frame, width=200, height=200, bg='black')
        self.result_canvas.grid(row=3, column=2, padx=5, pady=5, sticky='nsew')
        
        # Control buttons
        button_frame = tk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        Button(button_frame, text="Run Python Viewer", 
               command=self.run_viewer, bg='lightgreen').pack(side=tk.LEFT, padx=5)
        Button(button_frame, text="Digital→Analog", 
               command=self.translate_digital_to_analog, bg='lightblue').pack(side=tk.LEFT, padx=5)
        Button(button_frame, text="Analog→Digital", 
               command=self.translate_analog_to_digital, bg='lightcyan').pack(side=tk.LEFT, padx=5)
        Button(button_frame, text="Validate PXOS", 
               command=self.validate_pxos_schema, bg='lightyellow').pack(side=tk.LEFT, padx=5)
        Button(button_frame, text="Load Example", 
               command=self.load_example, bg='lightgray').pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready - Load example or run viewer")
        Label(button_frame, textvariable=self.status_var, 
              font=('Arial', 9)).pack(side=tk.RIGHT, padx=5)
    
    def load_example(self):
        """Load example demonstrating 6-pane dual-track workflow"""
        # Example digital Python source
        digital_example = '''# Digital source for analog execution
# This will be translated to PXOS analog operations

# Basic drawing operations
RECT(20, 20, 40, 20, 64)      # Rectangle at (20,20), 40x20, gray=64
SLEEP(30)                     # Wait 30ms
RECT(80, 20, 40, 20, 160)     # Another rectangle, lighter gray
SLEEP(30)
RECT(80, 60, 40, 20, 220)     # Third rectangle, even lighter

# Analog hardware control
DAC_WRITE(1, 150)             # Write 150 to DAC channel 1
SLEEP(50)
DAC_WRITE(2, 200)             # Write 200 to DAC channel 2

# Frame commit
COMMIT()

# Try editing in any pane and watch the others update!
# Digital source (Pane 1) ↔ Analog mirror (Pane 2) ↔ CSV (Pane 5)'''
        
        # Example analog source (native PXOS)
        analog_example = '''# Native PXOS analog programming
# Advanced analog operations not directly available in digital

# Signal processing chain
FILTER(lowpass, 1000, 0, 1)   # Low-pass filter 1kHz, ch0 → ch1
INTEGRATE(0.1, 1, 2)          # Integrator τ=0.1s, ch1 → ch2
DAC_WRITE(2, 128)             # Output integrated signal

# Sync and timing
SYNC_ROW(1)                   # Synchronization marker
SLEEP(100)                    # Wait 100ms

# Visual feedback
RECT(10, 100, 50, 10, 180)    # Status indicator
COMMIT()'''
        
        # Load digital source
        self.digital_source_text.delete('1.0', tk.END)
        self.digital_source_text.insert('1.0', digital_example)
        
        # Load analog source
        self.analog_source_text.delete('1.0', tk.END)
        self.analog_source_text.insert('1.0', analog_example)
        
        # Update all panes from digital source
        self.update_from_digital_source()
    
    def on_digital_source_change(self, event=None):
        """Handle changes in digital source (Pane 1)"""
        if self.last_edited == 'digital':
            return
        self.after(500, lambda: self.update_from_digital_source())
    
    def on_analog_mirror_change(self, event=None):
        """Handle changes in analog mirror (Pane 2)"""
        if self.last_edited == 'analog_mirror':
            return
        self.after(500, lambda: self.update_from_analog_mirror())
    
    def on_analog_source_change(self, event=None):
        """Handle changes in analog source editor (Pane 3)"""
        if self.last_edited == 'analog_source':
            return
        self.after(500, lambda: self.update_from_analog_source())
    
    def on_csv_change(self, event=None):
        """Handle changes in CSV (Pane 5)"""
        if self.last_edited == 'csv':
            return
        self.after(200, lambda: self.update_from_csv())
    
    def update_from_digital_source(self):
        """Update all panes when digital source changes"""
        try:
            self.last_edited = 'digital'
            
            # Get digital source
            digital_source = self.digital_source_text.get('1.0', tk.END)
            
            # Simple parsing - extract function calls and convert to PXOS
            self.pxos_schema = PXOSSchema()
            
            for line in digital_source.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Simple regex to extract function calls
                    import re
                    match = re.match(r'(\w+)\((.*)\)', line)
                    if match:
                        func_name = match.group(1).upper()
                        args_str = match.group(2)
                        
                        if func_name == 'RECT' and args_str:
                            args = [int(x.strip()) for x in args_str.split(',') if x.strip().isdigit()]
                            if len(args) >= 5:
                                gray = args[4] if len(args) == 5 else args[5]  # Handle both gray and RGB
                                self.pxos_schema.add_op("RECT", x=args[0], y=args[1], w=args[2], h=args[3], 
                                                      r=gray, g=gray, b=gray)
                        elif func_name == 'SLEEP' and args_str:
                            ms = int(args_str.strip())
                            self.pxos_schema.add_op("SLEEP", ms=ms)
                        elif func_name == 'DAC_WRITE' and args_str:
                            args = [int(x.strip()) for x in args_str.split(',') if x.strip().isdigit()]
                            if len(args) >= 2:
                                self.pxos_schema.add_op("DAC_WRITE", ch=args[0], val=args[1])
                        elif func_name == 'COMMIT':
                            self.pxos_schema.add_op("COMMIT")
            
            # Update analog mirror (Pane 2)
            analog_text = self.pxos_schema.to_analog_text()
            self.analog_mirror_text.delete('1.0', tk.END)
            self.analog_mirror_text.insert('1.0', analog_text)
            
            # Update CSV (Pane 5)
            csv_text = self.pxos_schema.to_csv()
            self.csv_text.delete('1.0', tk.END)
            self.csv_text.insert('1.0', csv_text)
            
            # Update tiles and results
            self.update_tiles_and_results()
            
            self.status_var.set(f"Updated from digital source - {len(self.pxos_schema.ops)} operations")
            
        except Exception as e:
            self.status_var.set(f"Error in digital source: {str(e)}")
        finally:
            self.last_edited = None
    
    def update_from_analog_mirror(self):
        """Update other panes when analog mirror changes"""
        try:
            self.last_edited = 'analog_mirror'
            
            # Parse analog text
            analog_text = self.analog_mirror_text.get('1.0', tk.END)
            self.pxos_schema.from_analog_text(analog_text)
            
            # Update CSV (Pane 5)
            csv_text = self.pxos_schema.to_csv()
            self.csv_text.delete('1.0', tk.END)
            self.csv_text.insert('1.0', csv_text)
            
            # Update tiles and results
            self.update_tiles_and_results()
            
            self.status_var.set(f"Updated from analog mirror - {len(self.pxos_schema.ops)} operations")
            
        except Exception as e:
            self.status_var.set(f"Error in analog mirror: {str(e)}")
        finally:
            self.last_edited = None
    
    def update_from_analog_source(self):
        """Update other panes when analog source editor changes"""
        try:
            self.last_edited = 'analog_source'
            
            # For now, treat analog source as advanced PXOS text
            # In the future, this could be a more sophisticated analog DSL
            analog_source = self.analog_source_text.get('1.0', tk.END)
            
            # If it looks like CSV, parse as CSV
            if 'RECT,' in analog_source or 'DAC_WRITE,' in analog_source:
                self.pxos_schema.from_csv(analog_source)
            else:
                # Otherwise parse as analog text
                self.pxos_schema.from_analog_text(analog_source)
            
            # Update analog mirror (Pane 2)
            analog_text = self.pxos_schema.to_analog_text()
            self.analog_mirror_text.delete('1.0', tk.END)
            self.analog_mirror_text.insert('1.0', analog_text)
            
            # Update CSV (Pane 5)
            csv_text = self.pxos_schema.to_csv()
            self.csv_text.delete('1.0', tk.END)
            self.csv_text.insert('1.0', csv_text)
            
            # Update tiles and results
            self.update_tiles_and_results()
            
            self.status_var.set(f"Updated from analog source - {len(self.pxos_schema.ops)} operations")
            
        except Exception as e:
            self.status_var.set(f"Error in analog source: {str(e)}")
        finally:
            self.last_edited = None
    
    def update_from_csv(self):
        """Update other panes when CSV changes"""
        try:
            self.last_edited = 'csv'
            
            # Parse CSV
            csv_text = self.csv_text.get('1.0', tk.END)
            self.pxos_schema.from_csv(csv_text)
            
            # Update analog mirror (Pane 2)
            analog_text = self.pxos_schema.to_analog_text()
            self.analog_mirror_text.delete('1.0', tk.END)
            self.analog_mirror_text.insert('1.0', analog_text)
            
            # Update tiles and results
            self.update_tiles_and_results()
            
            self.status_var.set(f"Updated from CSV - {len(self.pxos_schema.ops)} operations")
            
        except Exception as e:
            self.status_var.set(f"Error in CSV: {str(e)}")
        finally:
            self.last_edited = None
    
    def update_tiles_and_results(self):
        """Update tiles (Pane 4) and results (Pane 6) from current PXOS schema"""
        try:
            # Convert PXOS ops to operations for tile rendering
            operations = []
            
            for op in self.pxos_schema.ops:
                op_type = op["op"]
                
                if op_type == "RECT":
                    # Map to opcode for tile rendering
                    opcode = 1  # RECT opcode
                    operand = op.get('r', 128)  # Use red channel as operand
                    operations.append((opcode, operand))
                elif op_type == "SLEEP":
                    operations.append((3, op['ms'] & 0xFF))  # SLEEP opcode
                elif op_type == "DAC_WRITE":
                    operations.append((5, dac_pack(op['ch'], op['val'])))  # DAC_WRITE opcode
                elif op_type == "SYNC_ROW":
                    operations.append((4, op['i']))  # SYNC_ROW opcode
                elif op_type == "COMMIT":
                    operations.append((2, 0))  # COMMIT opcode
            
            # Update tiles visualization
            self.update_tiles_display(operations)
            
            # Update results visualization
            self.update_results_display()
            
        except Exception as e:
            self.show_tiles_message(f"Tiles error: {str(e)}")
    
    def update_tiles_display(self, operations):
        """Update the tiles visualization in Pane 4"""
        try:
            if PIL_AVAILABLE and operations:
                tile_sheet = create_tile_sheet(operations, cols=self.pxos_schema.metadata.get('cols', 8))
                if tile_sheet:
                    # Clear existing content
                    for widget in self.tiles_frame.winfo_children():
                        widget.destroy()
                    
                    # Display new tile sheet
                    self.tile_photo = ImageTk.PhotoImage(tile_sheet)
                    tile_label = Label(self.tiles_frame, image=self.tile_photo, bg='white')
                    tile_label.pack(expand=True)
                else:
                    self.show_tiles_message("No valid tiles generated")
            else:
                self.show_tiles_message("Pillow not available" if not PIL_AVAILABLE else "No operations to visualize")
        
        except Exception as e:
            self.show_tiles_message(f"Tiles error: {str(e)}")
    
    def update_results_display(self):
        """Update the results visualization in Pane 6"""
        try:
            # Clear canvas
            self.result_canvas.delete('all')
            
            # Render PXOS operations
            y_offset = 10
            rect_count = 0
            
            for op in self.pxos_schema.ops:
                op_type = op["op"]
                
                if op_type == "RECT":
                    # Draw the rectangle
                    x, y, w, h = op['x'], op['y'], op['w'], op['h']
                    r, g, b = op.get('r', 128), op.get('g', 128), op.get('b', 128)
                    
                    # Scale down for display
                    scale = 0.8
                    x_scaled = int(x * scale)
                    y_scaled = int(y * scale)
                    w_scaled = int(w * scale)
                    h_scaled = int(h * scale)
                    
                    color = f"#{r:02x}{g:02x}{b:02x}"
                    self.result_canvas.create_rectangle(
                        x_scaled + 10, y_scaled + 10, 
                        x_scaled + w_scaled + 10, y_scaled + h_scaled + 10,
                        fill=color, outline=color
                    )
                    rect_count += 1
                
                elif op_type in ['SLEEP', 'DAC_WRITE', 'SYNC_ROW', 'COMMIT', 'FILTER', 'INTEGRATE']:
                    # Show operation as text
                    if op_type == "DAC_WRITE":
                        text = f"DAC_WRITE ch={op['ch']} val={op['val']}"
                    elif op_type == "FILTER":
                        text = f"FILTER {op['type']} {op['fc']}Hz"
                    elif op_type == "INTEGRATE":
                        text = f"INTEGRATE τ={op['tau']}ms"
                    else:
                        text = f"{op_type}"
                    
                    self.result_canvas.create_text(
                        10, y_offset, anchor='nw', text=text, 
                        fill='yellow', font=('Courier', 8)
                    )
                    y_offset += 15
            
            # Show summary
            summary = f"Rendered: {rect_count} rectangles, {len(self.pxos_schema.ops)} total ops"
            self.result_canvas.create_text(
                10, self.result_canvas.winfo_height() - 20, 
                anchor='nw', text=summary, fill='green', font=('Courier', 7)
            )
            
        except Exception as e:
            self.result_canvas.create_text(
                10, 10, anchor='nw', text=f"Render error: {str(e)}", 
                fill='red', font=('Courier', 8)
            )
    
    def show_tiles_message(self, message):
        """Show a message in the tiles pane"""
        for widget in self.tiles_frame.winfo_children():
            widget.destroy()
        
        Label(self.tiles_frame, text=message, bg='white').pack(expand=True)
    

    
    def run_viewer(self):
        """Environment-configurable viewer runner with 6-pane integration"""
        try:
            # Import viewer adapter
            import viewer_adapter_simple as VA
            VA.reset()
            
            # Get module and function names from environment or use defaults
            module_name = os.getenv("ACW_VIEWER_MODULE", "your_viewer_main")
            func_name = os.getenv("ACW_VIEWER_FUNC", "main")
            
            try:
                # Dynamic import
                mod = importlib.import_module(module_name)
                func = getattr(mod, func_name)
                
                # Execute viewer function
                func()  # viewer emits ops via viewer_adapter.*
                
            except (ImportError, AttributeError) as e:
                error_msg = f"# ERROR: failed to run viewer '{module_name}.{func_name}'\n" + traceback.format_exc()
                self.csv_text.delete('1.0', tk.END)
                self.csv_text.insert(tk.END, error_msg)
                self.status_var.set(f"Error: {str(e)}")
                return
            
            # Get captured operations
            csv_text = VA.get_captured_csv()
            
            if not csv_text:
                self.status_var.set("Warning: No operations captured from viewer")
                return
            
            # Parse captured CSV into PXOS schema
            self.pxos_schema.from_csv(csv_text)
            
            # Update all panes
            self.last_edited = 'viewer'
            
            # Update CSV (Pane 5)
            self.csv_text.delete('1.0', tk.END)
            self.csv_text.insert(tk.END, csv_text)
            
            # Update analog mirror (Pane 2)
            analog_text = self.pxos_schema.to_analog_text()
            self.analog_mirror_text.delete('1.0', tk.END)
            self.analog_mirror_text.insert(tk.END, analog_text)
            
            # Update tiles and results
            self.update_tiles_and_results()
            
            # Optional: mirror source into Pane 1 ("tracer mode")
            try:
                # Try to get source code of the executed function
                import inspect, pathlib
                src = inspect.getsource(func)
            except Exception:
                try:
                    # Fallback: read the entire module file
                    if hasattr(mod, '__file__') and mod.__file__:
                        src = pathlib.Path(mod.__file__).read_text(encoding="utf-8")
                    else:
                        src = "# Source unavailable - module loaded dynamically"
                except Exception:
                    src = f"# Source for '{module_name}.{func_name}' unavailable"
            
            # Update Pane 1 with captured source
            self.digital_source_text.delete('1.0', tk.END)
            self.digital_source_text.insert(tk.END, f"# Captured from {module_name}.{func_name}\n# Env vars: ACW_VIEWER_MODULE, ACW_VIEWER_FUNC\n\n{src}")
            
            self.last_edited = None
            
            self.status_var.set(f"Viewer captured: {VA.get_ops_count()} operations from {module_name}.{func_name}")
            
        except Exception as e:
            error_msg = f"# ERROR: failed to run viewer\n{traceback.format_exc()}"
            self.csv_text.delete('1.0', tk.END)
            self.csv_text.insert(tk.END, error_msg)
            self.status_var.set(f"Error: {str(e)}")
    
# Helper function for DAC packing (from PXOS schema)
def dac_pack(ch, val):
    """Pack DAC channel and value into single operand"""
    return ((ch & 0x7) << 5) | ((val >> 3) & 0x1F)


if __name__ == "__main__":
    app = SimpleWorkbench()
    app.mainloop()