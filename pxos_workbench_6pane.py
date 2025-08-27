#!/usr/bin/env python3
"""
PXOS 6-Pane Workbench - Complete Round-Trip Translator
Implements bulletproof data flow with event bus architecture
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from PIL import Image, ImageDraw, ImageTk
import json
import re
import time
import traceback
import importlib
import os
import sys

# Import components
sys.path.append(os.path.dirname(__file__))
from pxos_sync_engine_enhanced import (
    PXOSEngine, Transforms, Profile, TextPaneAdapter, TilesPane, ReplayPane,
    ValidationError, PinnedError
)
from pxos_validator import PXOSValidator
import asyncio

class PXOSWorkbench6Pane(tk.Tk):
    """Complete 6-pane PXOS workbench with bulletproof data flow"""
    
    def __init__(self):
        super().__init__()
        
        self.title("PXOS 6-Pane Workbench - Round-Trip Translator")
        self.geometry("1800x1000")
        self.configure(bg='#2d2d30')
        
        # Initialize enhanced sync engine
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.validator = PXOSValidator()
        self.engine = None  # Will be setup in setup_engine()
        self.setup_engine()
        
        # UI components
        self.panes = {}
        self.status_bar = None
        
        self.setup_ui()
        self.load_sample_program()
    
    def setup_engine(self):
        """Configure enhanced PXOS engine with transforms and validators"""
        
        # Create transforms
        tr = Transforms()
        
        def T_py_to_hlir(python_code: str) -> dict:
            """Enhanced Python to HLIR conversion with better parsing"""
            import ast
            try:
                tree = ast.parse(python_code)
                operations = []
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                        if node.func.attr == 'RECT' and len(node.args) >= 5:
                            args = [ast.literal_eval(arg) for arg in node.args]
                            operations.append({
                                'op': 'RECT',
                                'x': args[0], 'y': args[1], 'w': args[2], 'h': args[3],
                                'r': args[4], 'g': args[4], 'b': args[4]
                            })
                        elif node.func.attr == 'SLEEP' and len(node.args) >= 1:
                            operations.append({
                                'op': 'SLEEP',
                                'ms': ast.literal_eval(node.args[0])
                            })
                        elif node.func.attr == 'COMMIT':
                            operations.append({'op': 'COMMIT'})
                        elif node.func.attr == 'DAC_WRITE' and len(node.args) >= 2:
                            operations.append({
                                'op': 'DAC_WRITE',
                                'ch': ast.literal_eval(node.args[0]),
                                'val': ast.literal_eval(node.args[1])
                            })
                        elif node.func.attr == 'INTEGRATE' and len(node.args) >= 3:
                            operations.append({
                                'op': 'INTEGRATE',
                                'tau': ast.literal_eval(node.args[0]),
                                'src': ast.literal_eval(node.args[1]),
                                'dst': ast.literal_eval(node.args[2])
                            })
                        elif node.func.attr == 'FILTER' and len(node.args) >= 4:
                            operations.append({
                                'op': 'FILTER',
                                'type': ast.literal_eval(node.args[0]),
                                'fc': ast.literal_eval(node.args[1]),
                                'src': ast.literal_eval(node.args[2]),
                                'dst': ast.literal_eval(node.args[3])
                            })
                
                return {
                    'schemaVersion': 'pxos-ops/1.0',
                    'meta': {'profile': 'default', 'cols': 16},
                    'program': operations
                }
            except Exception as e:
                raise ValidationError(f"Python parsing error: {str(e)}")
        
        def T_hlir_to_analog(hlir: dict) -> str:
            """Enhanced HLIR to analog DSL conversion"""
            lines = ["# PXOS Analog Program", ""]
            for op in hlir.get('program', []):
                op_type = op.get('op', '').upper()
                
                if op_type == 'RECT':
                    lines.append(f"draw_rectangle({op.get('x', 0)}, {op.get('y', 0)}, {op.get('w', 0)}, {op.get('h', 0)})")
                    lines.append(f"  ├─ color: rgb({op.get('r', 128)}, {op.get('g', 128)}, {op.get('b', 128)})")
                elif op_type == 'SLEEP':
                    lines.append(f"wait({op.get('ms', 0)}ms)")
                elif op_type == 'DAC_WRITE':
                    voltage = op.get('val', 0) * 5.0 / 255
                    lines.append(f"analog_output(channel_{op.get('ch', 0)}, {voltage:.2f}V)")
                elif op_type == 'FILTER':
                    lines.append(f"analog_filter({op.get('type', 'lowpass')}, {op.get('fc', 1000)}Hz)")
                    lines.append(f"  ├─ input: channel_{op.get('src', 0)}")
                    lines.append(f"  └─ output: channel_{op.get('dst', 1)}")
                elif op_type == 'INTEGRATE':
                    lines.append(f"analog_integrator(τ={op.get('tau', 0.1)}ms)")
                    lines.append(f"  ├─ input: channel_{op.get('src', 0)}")
                    lines.append(f"  └─ output: channel_{op.get('dst', 1)}")
                elif op_type == 'COMMIT':
                    lines.append("commit_frame()")
                    lines.append("")
            return '\n'.join(lines)
        
        def T_analog_to_hlir(analog: str) -> dict:
            """Enhanced analog DSL to HLIR conversion"""
            operations = []
            for line in analog.split('\n'):
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('├') or line.startswith('└'):
                    continue
                
                # Enhanced parsing for analog DSL
                if line.startswith('draw_rectangle('):
                    match = re.search(r'draw_rectangle\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)', line)
                    if match:
                        x, y, w, h = map(int, match.groups())
                        operations.append({
                            'op': 'RECT', 'x': x, 'y': y, 'w': w, 'h': h,
                            'r': 128, 'g': 128, 'b': 128
                        })
                elif line.startswith('wait('):
                    match = re.search(r'wait\((\d+)ms\)', line)
                    if match:
                        operations.append({'op': 'SLEEP', 'ms': int(match.group(1))})
                elif line.startswith('analog_output('):
                    match = re.search(r'analog_output\(channel_(\d+),\s*([\d.]+)V\)', line)
                    if match:
                        ch = int(match.group(1))
                        voltage = float(match.group(2))
                        val = int(voltage * 255 / 5.0)
                        operations.append({'op': 'DAC_WRITE', 'ch': ch, 'val': val})
                elif line.startswith('analog_filter('):
                    match = re.search(r'analog_filter\(([^,]+),\s*(\d+)Hz\)', line)
                    if match:
                        filter_type, fc = match.groups()
                        operations.append({
                            'op': 'FILTER', 'type': filter_type, 'fc': int(fc),
                            'src': 0, 'dst': 1  # Default - could be enhanced
                        })
                elif line.startswith('analog_integrator('):
                    match = re.search(r'analog_integrator\(τ=([\d.]+)ms\)', line)
                    if match:
                        tau = float(match.group(1))
                        operations.append({
                            'op': 'INTEGRATE', 'tau': tau, 'src': 0, 'dst': 1
                        })
                elif line.startswith('commit_frame'):
                    operations.append({'op': 'COMMIT'})
            
            return {
                'schemaVersion': 'pxos-ops/1.0',
                'meta': {'profile': 'default', 'cols': 16},
                'program': operations
            }
        
        def validate_hlir(hlir: dict) -> None:
            """Enhanced HLIR validation"""
            try:
                is_valid, errors = self.validator.validate_json(hlir)
                if not is_valid:
                    raise ValidationError(f"Schema validation failed: {'; '.join(errors)}")
            except Exception as e:
                raise ValidationError(f"HLIR validation error: {str(e)}")
        
        def lower_hlir_to_llir(hlir: dict) -> list:
            """Lower HLIR to LLIR operations"""
            llir = []
            for op in hlir.get('program', []):
                op_type = op.get('op', '').upper()
                if op_type == 'RECT':
                    llir.extend([
                        ('SET_GRAY', op.get('r', 128)),
                        ('MOVE_X', op.get('x', 0)),
                        ('MOVE_Y', op.get('y', 0)),
                        ('SET_W', op.get('w', 0)),
                        ('SET_H', op.get('h', 0)),
                        ('DRAW_RECT', 0)
                    ])
                elif op_type == 'SLEEP':
                    llir.append(('SLEEP', op.get('ms', 0)))
                elif op_type == 'DAC_WRITE':
                    llir.append(('DAC_WRITE', (op.get('ch', 0) << 8) | op.get('val', 0)))
                elif op_type == 'COMMIT':
                    llir.append(('COMMIT', 0))
            return llir
        
        def encode_tiles(llir: list, ecc_mode: str) -> list:
            """Encode LLIR to tiles with ECC"""
            tiles = []
            for op_name, operand in llir:
                # Simple encoding - could be enhanced with real ECC
                op_code = {'SET_GRAY': 1, 'MOVE_X': 2, 'MOVE_Y': 3, 'SET_W': 4, 
                          'SET_H': 5, 'DRAW_RECT': 6, 'SLEEP': 8, 'DAC_WRITE': 10, 
                          'COMMIT': 7}.get(op_name, 0)
                tiles.append((op_code, operand, f"{op_code:04b}{operand:08b}"))
            return tiles
        
        def ecc_stats(tiles: list) -> dict:
            """Generate ECC statistics"""
            return {'ok': len(tiles), 'corrected': 0, 'bad': 0}
        
        # Assign transforms
        tr.T_py_to_hlir = T_py_to_hlir
        tr.T_analog_to_hlir = T_analog_to_hlir
        tr.T_hlir_to_analog = T_hlir_to_analog
        tr.validate_hlir = validate_hlir
        tr.lower_hlir_to_llir = lower_hlir_to_llir
        tr.encode_tiles = encode_tiles
        tr.ecc_stats = ecc_stats
        
        # Create engine
        profile = Profile(ecc="hamming16_12")
        self.engine = PXOSEngine(tr, profile, loop=self.loop)
    
    def setup_ui(self):
        """Create the 6-pane UI layout"""
        
        # Create main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Top row: P1, P2, P3
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill='both', expand=True)
        
        # P1: Python Source
        p1_frame = ttk.LabelFrame(top_frame, text="P1: Python Source", padding=5)
        p1_frame.pack(side='left', fill='both', expand=True, padx=2)
        
        self.panes['P1'] = self.create_text_pane(p1_frame, 'P1')
        
        # P2: Analog Mirror
        p2_frame = ttk.LabelFrame(top_frame, text="P2: Analog Mirror", padding=5)
        p2_frame.pack(side='left', fill='both', expand=True, padx=2)
        
        self.panes['P2'] = self.create_text_pane(p2_frame, 'P2')
        
        # P3: Analog Editor
        p3_frame = ttk.LabelFrame(top_frame, text="P3: Analog Editor", padding=5)
        p3_frame.pack(side='left', fill='both', expand=True, padx=2)
        
        self.panes['P3'] = self.create_text_pane(p3_frame, 'P3')
        
        # Bottom row: P4, P5, P6
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill='both', expand=True)
        
        # P4: Tiles
        p4_frame = ttk.LabelFrame(bottom_frame, text="P4: Tile Sheet", padding=5)
        p4_frame.pack(side='left', fill='both', expand=True, padx=2)
        
        self.panes['P4'] = self.create_tile_pane(p4_frame)
        
        # P5: HLIR
        p5_frame = ttk.LabelFrame(bottom_frame, text="P5: HLIR (CSV/JSON)", padding=5)
        p5_frame.pack(side='left', fill='both', expand=True, padx=2)
        
        self.panes['P5'] = self.create_text_pane(p5_frame, 'P5')
        
        # P6: Replay
        p6_frame = ttk.LabelFrame(bottom_frame, text="P6: Live Replay", padding=5)
        p6_frame.pack(side='left', fill='both', expand=True, padx=2)
        
        self.panes['P6'] = self.create_replay_pane(p6_frame)
        
        # Control panel
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill='x', pady=5)
        
        ttk.Button(control_frame, text="Run Viewer", command=self.run_viewer).pack(side='left', padx=5)
        ttk.Button(control_frame, text="Force Rebuild", command=self.engine.force_rebuild).pack(side='left', padx=5)
        ttk.Button(control_frame, text="Reset", command=self.engine.reset).pack(side='left', padx=5)
        
        # Status bar
        self.status_bar = ttk.Label(main_frame, text="Ready", relief='sunken', font=('Arial', 8))
        self.status_bar.pack(fill='x', pady=2)
        
        # Register adapters with engine
        self.engine.register(self.panes['P1']['adapter'])
        self.engine.register(self.panes['P2']['adapter'])
        self.engine.register(self.panes['P3']['adapter'])
        self.engine.register(self.panes['P5']['adapter'])
        
        # Register visual panes
        if 'P4' in self.panes:
            self.engine.register(self.panes['P4']['adapter'])
        if 'P6' in self.panes:
            self.engine.register(self.panes['P6']['adapter'])
    
    def create_text_pane(self, parent, pane_id):
        """Create a text editing pane with enhanced adapter"""
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True)
        
        # Header with pin button
        header = ttk.Frame(frame)
        header.pack(fill='x', pady=2)
        
        pin_var = tk.BooleanVar()
        pin_btn = ttk.Checkbutton(header, text="📌 Pin", variable=pin_var)
        pin_btn.pack(side='right')
        
        truth_label = ttk.Label(header, text="", foreground='green', font=('Arial', 8))
        truth_label.pack(side='right', padx=10)
        
        # Text widget
        text_widget = scrolledtext.ScrolledText(
            frame, 
            width=40, 
            height=20,
            font=('Consolas', 9),
            bg='#1e1e1e' if pane_id == 'P1' else '#2d2d30',
            fg='#dcdcdc',
            insertbackground='white'
        )
        text_widget.pack(fill='both', expand=True)
        
        # Status
        status_label = ttk.Label(frame, text="Ready", font=('Arial', 8))
        status_label.pack(fill='x')
        
        # Create adapter functions
        def get_fn():
            return text_widget.get('1.0', tk.END).rstrip()
        
        def set_fn(text, origin, build_id):
            # Save cursor position
            try:
                cursor_pos = text_widget.index(tk.INSERT)
            except:
                cursor_pos = '1.0'
            
            # Update content
            text_widget.delete('1.0', tk.END)
            text_widget.insert('1.0', text)
            
            # Restore cursor
            try:
                text_widget.mark_set(tk.INSERT, cursor_pos)
                text_widget.see(cursor_pos)
            except:
                pass
            
            status_label.config(text=f"Updated from {origin} (build {build_id})")
        
        def annotate_fn(message, severity):
            # Clear existing content and show error
            current = text_widget.get('1.0', tk.END)
            if not current.startswith('#'):
                text_widget.insert('1.0', f"# {severity.upper()}: {message}\n")
            text_widget.tag_add(severity, '1.0', '2.0')
            text_widget.tag_config(severity, foreground='red' if severity == "error" else 'orange')
            status_label.config(text=f"{severity.upper()}: {message}")
        
        def clear_fn():
            # Remove error tags
            text_widget.tag_remove("error", '1.0', tk.END)
            text_widget.tag_remove("warn", '1.0', tk.END)
            status_label.config(text="Ready")
        
        def splice_fn(i0, i1, insert_text, origin, build_id):
            # Advanced splice operation for minimal edits
            old_text = text_widget.get('1.0', tk.END).rstrip()
            new_text = old_text[:i0] + insert_text + old_text[i1:]
            
            # Convert to tkinter indices
            lines_before = old_text[:i0].count('\n')
            col_offset = len(old_text[:i0].split('\n')[-1])
            start_pos = f"{lines_before + 1}.{col_offset}"
            
            lines_in_range = old_text[i0:i1].count('\n')
            if lines_in_range > 0:
                end_pos = f"{lines_before + lines_in_range + 1}.0"
            else:
                end_pos = f"{lines_before + 1}.{col_offset + (i1 - i0)}"
            
            # Apply splice
            text_widget.delete(start_pos, end_pos)
            text_widget.insert(start_pos, insert_text)
            
            status_label.config(text=f"Spliced from {origin} (build {build_id})")
        
        # Create adapter
        adapter = TextPaneAdapter(pane_id, get_fn, set_fn, annotate_fn, clear_fn, splice_fn)
        
        # Pin button callback
        def toggle_pin():
            adapter.pinned = pin_var.get()
            text_widget.configure(background='lightyellow' if adapter.pinned else 
                                 ('#1e1e1e' if pane_id == 'P1' else '#2d2d30'))
        
        pin_btn.configure(command=toggle_pin)
        
        # Bind edit events for editable panes
        if pane_id in ['P1', 'P2', 'P3', 'P5']:
            def on_text_edit(event):
                # Use asyncio-safe scheduling
                self.loop.call_soon_threadsafe(lambda: self.engine.on_edit(pane_id))
            
            text_widget.bind('<KeyRelease>', on_text_edit)
            text_widget.bind('<FocusIn>', lambda e: self.update_truth_indicator(pane_id, truth_label))
        
        return {
            'type': 'text',
            'adapter': adapter,
            'widget': text_widget,
            'truth_label': truth_label,
            'status_label': status_label,
            'pin_var': pin_var
        }
    
    def create_tile_pane(self, parent):
        """Create tile visualization pane with adapter"""
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(frame, width=400, height=250, bg='white')
        canvas.pack(fill='both', expand=True, pady=2)
        
        status_label = ttk.Label(frame, text="Ready", font=('Arial', 8))
        status_label.pack(fill='x')
        
        # Enhanced tile adapter
        class TilesPaneAdapter:
            def __init__(self):
                self.id = 'P4'
                self.pinned = False
                self._last_build_id = -1
                self.photo = None
            
            def read(self):
                return ""  # Tiles are visual only
            
            def write(self, text, *, origin, build_id):
                pass  # Not applicable for visual panes
            
            def annotate(self, message, *, severity="error"):
                canvas.delete('all')
                canvas.create_text(200, 125, text=f"{severity.upper()}: {message}", 
                                 fill='red' if severity == 'error' else 'orange',
                                 font=('Arial', 10), justify='center')
            
            def clear_diagnostics(self):
                pass  # Visual panes don't have persistent diagnostics
            
            def render_tiles(self, tiles, ecc_report, *, origin, build_id):
                if build_id == self._last_build_id and origin == self.id:
                    return  # Echo guard
                self._last_build_id = build_id
                
                canvas.delete('all')
                
                try:
                    # Enhanced tile rendering
                    tile_size = 24
                    cols = 8
                    
                    for i, (op_code, operand, bits) in enumerate(tiles):
                        row = i // cols
                        col = i % cols
                        x = 10 + col * (tile_size + 2)
                        y = 10 + row * (tile_size + 2)
                        
                        # Draw tile background
                        canvas.create_rectangle(x, y, x + tile_size, y + tile_size, 
                                              fill='lightgray', outline='black')
                        
                        # Draw operation representation
                        if op_code == 1:  # SET_GRAY
                            gray = min(255, operand)
                            color = f"#{gray:02x}{gray:02x}{gray:02x}"
                            canvas.create_rectangle(x + 2, y + 2, x + tile_size - 2, y + tile_size - 2,
                                                  fill=color, outline='white')
                        elif op_code == 6:  # DRAW_RECT
                            canvas.create_rectangle(x + 4, y + 4, x + tile_size - 4, y + tile_size - 4,
                                                  fill='blue', outline='white')
                        elif op_code == 7:  # COMMIT
                            canvas.create_oval(x + 4, y + 4, x + tile_size - 4, y + tile_size - 4,
                                             fill='green', outline='white')
                        elif op_code == 8:  # SLEEP
                            canvas.create_text(x + tile_size//2, y + tile_size//2, text="Z", 
                                             font=('Arial', 8), fill='purple')
                        elif op_code == 10:  # DAC_WRITE
                            canvas.create_text(x + tile_size//2, y + tile_size//2, text="D", 
                                             font=('Arial', 8), fill='red')
                        else:
                            canvas.create_text(x + tile_size//2, y + tile_size//2, text=str(op_code), 
                                             font=('Arial', 6))
                        
                        # Add index
                        canvas.create_text(x + 1, y + 1, text=str(i), font=('Arial', 6), 
                                         fill='blue', anchor='nw')
                    
                    # Show ECC statistics
                    stats_text = f"Tiles: {len(tiles)} | OK: {ecc_report.get('ok', 0)} | Corrected: {ecc_report.get('corrected', 0)} | Bad: {ecc_report.get('bad', 0)}"
                    status_label.config(text=stats_text)
                    
                except Exception as e:
                    canvas.create_text(200, 125, text=f"Tile error: {str(e)}", 
                                     fill='red', font=('Arial', 10), justify='center')
        
        adapter = TilesPaneAdapter()
        
        return {
            'type': 'tiles',
            'adapter': adapter,
            'canvas': canvas,
            'status_label': status_label
        }
    
    def create_replay_pane(self, parent):
        """Create replay visualization pane with adapter"""
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(frame, width=400, height=200, bg='black')
        canvas.pack(fill='both', expand=True, pady=2)
        
        log_text = tk.Text(frame, height=3, font=('Consolas', 8), bg='#1e1e1e', fg='#dcdcdc')
        log_text.pack(fill='x')
        
        # Enhanced replay adapter
        class ReplayPaneAdapter:
            def __init__(self):
                self.id = 'P6'
                self.pinned = False
                self._last_build_id = -1
                self.log_lines = []
            
            def read(self):
                return ""  # Replay is visual only
            
            def write(self, text, *, origin, build_id):
                pass  # Not applicable for visual panes
            
            def annotate(self, message, *, severity="error"):
                self.log(f"{severity.upper()}: {message}")
            
            def clear_diagnostics(self):
                pass  # Visual panes don't have persistent diagnostics
            
            def replay_from_hlir(self, hlir, *, origin, build_id):
                if build_id == self._last_build_id and origin == self.id:
                    return  # Echo guard
                self._last_build_id = build_id
                
                canvas.delete('all')
                
                try:
                    # Enhanced replay visualization
                    self.log(f"Replay build {build_id}: {len(hlir.get('program', []))} ops")
                    
                    for i, op in enumerate(hlir.get('program', [])):
                        op_type = op.get('op', 'UNKNOWN')
                        
                        if op_type == 'RECT':
                            x = op.get('x', 0) + 10
                            y = op.get('y', 0) + 10
                            w = op.get('w', 10)
                            h = op.get('h', 10)
                            r, g, b = op.get('r', 128), op.get('g', 128), op.get('b', 128)
                            color = f"#{r:02x}{g:02x}{b:02x}"
                            
                            canvas.create_rectangle(x, y, x + w, y + h, fill=color, outline='white')
                            self.log(f"  RECT({x},{y},{w},{h}) {color}")
                        
                        elif op_type == 'SLEEP':
                            ms = op.get('ms', 0)
                            # Draw timeline marker
                            x_pos = 10 + (i * 20)
                            canvas.create_line(x_pos, 180, x_pos + 15, 180, fill='yellow', width=2)
                            canvas.create_text(x_pos + 7, 190, text=f"{ms}ms", fill='yellow', font=('Arial', 6))
                            self.log(f"  SLEEP {ms}ms")
                        
                        elif op_type == 'DAC_WRITE':
                            ch, val = op.get('ch', 0), op.get('val', 0)
                            # Draw DAC output visualization
                            x_pos = 300 + (ch * 15)
                            bar_height = int(val * 150 / 255)
                            canvas.create_rectangle(x_pos, 150 - bar_height, x_pos + 10, 150, 
                                                  fill='red', outline='white')
                            canvas.create_text(x_pos + 5, 160, text=f"D{ch}", fill='white', font=('Arial', 6))
                            self.log(f"  DAC_WRITE ch={ch} val={val}")
                        
                        elif op_type == 'INTEGRATE':
                            tau, src, dst = op.get('tau', 0.1), op.get('src', 0), op.get('dst', 1)
                            # Draw integrator visualization
                            x_start = 50 + (src * 30)
                            x_end = 50 + (dst * 30)
                            canvas.create_oval(x_start, 50, x_start + 20, 70, fill='cyan', outline='white')
                            canvas.create_line(x_start + 20, 60, x_end, 60, fill='cyan', width=2, arrow=tk.LAST)
                            canvas.create_text(x_start + 10, 40, text=f"τ={tau}", fill='white', font=('Arial', 6))
                            self.log(f"  INTEGRATE τ={tau} {src}→{dst}")
                        
                        elif op_type == 'FILTER':
                            filter_type, fc = op.get('type', 'lowpass'), op.get('fc', 1000)
                            src, dst = op.get('src', 0), op.get('dst', 1)
                            # Draw filter visualization
                            x_start = 50 + (src * 30)
                            x_end = 50 + (dst * 30)
                            canvas.create_polygon(x_start, 80, x_start + 15, 70, x_start + 15, 90, 
                                                fill='magenta', outline='white')
                            canvas.create_line(x_start + 15, 80, x_end, 80, fill='magenta', width=2, arrow=tk.LAST)
                            canvas.create_text(x_start + 7, 100, text=f"{fc}Hz", fill='white', font=('Arial', 6))
                            self.log(f"  FILTER {filter_type} fc={fc}Hz {src}→{dst}")
                        
                        elif op_type == 'COMMIT':
                            # Draw commit line
                            canvas.create_line(0, 180, 400, 180, fill='green', width=3)
                            canvas.create_text(200, 175, text="COMMIT", fill='green', font=('Arial', 8, 'bold'))
                            self.log(f"  COMMIT")
                    
                except Exception as e:
                    canvas.create_text(200, 100, text=f"Replay error: {str(e)}", 
                                     fill='red', font=('Arial', 10), justify='center')
                    self.log(f"ERROR: {str(e)}")
            
            def log(self, line):
                """Add log line with auto-scrolling"""
                self.log_lines.append(line)
                log_text.insert(tk.END, f"{line}\n")
                log_text.see(tk.END)
                
                # Limit log size
                lines = int(log_text.index('end').split('.')[0])
                if lines > 50:
                    log_text.delete('1.0', '25.0')
        
        adapter = ReplayPaneAdapter()
        
        return {
            'type': 'replay',
            'adapter': adapter,
            'canvas': canvas,
            'log_text': log_text
        }
    
    def update_truth_indicator(self, pane_id, truth_label):
        """Update truth indicator for focused pane"""
        build_info = self.engine.get_build_info()
        if build_info['truth_origin'] == pane_id:
            truth_label.config(text="TRUTH", foreground='green')
        else:
            truth_label.config(text="", foreground='green')
    
    def update_status_bar(self):
        """Update main status bar with enhanced info"""
        build_info = self.engine.get_build_info()
        status_text = f"Build {build_info['build_id']} | Truth: {build_info['truth_origin'] or 'None'}"
        
        # Add cache info
        cache_stats = build_info['cache_stats']
        cached_panes = [k.split('_')[1] for k, v in cache_stats.items() if v and k.startswith('H_')]
        if cached_panes:
            status_text += f" | Cached: {','.join(cached_panes)}"
        
        if build_info['has_errors']:
            status_text += " | ERRORS"
            self.status_bar.config(foreground='red')
        else:
            self.status_bar.config(foreground='black')
        
        self.status_bar.config(text=status_text)
    
    def run_viewer(self):
        """Run viewer integration with enhanced engine"""
        try:
            import viewer_adapter_simple as VA
            VA.reset()
            
            module_name = os.getenv("ACW_VIEWER_MODULE", "demo_viewer_main") 
            func_name = os.getenv("ACW_VIEWER_FUNC", "main")
            
            mod = importlib.import_module(module_name)
            func = getattr(mod, func_name)
            func()
            
            csv_text = VA.get_captured_csv()
            if csv_text:
                # Convert CSV to HLIR
                hlir_lines = []
                for line in csv_text.splitlines():
                    if line.strip() and not line.startswith('#'):
                        hlir_lines.append(line)
                
                if hlir_lines:
                    # Update P5 with HLIR data
                    hlir_json = {
                        "schemaVersion": "pxos-ops/1.0",
                        "meta": {"profile": "default", "cols": 16},
                        "program": []
                    }
                    
                    for line in hlir_lines:
                        parts = line.split(',')
                        op_type = parts[0].upper()
                        
                        if op_type == 'RECT' and len(parts) >= 8:
                            hlir_json["program"].append({
                                "op": "RECT",
                                "x": int(parts[1]), "y": int(parts[2]),
                                "w": int(parts[3]), "h": int(parts[4]),
                                "r": int(parts[5]), "g": int(parts[6]), "b": int(parts[7])
                            })
                        elif op_type == 'SLEEP' and len(parts) >= 2:
                            hlir_json["program"].append({"op": "SLEEP", "ms": int(parts[1])})
                        elif op_type == 'COMMIT':
                            hlir_json["program"].append({"op": "COMMIT"})
                        elif op_type == 'DAC_WRITE' and len(parts) >= 3:
                            hlir_json["program"].append({"op": "DAC_WRITE", "ch": int(parts[1]), "val": int(parts[2])})
                    
                    # Write to P5 and trigger update
                    json_text = json.dumps(hlir_json, indent=2)
                    self.panes['P5']['adapter'].write(json_text, origin='viewer', build_id=0)
                    
                    # Trigger engine update
                    self.loop.call_soon_threadsafe(lambda: self.engine.on_edit('P5'))
                    
                    # Update P1 with source if available
                    try:
                        import inspect
                        src = inspect.getsource(func)
                        self.panes['P1']['widget'].delete('1.0', tk.END)
                        self.panes['P1']['widget'].insert('1.0', f"# From {module_name}.{func_name}\n\n{src}")
                    except:
                        pass
                    
                    messagebox.showinfo("Viewer", f"Captured {VA.get_ops_count()} operations")
                else:
                    messagebox.showwarning("Viewer", "No valid operations captured")
            else:
                messagebox.showwarning("Viewer", "No operations captured")
                
        except Exception as e:
            messagebox.showerror("Viewer Error", str(e))
            traceback.print_exc()
    
    def load_sample_program(self):
        """Load sample program for testing enhanced engine"""
        sample_python = """# Enhanced PXOS sample program
import viewer_adapter_simple as VA

def main():
    VA.RECT(20, 20, 40, 20, 128)
    VA.SLEEP(30)
    VA.RECT(70, 70, 30, 30, 200)
    VA.DAC_WRITE(1, 180)
    VA.INTEGRATE(0.1, 0, 1)
    VA.FILTER('lowpass', 1000, 1, 2)
    VA.COMMIT()
"""
        
        sample_hlir = {
            "schemaVersion": "pxos-ops/1.0",
            "meta": {"profile": "default", "cols": 16},
            "program": [
                {"op": "RECT", "x": 20, "y": 20, "w": 40, "h": 20, "r": 128, "g": 128, "b": 128},
                {"op": "SLEEP", "ms": 30},
                {"op": "RECT", "x": 70, "y": 70, "w": 30, "h": 30, "r": 200, "g": 200, "b": 200},
                {"op": "DAC_WRITE", "ch": 1, "val": 180},
                {"op": "INTEGRATE", "tau": 0.1, "src": 0, "dst": 1},
                {"op": "FILTER", "type": "lowpass", "fc": 1000, "src": 1, "dst": 2},
                {"op": "COMMIT"}
            ]
        }
        
        # Load into P1 and P5
        self.panes['P1']['widget'].insert('1.0', sample_python)
        self.panes['P5']['widget'].insert('1.0', json.dumps(sample_hlir, indent=2))
        
        # Trigger initial update from P5
        self.loop.call_soon_threadsafe(lambda: self.engine.on_edit('P5'))
        
        # Start status updates
        self.after(1000, self.periodic_status_update)
    
    def periodic_status_update(self):
        """Periodic status bar updates"""
        self.update_status_bar()
        self.after(1000, self.periodic_status_update)

if __name__ == "__main__":
    try:
        app = PXOSWorkbench6Pane()
        app.mainloop()
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure pxos_bus.py and pxos_validator.py are in the same directory")
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()