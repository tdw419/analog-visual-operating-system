"""
Visual backends for VisualPython rendering

This module provides different rendering backends for displaying
Python execution as visual operations.
"""

import time
import threading
import csv
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from pathlib import Path

# Optional PIL import for PNG support
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

# Import visual element class
try:
    from .core import VisualElement
except ImportError:
    # Fallback for standalone testing
    from dataclasses import dataclass
    
    @dataclass
    class VisualElement:
        element_type: str
        content: str
        x: int
        y: int
        color: str = '#00ff88'


class VisualBackend(ABC):
    """Abstract base class for visual backends"""
    
    @abstractmethod
    def render_elements(self, elements: List[VisualElement]):
        """Render visual elements to the display"""
        pass
    
    @abstractmethod
    def clear(self):
        """Clear the display"""
        pass
    
    @abstractmethod
    def update(self):
        """Update the display"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Clean up resources"""
        pass


class ConsoleBackend(VisualBackend):
    """
    Console backend for text-based visual output.
    
    Provides the core "no compilation" experience even in environments
    without GUI support.
    """
    
    def __init__(self, **kwargs):
        self.last_elements = []
        self.console_width = kwargs.get('width', 80)
        self.show_positions = kwargs.get('show_positions', False)
        self.color_mode = kwargs.get('color_mode', 'ansi')
        
        # ANSI color codes
        self.colors = {
            '#00ff88': '\033[92m',  # Green
            '#00ffff': '\033[96m',  # Cyan
            '#ffff00': '\033[93m',  # Yellow
            '#ff4444': '\033[91m',  # Red
            '#ff88ff': '\033[95m',  # Magenta
            '#ffffff': '\033[97m',  # White
            '#88ff88': '\033[92m',  # Light Green
            '#88ffff': '\033[96m',  # Light Cyan
        }
        self.reset_color = '\033[0m'
    
    def render_elements(self, elements: List[VisualElement]):
        """Render elements to console"""
        if not elements:
            return
        
        # Only show new elements to avoid spam
        new_elements = elements[len(self.last_elements):]
        
        for element in new_elements:
            self._render_element(element)
        
        self.last_elements = elements.copy()
    
    def _render_element(self, element: VisualElement):
        """Render a single element to console"""
        content = element.content
        
        if self.show_positions:
            content = f"[{element.x},{element.y}] {content}"
        
        # Apply color if supported
        if self.color_mode == 'ansi' and element.color in self.colors:
            content = f"{self.colors[element.color]}{content}{self.reset_color}"
        
        # Add element type indicator
        type_indicators = {
            'variable': '📊',
            'variable_bar': '▬',
            'output': '💬',
            'error': '❌',
            'function_call': '🔧',
            'loop_start': '🔄',
            'loop_iteration': '  ↳',
            'if_condition': '❓',
        }
        
        indicator = type_indicators.get(element.element_type, '▶️')
        
        # Special handling for variable bars
        if element.element_type == 'variable_bar':
            bar_width = element.metadata.get('bar_width', 0)
            value = element.metadata.get('value', 0)
            bar_chars = int(bar_width / 5)  # Scale down for console
            bar = '█' * bar_chars
            print(f"  {bar} ({value})")
        else:
            print(f"{indicator} {content}")
    
    def clear(self):
        """Clear console display"""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
        self.last_elements = []
        
        print("🔥 VisualPython Console Display")
        print("=" * self.console_width)
    
    def update(self):
        """Console doesn't need explicit updates"""
        pass
    
    def cleanup(self):
        """No cleanup needed for console"""
        print("\n" + "=" * self.console_width)
        print("🔥 VisualPython execution complete")


try:
    import tkinter as tk
    from tkinter import ttk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False


class TkinterBackend(VisualBackend):
    """
    Tkinter-based visual backend.
    
    Provides a GUI window showing Python execution as visual elements
    with 5x7 bitmap font for pixel-perfect rendering.
    """
    
    def __init__(self, width=800, height=600, **kwargs):
        if not TKINTER_AVAILABLE:
            raise ImportError("Tkinter not available")
        
        self.width = width
        self.height = height
        self.kwargs = kwargs
        
        # Create GUI components
        self.root = tk.Tk()
        self.root.title("VisualPython - Direct Visual Execution")
        self.root.geometry(f"{width}x{height}")
        self.root.configure(bg='#001122')
        
        self._setup_gui()
        self._setup_bitmap_font()
        
        # Element tracking
        self.canvas_elements = []
        
        # Start GUI in separate thread if needed
        self._gui_ready = True
    
    def _setup_gui(self):
        """Setup the GUI layout"""
        # Main frame
        main_frame = tk.Frame(self.root, bg='#001122')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="🔥 VisualPython - Revolutionary Direct Execution",
            font=("Consolas", 14, "bold"),
            bg='#001122',
            fg='#00ff88'
        )
        title_label.pack(pady=(0, 10))
        
        # Canvas for visual output
        self.canvas = tk.Canvas(
            main_frame,
            bg='#001100',
            highlightthickness=0,
            width=self.width-20,
            height=self.height-100
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_bar = tk.Label(
            main_frame,
            text="Ready for direct visual execution...",
            font=("Consolas", 9),
            bg='#002244',
            fg='#88ffff',
            anchor=tk.W
        )
        self.status_bar.pack(fill=tk.X, pady=(5, 0))
    
    def _setup_bitmap_font(self):
        """Initialize the 5x7 bitmap font for pixel-perfect text"""
        self.font5x7 = {
            'A': [0x0E, 0x11, 0x1F, 0x11, 0x11], 'B': [0x1E, 0x11, 0x1E, 0x11, 0x1E],
            'C': [0x0E, 0x11, 0x10, 0x11, 0x0E], 'D': [0x1E, 0x11, 0x11, 0x11, 0x1E],
            'E': [0x1F, 0x10, 0x1E, 0x10, 0x1F], 'F': [0x1F, 0x10, 0x1E, 0x10, 0x10],
            'G': [0x0E, 0x11, 0x13, 0x11, 0x0E], 'H': [0x11, 0x11, 0x1F, 0x11, 0x11],
            'I': [0x0E, 0x04, 0x04, 0x04, 0x0E], 'L': [0x10, 0x10, 0x10, 0x10, 0x1F],
            'M': [0x11, 0x1B, 0x15, 0x11, 0x11], 'N': [0x11, 0x19, 0x15, 0x13, 0x11],
            'O': [0x0E, 0x11, 0x11, 0x11, 0x0E], 'P': [0x1E, 0x11, 0x1E, 0x10, 0x10],
            'R': [0x1E, 0x11, 0x1E, 0x14, 0x13], 'S': [0x0F, 0x10, 0x0E, 0x01, 0x1E],
            'T': [0x1F, 0x04, 0x04, 0x04, 0x04], 'U': [0x11, 0x11, 0x11, 0x11, 0x0E],
            'V': [0x11, 0x11, 0x11, 0x0A, 0x04], 'W': [0x11, 0x11, 0x15, 0x1B, 0x11],
            'X': [0x11, 0x0A, 0x04, 0x0A, 0x11], 'Y': [0x11, 0x0A, 0x04, 0x04, 0x04],
            'Z': [0x1F, 0x02, 0x04, 0x08, 0x1F],
            '0': [0x0E, 0x11, 0x11, 0x11, 0x0E], '1': [0x04, 0x0C, 0x04, 0x04, 0x0E],
            '2': [0x0E, 0x11, 0x02, 0x08, 0x1F], '3': [0x1F, 0x02, 0x06, 0x01, 0x1E],
            '4': [0x02, 0x06, 0x0A, 0x1F, 0x02], '5': [0x1F, 0x10, 0x1E, 0x01, 0x1E],
            '6': [0x06, 0x08, 0x1E, 0x11, 0x0E], '7': [0x1F, 0x01, 0x02, 0x04, 0x08],
            '8': [0x0E, 0x11, 0x0E, 0x11, 0x0E], '9': [0x0E, 0x11, 0x0F, 0x02, 0x0C],
            ' ': [0x00, 0x00, 0x00, 0x00, 0x00], ':': [0x00, 0x04, 0x00, 0x04, 0x00],
            '(': [0x02, 0x04, 0x04, 0x04, 0x02], ')': [0x08, 0x04, 0x04, 0x04, 0x08],
            '!': [0x04, 0x04, 0x04, 0x00, 0x04], ',': [0x00, 0x00, 0x00, 0x04, 0x08],
            '.': [0x00, 0x00, 0x00, 0x00, 0x04], '_': [0x00, 0x00, 0x00, 0x00, 0x1F],
            '=': [0x00, 0x1F, 0x00, 0x1F, 0x00], '+': [0x00, 0x04, 0x1F, 0x04, 0x00],
            '-': [0x00, 0x00, 0x1F, 0x00, 0x00], '*': [0x00, 0x0A, 0x04, 0x0A, 0x00],
            '/': [0x01, 0x02, 0x04, 0x08, 0x10]
        }
    
    def render_elements(self, elements: List[VisualElement]):
        """Render elements to Tkinter display"""
        if not elements:
            return
        
        try:
            self._update_display(elements)
        except Exception as e:
            print(f"Render error: {e}")
    
    def _update_display(self, elements: List[VisualElement]):
        """Update display with new elements"""
        # Clear previous elements
        self.canvas.delete("visual_element")
        
        # Render header
        self._render_bitmap_text("VISUALPYTHON DIRECT EXECUTION", 20, 20, scale=2, color='#00ff88')
        
        # Render all elements
        for element in elements:
            self._render_element(element)
        
        # Update status
        self.status_bar.config(
            text=f"Rendered {len(elements)} elements | "
                 f"Time: {time.strftime('%H:%M:%S')}"
        )
    
    def _render_element(self, element: VisualElement):
        """Render a single visual element"""
        if element.element_type == 'variable':
            # Render variable text
            self._render_bitmap_text(
                element.content, 
                element.x, 
                element.y, 
                scale=2, 
                color=element.color
            )
        
        elif element.element_type == 'variable_bar':
            # Render variable bar
            bar_width = element.metadata.get('bar_width', 0)
            bar_height = 15
            
            self.canvas.create_rectangle(
                element.x, element.y,
                element.x + bar_width, element.y + bar_height,
                fill=element.color,
                outline='',
                tags="visual_element"
            )
        
        elif element.element_type in ['output', 'print']:
            # Render output text
            self._render_bitmap_text(
                element.content,
                element.x,
                element.y,
                scale=2,
                color=element.color
            )
        
        elif element.element_type.startswith('loop'):
            # Render loop indicators
            self._render_bitmap_text(
                element.content,
                element.x,
                element.y,
                scale=1,
                color=element.color
            )
        
        else:
            # Default text rendering for other elements
            self._render_bitmap_text(
                element.content,
                element.x,
                element.y,
                scale=1,
                color=element.color
            )
    
    def _render_bitmap_text(self, text: str, x: int, y: int, scale: int = 1, color: str = '#00ff88'):
        """Render text using 5x7 bitmap font"""
        current_x = x
        
        for char in text.upper():
            if char not in self.font5x7:
                char = ' '  # Default to space for unknown characters
            
            glyph = self.font5x7[char]
            
            # Render each pixel of the character
            for col in range(5):
                col_bits = glyph[col]
                for row in range(7):
                    if col_bits & (1 << (6 - row)):  # Check if pixel should be on
                        pixel_x = current_x + col * scale
                        pixel_y = y + row * scale
                        
                        self.canvas.create_rectangle(
                            pixel_x, pixel_y,
                            pixel_x + scale, pixel_y + scale,
                            fill=color,
                            outline='',
                            tags="visual_element"
                        )
            
            current_x += 6 * scale  # Move to next character position
    
    def clear(self):
        """Clear the display"""
        try:
            self.canvas.delete("all")
        except:
            pass
    
    def update(self):
        """Update display"""
        try:
            self.root.update()
        except:
            pass
    
    def cleanup(self):
        """Clean up Tkinter resources"""
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass


class SimulatorBackend(VisualBackend):
    """
    Headless simulator backend that wraps the SimRenderer from mock_backend.
    
    This provides the same visual API as other backends but saves frames
    as PNG/PPM files instead of displaying them in a GUI.
    """
    
    def __init__(self, width=800, height=600, **kwargs):
        from .mock_backend import SimRenderer, SimDrawAPI
        
        # Extract simulator-specific options
        out_dir = kwargs.get('out_dir', 'vp_sim_frames')
        file_prefix = kwargs.get('file_prefix', 'vp_sim_')
        start_index = kwargs.get('start_index', 0)
        bg_color = kwargs.get('bg_color', '#001100')
        
        # Create the simulator renderer
        self.sim_renderer = SimRenderer(
            width=width,
            height=height,
            scale=1,
            title="VisualPython Simulator",
            out_dir=out_dir,
            file_prefix=file_prefix,
            start_index=start_index,
            bg=bg_color
        )
        
        self.draw_api = SimDrawAPI(self.sim_renderer)
        self.width = width
        self.height = height
        self.last_elements = []
        
    def render_elements(self, elements: List[VisualElement]):
        """Render elements using the simulator backend"""
        if not elements:
            return
        
        # Clear the frame first
        self.draw_api.clear('#001100')
        
        # Render header
        self.draw_api.text(20, 20, "VISUALPYTHON SIMULATOR", 0, 255, 136)
        
        # Render all elements
        for element in elements:
            self._render_element(element)
        
        # Commit the frame
        self.draw_api.commit()
        
        self.last_elements = elements.copy()
    
    def _render_element(self, element: VisualElement):
        """Render a single visual element using the simulator API"""
        # Parse color from hex to RGB
        color_hex = element.color.lstrip('#')
        try:
            r = int(color_hex[0:2], 16)
            g = int(color_hex[2:4], 16)
            b = int(color_hex[4:6], 16)
        except (ValueError, IndexError):
            r, g, b = 0, 255, 136  # Default green
        
        if element.element_type == 'variable':
            # Render variable text
            self.draw_api.text(element.x, element.y, element.content, r, g, b)
        
        elif element.element_type == 'variable_bar':
            # Render variable bar
            bar_width = element.metadata.get('bar_width', 0)
            bar_height = 15
            self.draw_api.rect(element.x, element.y, bar_width, bar_height, r, g, b)
        
        elif element.element_type in ['output', 'print']:
            # Render output text
            self.draw_api.text(element.x, element.y, element.content, r, g, b)
        
        elif element.element_type.startswith('loop'):
            # Render loop indicators
            self.draw_api.text(element.x, element.y, element.content, r, g, b)
        
        else:
            # Default text rendering for other elements
            self.draw_api.text(element.x, element.y, element.content, r, g, b)
    
    def clear(self):
        """Clear the simulator display"""
        self.draw_api.clear('#001100')
        self.last_elements = []
    
    def update(self):
        """Update display (no-op for simulator)"""
        pass
    
    def cleanup(self):
        """Clean up simulator resources"""
        try:
            if hasattr(self.sim_renderer, 'close'):
                self.sim_renderer.close()
        except Exception:
            pass


class RecordRenderer:
    """
    CSV recording wrapper for any renderer (TkRenderer, SimRenderer, etc.).
    Records all draw operations to CSV with frame batching.
    """
    
    def __init__(self, wrapped, csv_path="vp_record.csv", start_frame=0):
        self.wrapped = wrapped
        self.csv_path = csv_path
        self.frame = start_frame
        
        # Open CSV file and write header
        self._fh = open(csv_path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(
            self._fh, 
            fieldnames=["frame", "op", "x", "y", "w", "h", "r", "g", "b", "text"]
        )
        self._writer.writeheader()
    
    def _hex_to_rgb(self, hx):
        """Convert hex color to RGB tuple."""
        hx = (hx or "#000000").lstrip("#")
        try:
            return (int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16))
        except (ValueError, IndexError):
            return (0, 0, 0)
    
    def _write_row(self, op, **kwargs):
        """Write a row to the CSV file."""
        row = {
            "frame": self.frame,
            "op": op,
            "x": kwargs.get("x", ""),
            "y": kwargs.get("y", ""),
            "w": kwargs.get("w", ""),
            "h": kwargs.get("h", ""),
            "r": kwargs.get("r", ""),
            "g": kwargs.get("g", ""),
            "b": kwargs.get("b", ""),
            "text": kwargs.get("text", ""),
        }
        self._writer.writerow(row)
        self._fh.flush()
    
    # Forward properties
    @property
    def w(self):
        return self.wrapped.w
    
    @property
    def h(self):
        return self.wrapped.h
    
    # Forward methods with recording
    def space(self):
        return self.wrapped.space()
    
    def clear(self, color="#001100"):
        r, g, b = self._hex_to_rgb(color)
        self._write_row("CLEAR", r=r, g=g, b=b)
        self.wrapped.clear(color)
    
    def set_pixel(self, x, y, r, g, b):
        self._write_row("PIXEL", x=int(x), y=int(y), r=int(r), g=int(g), b=int(b))
        self.wrapped.set_pixel(x, y, r, g, b)
    
    def rect(self, x, y, w, h, r, g, b):
        self._write_row("RECT", x=int(x), y=int(y), w=int(w), h=int(h), r=int(r), g=int(g), b=int(b))
        self.wrapped.rect(x, y, w, h, r, g, b)
    
    def text(self, x, y, msg, r=144, g=238, b=144):
        self._write_row("TEXT", x=int(x), y=int(y), r=int(r), g=int(g), b=int(b), text=str(msg))
        self.wrapped.text(x, y, msg, r, g, b)
    
    def commit(self):
        self._write_row("COMMIT")
        self.wrapped.commit()
        self.frame += 1
    
    def close(self):
        try:
            self._fh.close()
        except Exception:
            pass
        try:
            self.wrapped.close()
        except Exception:
            pass
    
    def __getattr__(self, name):
        """Forward any other attributes to the wrapped renderer."""
        return getattr(self.wrapped, name)


# CSV Playback Functions
CSV_COLS = ["frame", "op", "x", "y", "w", "h", "r", "g", "b", "text"]


def _as_int(v, default=0):
    """Safely convert value to int."""
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return default


def _rgb_hex(r, g, b):
    """Convert RGB values to hex color string."""
    return f"#{_as_int(r, 0):02x}{_as_int(g, 0):02x}{_as_int(b, 0):02x}"


def csv_play(renderer, csv_path: str, frame_delay: float = 0.0):
    """
    Play a sparse CSV file frame by frame.
    
    CSV format (frame-batched):
    frame,op,x,y,w,h,r,g,b,text
    1,CLEAR,,,,0,17,0,
    1,RECT,130,30,60,40,40,120,240,
    1,TEXT,136,36,,,,,,HELLO
    2,PIXEL,100,50,,,255,0,0,
    2,COMMIT,,,,,,,
    
    All operations with the same frame number are applied together,
    then commit() is called once per frame.
    """
    # Read and group rows by frame
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    by_frame = {}
    for row in rows:
        frame_num = _as_int(row.get("frame", 0))
        by_frame.setdefault(frame_num, []).append(row)
    
    # Process frames in order
    for frame_num in sorted(by_frame.keys()):
        print(f"Processing frame {frame_num}...")
        
        # Apply all operations for this frame
        for row in by_frame[frame_num]:
            op = (row.get("op") or "").strip().upper()
            
            if op in ("CLEAR", "BG", "BACKGROUND"):
                color = _rgb_hex(row.get("r", 0), row.get("g", 0), row.get("b", 0))
                renderer.clear(color)
            
            elif op in ("RECT", "BOX"):
                x = _as_int(row.get("x", 0))
                y = _as_int(row.get("y", 0))
                w = _as_int(row.get("w", 0))
                h = _as_int(row.get("h", 0))
                r = _as_int(row.get("r", 0))
                g = _as_int(row.get("g", 0))
                b = _as_int(row.get("b", 0))
                renderer.rect(x, y, w, h, r, g, b)
            
            elif op in ("PIXEL", "SET", "SET_PIXEL"):
                x = _as_int(row.get("x", 0))
                y = _as_int(row.get("y", 0))
                r = _as_int(row.get("r", 0))
                g = _as_int(row.get("g", 0))
                b = _as_int(row.get("b", 0))
                renderer.set_pixel(x, y, r, g, b)
            
            elif op in ("TEXT", "LABEL"):
                x = _as_int(row.get("x", 0))
                y = _as_int(row.get("y", 0))
                text = row.get("text", "")
                r = _as_int(row.get("r", 144))
                g = _as_int(row.get("g", 238))
                b = _as_int(row.get("b", 144))
                renderer.text(x, y, text, r, g, b)
            
            elif op in ("COMMIT", "SHOW"):
                # No-op; we commit once at end of frame
                pass
        
        # Commit the frame (saves PNG/PPM)
        renderer.commit()
        
        # Optional delay between frames
        if frame_delay > 0.0:
            time.sleep(frame_delay)


# Backend factory function
def create_backend(backend_name: str, **kwargs) -> VisualBackend:
    """
    Create a visual backend by name
    
    Args:
        backend_name: 'tkinter', 'console', 'simulator', etc.
        **kwargs: Backend-specific options
        
    Returns:
        VisualBackend instance
    """
    backends = {
        'console': ConsoleBackend,
        'tkinter': TkinterBackend if TKINTER_AVAILABLE else ConsoleBackend,
        'simulator': SimulatorBackend,
        'sim': SimulatorBackend,  # Alias for simulator
    }
    
    backend_class = backends.get(backend_name, ConsoleBackend)
    
    try:
        return backend_class(**kwargs)
    except Exception as e:
        print(f"Failed to create {backend_name} backend: {e}")
        print("Falling back to console backend")
        return ConsoleBackend(**kwargs)