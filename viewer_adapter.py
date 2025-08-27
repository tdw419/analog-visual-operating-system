#!/usr/bin/env python3
"""
VisualPython to Analog Workbench Adapter

This adapter intercepts VisualPython draw calls and converts them to the 
analog workbench format, enabling seamless integration between the two systems.

Usage:
    import viewer_adapter as adapter
    
    # In your VisualPython code, replace direct draw calls with adapter calls
    adapter.RECT(50, 30, 100, 40, 128)
    adapter.TEXT(55, 35, "HELLO", 255)
    adapter.COMMIT()
    
    # Get the captured operations as CSV
    csv_output = adapter.get_csv()
"""

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class AnalogOperation:
    """Represents a single analog operation"""
    op_type: str
    timestamp: float
    params: Dict[str, Any] = field(default_factory=dict)
    line_info: Optional[str] = None

class ViewerAdapter:
    """Adapter class that captures VisualPython operations for analog workbench"""
    
    def __init__(self):
        self.operations: List[AnalogOperation] = []
        self.current_frame = 0
        self.start_time = time.time()
        
        # State tracking for analog operations
        self.current_x = 0
        self.current_y = 0
        self.current_gray = 128
        self.current_width = 10
        self.current_height = 10
    
    def reset(self):
        """Clear all captured operations and reset state"""
        self.operations.clear()
        self.current_frame = 0
        self.start_time = time.time()
        self.current_x = 0
        self.current_y = 0
        self.current_gray = 128
        self.current_width = 10
        self.current_height = 10
    
    def _add_operation(self, op_type: str, **params):
        """Add an operation to the capture list"""
        operation = AnalogOperation(
            op_type=op_type,
            timestamp=time.time() - self.start_time,
            params=params
        )
        self.operations.append(operation)
    
    # === Core Drawing Operations ===
    
    def CLEAR(self, r: int = 0, g: int = 20, b: int = 40):
        """Clear screen with background color"""
        # Convert RGB to grayscale for analog system
        gray = int(0.299 * r + 0.587 * g + 0.114 * b)
        self._add_operation("CLEAR", gray=gray)
    
    def RECT(self, x: int, y: int, w: int, h: int, gray: int = 128):
        """Draw a rectangle"""
        self.current_x = x
        self.current_y = y
        self.current_width = w
        self.current_height = h
        self.current_gray = gray
        self._add_operation("RECT", x=x, y=y, w=w, h=h, gray=gray)
    
    def TEXT(self, x: int, y: int, text: str, gray: int = 255):
        """Draw text (converted to visual representation)"""
        self.current_x = x
        self.current_y = y
        self.current_gray = gray
        self._add_operation("TEXT", x=x, y=y, text=text, gray=gray)
    
    def SET_PIXEL(self, x: int, y: int, gray: int = 255):
        """Set a single pixel"""
        self._add_operation("SET_PIXEL", x=x, y=y, gray=gray)
    
    # === Frame Control ===
    
    def COMMIT(self):
        """Commit current frame operations"""
        self._add_operation("COMMIT", frame=self.current_frame)
        self.current_frame += 1
    
    def SLEEP(self, ms: int):
        """Add a sleep/delay operation"""
        self._add_operation("SLEEP", duration_ms=ms)
    
    # === Analog Hardware Operations ===
    
    def DAC_WRITE(self, channel: int, value: int):
        """Write to DAC channel"""
        self._add_operation("DAC_WRITE", channel=channel, value=value)
    
    def ADC_READ(self, channel: int):
        """Read from ADC channel (placeholder for future implementation)"""
        self._add_operation("ADC_READ", channel=channel)
    
    def PWM_OUT(self, pin: int, duty_cycle: int):
        """Output PWM signal"""
        self._add_operation("PWM_OUT", pin=pin, duty_cycle=duty_cycle)
    
    def SYNC_ROW(self, row_index: int):
        """Synchronization marker for row-based processing"""
        self._add_operation("SYNC_ROW", row=row_index)
    
    def SYNC_PAGE(self, page_index: int):
        """Synchronization marker for page-based processing"""
        self._add_operation("SYNC_PAGE", page=page_index)
    
    # === Advanced Operations ===
    
    def CIRCLE(self, x: int, y: int, radius: int, gray: int = 128):
        """Draw a circle (approximated with rectangles for analog system)"""
        # Simple approximation - could be enhanced with better circle rendering
        self._add_operation("CIRCLE", x=x, y=y, radius=radius, gray=gray)
    
    def LINE(self, x1: int, y1: int, x2: int, y2: int, gray: int = 128):
        """Draw a line"""
        self._add_operation("LINE", x1=x1, y1=y1, x2=x2, y2=y2, gray=gray)
    
    # === Data Export ===
    
    def get_csv(self) -> str:
        """Convert captured operations to CSV format for analog workbench"""
        csv_lines = ["frame,op,x,y,w,h,gray,text,duration_ms,channel,value,line"]
        
        current_frame = 0
        
        for op in self.operations:
            op_type = op.op_type
            params = op.params
            
            # Build CSV row
            row = [
                current_frame,  # frame
                op_type,        # op
                params.get('x', ''),        # x
                params.get('y', ''),        # y  
                params.get('w', ''),        # w
                params.get('h', ''),        # h
                params.get('gray', ''),     # gray
                params.get('text', ''),     # text
                params.get('duration_ms', ''),  # duration_ms
                params.get('channel', ''),  # channel
                params.get('value', ''),    # value
                ''  # line (for source line tracking)
            ]
            
            csv_lines.append(','.join(str(field) for field in row))
            
            # Update frame counter on COMMIT
            if op_type == "COMMIT":
                current_frame = params.get('frame', current_frame + 1)
        
        return '\n'.join(csv_lines)
    
    def get_operations_summary(self) -> str:
        """Get a summary of captured operations"""
        op_counts = {}
        for op in self.operations:
            op_counts[op.op_type] = op_counts.get(op.op_type, 0) + 1
        
        summary = f"Captured {len(self.operations)} operations:\n"
        for op_type, count in sorted(op_counts.items()):
            summary += f"  {op_type}: {count}\n"
        
        return summary
    
    def get_source_code(self) -> str:
        """Generate source code representation of captured operations"""
        lines = ["# Generated from VisualPython adapter", ""]
        
        for op in self.operations:
            op_type = op.op_type
            params = op.params
            
            if op_type == "CLEAR":
                gray = params.get('gray', 0)
                lines.append(f"clear({gray}, {gray}, {gray})")
            elif op_type == "RECT":
                lines.append(f"rect({params['x']}, {params['y']}, {params['w']}, {params['h']}, {params['gray']})")
            elif op_type == "TEXT":
                lines.append(f"text({params['x']}, {params['y']}, \"{params['text']}\", {params['gray']})")
            elif op_type == "COMMIT":
                lines.append("commit()")
            elif op_type == "SLEEP":
                lines.append(f"sleep({params['duration_ms']})")
            elif op_type == "DAC_WRITE":
                lines.append(f"dac_write({params['channel']}, {params['value']})")
            elif op_type == "SYNC_ROW":
                lines.append(f"sync_row({params['row']})")
            else:
                lines.append(f"# {op_type}: {params}")
        
        return '\n'.join(lines)

# Global adapter instance for easy access
_global_adapter = ViewerAdapter()

# === Global Functions for Easy Integration ===

def reset():
    """Reset the global adapter"""
    _global_adapter.reset()

def CLEAR(r: int = 0, g: int = 20, b: int = 40):
    """Clear screen - global function"""
    _global_adapter.CLEAR(r, g, b)

def RECT(x: int, y: int, w: int, h: int, gray: int = 128):
    """Draw rectangle - global function"""
    _global_adapter.RECT(x, y, w, h, gray)

def TEXT(x: int, y: int, text: str, gray: int = 255):
    """Draw text - global function"""
    _global_adapter.TEXT(x, y, text, gray)

def COMMIT():
    """Commit frame - global function"""
    _global_adapter.COMMIT()

def SLEEP(ms: int):
    """Sleep - global function"""
    _global_adapter.SLEEP(ms)

def DAC_WRITE(channel: int, value: int):
    """DAC write - global function"""
    _global_adapter.DAC_WRITE(channel, value)

def SYNC_ROW(row: int):
    """Sync row - global function"""
    _global_adapter.SYNC_ROW(row)

def get_csv() -> str:
    """Get CSV output - global function"""
    return _global_adapter.get_csv()

def get_source_code() -> str:
    """Get source code - global function"""
    return _global_adapter.get_source_code()

def get_operations_summary() -> str:
    """Get operations summary - global function"""
    return _global_adapter.get_operations_summary()

# === VisualPython Integration Helpers ===

class VisualPythonBridge:
    """Bridge class for integrating with existing VisualPython systems"""
    
    def __init__(self, adapter: ViewerAdapter = None):
        self.adapter = adapter or _global_adapter
        
    def patch_visualpython_calls(self, visualpython_module):
        """Monkey-patch VisualPython module to use adapter"""
        # Store original functions
        original_functions = {}
        
        # Patch drawing functions
        patch_functions = ['RECT', 'TEXT', 'CLEAR', 'COMMIT', 'SLEEP']
        
        for func_name in patch_functions:
            if hasattr(visualpython_module, func_name):
                original_functions[func_name] = getattr(visualpython_module, func_name)
                setattr(visualpython_module, func_name, getattr(self.adapter, func_name))
        
        return original_functions
    
    def unpatch_visualpython_calls(self, visualpython_module, original_functions):
        """Restore original VisualPython functions"""
        for func_name, original_func in original_functions.items():
            setattr(visualpython_module, func_name, original_func)

# === Example Usage ===

if __name__ == "__main__":
    print("🔗 VisualPython to Analog Workbench Adapter")
    print("=" * 50)
    
    # Example capture session
    reset()
    
    # Simulate some VisualPython operations
    CLEAR(0, 20, 40)
    RECT(50, 30, 100, 40, 128)
    TEXT(55, 35, "ANALOG", 255)
    COMMIT()
    
    RECT(60, 80, 80, 30, 160)
    TEXT(65, 85, "CODE", 255)
    COMMIT()
    
    SLEEP(100)
    DAC_WRITE(2, 200)
    SYNC_ROW(1)
    
    # Show results
    print("Operations Summary:")
    print(get_operations_summary())
    
    print("\nGenerated Source Code:")
    print(get_source_code())
    
    print("\nCSV Output (first 5 lines):")
    csv_output = get_csv()
    for i, line in enumerate(csv_output.split('\n')[:6]):
        print(f"  {line}")
    
    print(f"\nTotal CSV lines: {len(csv_output.split())} lines")
    print("✅ Adapter ready for integration with Analog Workbench!")