# python_viewer.py (stub for your viewer; replace with real code)
from analog_code_workbench import ViewerAdapter  # Import adapter from workbench

def run_python_viewer():
    # Simulate your viewer drawing some rects (replace with your trace/draw logic)
    ViewerAdapter.RECT(10, 10, 50, 30, 128)
    ViewerAdapter.SLEEP(50)
    ViewerAdapter.RECT(70, 10, 50, 30, 200)
    # Use a value that is a multiple of 8 to avoid quantization errors in the test
    ViewerAdapter.DAC_WRITE(1, 144)
    ViewerAdapter.COMMIT()
    # Your real viewer would trace/execute code here, calling adapter functions for draws
