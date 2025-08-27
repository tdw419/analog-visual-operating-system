# viewer_adapter_simple.py
"""
Simple viewer adapter to capture Python viewer operations and convert to CSV.
This is the minimal bridge between your existing Python viewer and the workbench.
"""

# Global operations list - captured operations as CSV lines
ops = []

def reset():
    """Clear all captured operations"""
    ops.clear()

def RECT(x, y, w, h, gray):
    """Capture rectangle drawing operation"""
    g = int(gray)
    ops.append(f"RECT,{int(x)},{int(y)},{int(w)},{int(h)},{g},{g},{g}")

def TEXT(x, y, text, gray=255):
    """Capture text operation (placeholder for now)"""
    # Could be expanded to rasterize text to rectangles
    pass

def COMMIT():
    """Mark end of frame"""
    ops.append("COMMIT")

def SLEEP(ms):
    """Capture timing operation"""
    ops.append(f"SLEEP,{int(ms)}")

def SYNC_ROW(i):
    """Capture synchronization marker"""
    ops.append(f"SYNC_ROW,{int(i)}")

def DAC_WRITE(ch, val):
    """Capture DAC write operation"""
    ops.append(f"DAC_WRITE,{int(ch)},{int(val)}")

def get_captured_csv():
    """Return all captured operations as CSV text"""
    return '\n'.join(ops)

def get_ops_count():
    """Return number of captured operations"""
    return len(ops)

# Alternative interface for direct use
class ViewerAdapter:
    """Class-based interface for the adapter"""
    
    @staticmethod
    def reset():
        reset()
    
    @staticmethod
    def RECT(x, y, w, h, gray):
        RECT(x, y, w, h, gray)
    
    @staticmethod
    def COMMIT():
        COMMIT()
    
    @staticmethod
    def SLEEP(ms):
        SLEEP(ms)
    
    @staticmethod
    def SYNC_ROW(i):
        SYNC_ROW(i)
    
    @staticmethod
    def DAC_WRITE(ch, val):
        DAC_WRITE(ch, val)
    
    @staticmethod
    def get_captured_csv():
        return get_captured_csv()

if __name__ == "__main__":
    # Simple test
    reset()
    RECT(20, 20, 40, 20, 64)
    SLEEP(30)
    RECT(80, 20, 40, 20, 160)
    DAC_WRITE(1, 150)
    COMMIT()
    
    print("Captured operations:")
    print(get_captured_csv())