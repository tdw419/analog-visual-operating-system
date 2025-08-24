# python_viewer.py (stub for your viewer; replace with real code)
from analog_code_workbench import ViewerAdapter  # Import adapter from workbench

def run_python_viewer():
    # Simulate your viewer drawing some rects (replace with your trace/draw logic)
    ViewerAdapter.RECT(20, 20, 40, 20, 64)
    ViewerAdapter.SLEEP(30)
    ViewerAdapter.RECT(80, 20, 40, 20, 160)
    ViewerAdapter.SLEEP(30)
    ViewerAdapter.RECT(80, 60, 40, 20, 220)
    # Use a value that is a multiple of 8 to avoid quantization errors in the test
    ViewerAdapter.DAC_WRITE(1, 176)
    ViewerAdapter.COMMIT()
