"""
Headless simulator backend for VisualPython with CSV record/playback support.

This backend provides:
- Direct Python-to-pixels execution without GUI dependencies
- Frame-based CSV recording and playback
- PNG/PPM frame export for inspection
- Perfect for CI/CD, testing, and AI training workflows
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time
import csv
from pathlib import Path

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


@dataclass
class MockEvent:
    """Represents a mock rendering event."""
    timestamp: float
    operation: str
    params: Dict[str, Any]


class SimRenderer:
    """
    Headless renderer that records pixels and saves frames as PNG/PPM.
    Perfect for CI/CD, CSV playback, and testing without GUI dependencies.
    """
    
    def __init__(self, width=800, height=600, scale=1, title="SimRenderer",
                 out_dir="vp_sim_frames", file_prefix="vp_sim_", start_index=0,
                 bg="#001100"):
        self.w, self.h, self.scale = width, height, scale
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.file_prefix = file_prefix
        self.index = start_index
        self.bg = bg
        self._space_pressed = False
        self._batch: List[Dict[str, Any]] = []
        
        # Track rendering events for testing
        self.events: List[MockEvent] = []
        self.console_output: List[str] = []
        
        # Initialize frame buffer
        self._new_frame()
    
    def _new_frame(self):
        """Initialize a new frame buffer."""
        self.buf = [[self._hex_to_rgb(self.bg) for _ in range(self.w)] for _ in range(self.h)]
        self._dirty = False
    
    def _hex_to_rgb(self, hx):
        """Convert hex color to RGB tuple."""
        hx = hx.lstrip('#')
        if len(hx) != 6:
            hx = "000000"
        try:
            return (int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16))
        except ValueError:
            return (0, 0, 0)
        
    def space(self) -> bool:
        """Check if space was pressed (simulation for testing)."""
        result = self._space_pressed
        self._space_pressed = False
        return result
    
    def trigger_space(self):
        """Trigger a space press for testing."""
        self._space_pressed = True
    
    def clear(self, color: str = "#001100"):
        """Clear the frame buffer."""
        self.bg = color
        self._new_frame()
        
        # Log event for testing
        self.events.append(MockEvent(
            timestamp=time.time(),
            operation='clear',
            params={'color': color}
        ))
        self.console_output.append(f"🧹 CLEAR: {color}")
    
    def set_pixel(self, x: int, y: int, r: int, g: int, b: int):
        """Set a single pixel in the frame buffer."""
        if 0 <= x < self.w and 0 <= y < self.h:
            self.buf[y][x] = (int(r), int(g), int(b))
            self._dirty = True
            
            # Also add to batch for event tracking
            self._batch.append({
                'operation': 'set_pixel',
                'x': x, 'y': y, 'r': r, 'g': g, 'b': b
            })
    
    def rect(self, x: int, y: int, w: int, h: int, r: int, g: int, b: int):
        """Draw a rectangle in the frame buffer."""
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(self.w, x0 + int(w)), min(self.h, y0 + int(h))
        
        if x1 <= x0 or y1 <= y0:
            return
        
        color = (int(r), int(g), int(b))
        for yy in range(y0, y1):
            row = self.buf[yy]
            for xx in range(x0, x1):
                row[xx] = color
        
        self._dirty = True
        
        # Log event
        self.events.append(MockEvent(
            timestamp=time.time(),
            operation='rect',
            params={'x': x, 'y': y, 'w': w, 'h': h, 'r': r, 'g': g, 'b': b}
        ))
        color_hex = f"#{r:02x}{g:02x}{b:02x}"
        self.console_output.append(f"📦 RECT: ({x},{y}) {w}x{h} {color_hex}")
    
    def text(self, x: int, y: int, msg: str, r: int = 144, g: int = 238, b: int = 144):
        """Draw text using 5x7 bitmap font."""
        # Use bitmap font rendering by calling rect for each pixel
        self._render_bitmap_text(str(msg), int(x), int(y), 2, (int(r), int(g), int(b)))
        
        # Log event
        self.events.append(MockEvent(
            timestamp=time.time(),
            operation='text',
            params={'x': x, 'y': y, 'text': str(msg), 'r': r, 'g': g, 'b': b}
        ))
        color_hex = f"#{r:02x}{g:02x}{b:02x}"
    def _render_bitmap_text(self, text: str, x: int, y: int, scale: int = 2, color=(144, 238, 144)):
        """Render text using 5x7 bitmap font."""
        # 5x7 font subset
        font5x7 = {
            'A': [0x0E, 0x11, 0x1F, 0x11, 0x11], 'B': [0x1E, 0x11, 0x1E, 0x11, 0x1E],
            'C': [0x0E, 0x11, 0x10, 0x11, 0x0E], 'D': [0x1E, 0x11, 0x11, 0x11, 0x1E],
            'E': [0x1F, 0x10, 0x1E, 0x10, 0x1F], 'F': [0x1F, 0x10, 0x1E, 0x10, 0x10],
            'H': [0x11, 0x11, 0x1F, 0x11, 0x11], 'L': [0x10, 0x10, 0x10, 0x10, 0x1F],
            'O': [0x0E, 0x11, 0x11, 0x11, 0x0E], 'R': [0x1E, 0x11, 0x1E, 0x14, 0x13],
            'W': [0x11, 0x11, 0x15, 0x1B, 0x11], ' ': [0x00, 0x00, 0x00, 0x00, 0x00],
            '0': [0x0E, 0x11, 0x11, 0x11, 0x0E], '1': [0x04, 0x0C, 0x04, 0x04, 0x0E],
            '2': [0x0E, 0x11, 0x02, 0x08, 0x1F], '3': [0x1F, 0x02, 0x06, 0x01, 0x1E],
            '!': [0x04, 0x04, 0x04, 0x00, 0x04], '.': [0x00, 0x00, 0x00, 0x00, 0x04],
        }
        
        ox = x
        for ch in text.upper():
            bits = font5x7.get(ch, font5x7[' '])
            for cx, col in enumerate(bits):
                for row in range(7):
                    if col & (1 << (6 - row)):
                        # Draw scaled pixel
                        for dy in range(scale):
                            for dx in range(scale):
                                px, py = ox + cx * scale + dx, y + row * scale + dy
                                if 0 <= px < self.w and 0 <= py < self.h:
                                    self.buf[py][px] = color
            ox += 6 * scale
        self._dirty = True
    
    def commit(self):
        """Commit batched operations and save frame."""
        # Process batched pixel operations
        if self._batch:
            for op in self._batch:
                self.events.append(MockEvent(
                    timestamp=time.time(),
                    operation=op['operation'],
                    params=op
                ))
            self._batch.clear()
        
        # Save frame to file
        if self._dirty or self.index == 0:  # Always save first frame
            path = self._save_frame()
            self.console_output.append(f"✅ COMMIT: Frame {self.index} saved to {path}")
        else:
            self.console_output.append(f"✅ COMMIT: No changes, frame {self.index} skipped")
        
        self.index += 1
        self._new_frame()  # Start fresh for next frame
    
    def _save_frame(self):
        """Save current frame buffer as PNG or PPM."""
        filename = f"{self.file_prefix}{self.index:04d}"
        
        if PILLOW_AVAILABLE:
            # Save as PNG using Pillow
            from PIL import Image
            im = Image.new("RGB", (self.w, self.h))
            flat = [px for row in self.buf for px in row]
            im.putdata(flat)
            out_path = self.out_dir / f"{filename}.png"
            im.save(out_path)
            return out_path
        else:
            # Save as PPM (widely readable)
            out_path = self.out_dir / f"{filename}.ppm"
            with open(out_path, "wb") as f:
                f.write(f"P6 {self.w} {self.h} 255\n".encode("ascii"))
                for row in self.buf:
                    f.write(bytes([c for (r, g, b) in row for c in (r, g, b)]))
            return out_path
    
    def close(self):
        """Clean up simulator backend."""
        self.console_output.append("🔴 CLOSE: SimRenderer closed")
        self.events.clear()


class RecordRenderer:
    """
    CSV recording wrapper for any renderer (SimRenderer, TkRenderer, etc.).
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
    
    # Testing utilities
    def get_rendered_events(self) -> List[MockEvent]:
        """Get all rendered events for testing verification."""
        return self.events.copy()
    
    def get_console_output(self) -> List[str]:
        """Get console output for debugging."""
        return self.console_output.copy()
    
    def count_operations(self, operation_type: str) -> int:
        """Count operations of a specific type."""
        return sum(1 for event in self.events if event.operation == operation_type)
    
    def find_events(self, **criteria) -> List[MockEvent]:
        """Find events matching specific criteria."""
        results = []
        for event in self.events:
            match = True
            for key, value in criteria.items():
                if key == 'operation':
                    if event.operation != value:
                        match = False
                        break
                elif key in event.params:
                    if event.params[key] != value:
                        match = False
                        break
                else:
                    match = False
                    break
            if match:
                results.append(event)
        return results
    
    def verify_sequence(self, expected_operations: List[str]) -> bool:
        """Verify that operations occurred in the expected sequence."""
        actual_ops = [event.operation for event in self.events]
        return actual_ops == expected_operations
    
    def print_summary(self):
        """Print a summary of all operations for debugging."""
        print("\n=== Mock Backend Summary ===")
        print(f"Total Events: {len(self.events)}")
        print(f"Dimensions: {self.w}x{self.h} (scale: {self.scale})")
        
        # Count by operation type
        op_counts = {}
        for event in self.events:
            op_counts[event.operation] = op_counts.get(event.operation, 0) + 1
        
        print("\nOperation Counts:")
        for op, count in sorted(op_counts.items()):
            print(f"  {op}: {count}")
        
        print("\nConsole Output:")
        for line in self.console_output[-10:]:  # Last 10 lines
            print(f"  {line}")
        print("="*30)


class SimDrawAPI:
    """Draw API wrapper for SimRenderer (headless simulator)."""
    
    def __init__(self, renderer):
        self.r = renderer
    
    def set_pixel(self, x: int, y: int, r: int, g: int, b: int):
        self.r.set_pixel(x, y, r, g, b)
    
    def rect(self, x: int, y: int, w: int, h: int, r: int, g: int, b: int):
        self.r.rect(x, y, w, h, r, g, b)
    
    def text(self, x: int, y: int, msg: str, r: int = 144, g: int = 238, b: int = 144):
        self.r.text(x, y, msg, r, g, b)
    
    def clear(self, color: str = "#001100"):
        self.r.clear(color)
    
    def commit(self):
        self.r.commit()
    
    def SPACE(self) -> bool:
        return self.r.space()


    def SPACE(self) -> bool:
        return self.r.space()


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
    import csv
    
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


# Test the mock backend
if __name__ == "__main__":
    print("Testing MockBackend...")
    
    # Create mock backend
    backend = MockBackend({'width': 800, 'height': 600})
    
    # Test operations
    backend.clear()
    backend.rect(10, 10, 100, 50, 255, 0, 0)
    backend.text(20, 70, "Hello World!", 0, 255, 0)
    backend.set_pixel(200, 200, 255, 255, 255)
    backend.commit()
    
    # Verify operations
    events = backend.get_rendered_events()
    print(f"\nCaptured {len(events)} events:")
    for i, event in enumerate(events):
        print(f"  {i+1}. {event.operation}: {event.params}")
    
    # Test verification methods
    print(f"\nRectangles drawn: {backend.count_operations('rect')}")
    print(f"Text drawn: {backend.count_operations('text')}")
    
    # Test sequence verification
    expected = ['clear', 'rect', 'text', 'set_pixel', 'commit']
    print(f"Sequence correct: {backend.verify_sequence(expected)}")
    
    # Print summary
    backend.print_summary()