# python_viewer_demo.py
"""
Demo Python viewer that shows how to integrate your existing viewer
with the viewer adapter for the Analog Code Workbench.

Replace this with your actual Python viewer code, but keep the
adapter calls to capture operations.
"""

import viewer_adapter_simple as adapter

def run_python_viewer():
    """
    Main function called by the workbench.
    Replace this content with your actual viewer logic.
    """
    # Reset adapter state
    adapter.reset()
    
    # Example drawing sequence - replace with your actual viewer operations
    # Draw a simple scene
    adapter.RECT(20, 20, 40, 20, 64)     # Dark gray rectangle
    adapter.SLEEP(30)                     # 30ms delay
    
    adapter.RECT(80, 20, 40, 20, 160)    # Medium gray rectangle  
    adapter.SLEEP(30)
    
    adapter.RECT(80, 60, 40, 20, 220)    # Light gray rectangle
    
    # Hardware control example
    adapter.DAC_WRITE(1, 150)            # Write 150 to DAC channel 1
    adapter.SYNC_ROW(1)                  # Synchronization marker
    
    # Commit the frame
    adapter.COMMIT()

def demo_animation():
    """
    Example of an animated sequence
    """
    adapter.reset()
    
    # Animated sequence - moving rectangle
    for frame in range(5):
        x = 50 + frame * 30
        gray = 100 + frame * 30
        
        adapter.RECT(x, 50, 40, 40, gray)
        adapter.COMMIT()
        
        if frame < 4:  # Don't sleep on last frame
            adapter.SLEEP(100)

def demo_complex_scene():
    """
    More complex scene with multiple elements
    """
    adapter.reset()
    
    # Background
    adapter.RECT(0, 0, 320, 240, 30)    # Dark background
    
    # Multiple objects
    for i in range(3):
        x = 50 + i * 80
        y = 50 + i * 20
        gray = 80 + i * 40
        
        adapter.RECT(x, y, 60, 30, gray)
    
    # Control sequence
    adapter.DAC_WRITE(0, 100)
    adapter.DAC_WRITE(1, 200)
    adapter.SYNC_ROW(2)
    
    adapter.COMMIT()

# Different demo modes you can switch between
DEMO_MODES = {
    'simple': run_python_viewer,
    'animation': demo_animation,
    'complex': demo_complex_scene
}

def run_demo(mode='simple'):
    """Run a specific demo mode"""
    if mode in DEMO_MODES:
        DEMO_MODES[mode]()
    else:
        print(f"Unknown mode: {mode}")
        print(f"Available modes: {list(DEMO_MODES.keys())}")

if __name__ == "__main__":
    # Test the demos
    print("Testing simple demo:")
    run_python_viewer()
    print(f"Captured {adapter.get_ops_count()} operations")
    print("CSV output:")
    print(adapter.get_captured_csv())
    
    print("\n" + "="*50)
    print("Testing animation demo:")
    demo_animation()
    print(f"Captured {adapter.get_ops_count()} operations")
    print("CSV output (first 5 lines):")
    lines = adapter.get_captured_csv().split('\n')
    for line in lines[:5]:
        print(line)
    if len(lines) > 5:
        print(f"... and {len(lines) - 5} more lines")