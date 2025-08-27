# your_viewer_main.py
"""
Smoke-test viewer for the Analog Code Workbench integration.
This demonstrates how to integrate any Python viewer with the workbench.

Replace this with your actual viewer logic while keeping the adapter calls.
"""
import viewer_adapter_simple as VA

def main():
    """Main viewer function - called by workbench"""
    VA.reset()
    
    # Basic drawing sequence - replace with your actual viewer operations
    VA.RECT(20, 20, 40, 20, 64)    # Dark gray rectangle
    VA.SLEEP(30)                    # 30ms delay
    VA.RECT(80, 20, 40, 20, 160)   # Medium gray rectangle
    VA.SLEEP(30)
    VA.RECT(80, 60, 40, 20, 220)   # Light gray rectangle
    VA.DAC_WRITE(1, 180)           # Hardware control - DAC channel 1, value 180
    VA.COMMIT()                    # Frame complete

def demo_animation():
    """Example of animated sequence"""
    VA.reset()
    
    # Animated bouncing rectangle
    for frame in range(5):
        x = 50 + frame * 30
        y = 50 + abs((frame - 2) * 15)  # Bounce effect
        gray = 100 + frame * 30
        
        VA.RECT(x, y, 30, 30, gray)
        VA.COMMIT()
        
        if frame < 4:  # Don't sleep on last frame
            VA.SLEEP(100)

def demo_hardware_control():
    """Example of hardware control sequence"""
    VA.reset()
    
    # Hardware control sequence
    VA.DAC_WRITE(0, 100)    # Channel 0, value 100
    VA.SLEEP(50)            # Wait 50ms
    VA.DAC_WRITE(1, 200)    # Channel 1, value 200
    VA.SYNC_ROW(1)          # Synchronization marker
    VA.DAC_WRITE(0, 0)      # Turn off channel 0
    VA.COMMIT()

# Entry point - you can switch between different demo modes
if __name__ == "__main__":
    # Test different demo functions
    print("Running main demo...")
    main()
    print(f"Captured {VA.get_ops_count()} operations")
    print("CSV output:")
    print(VA.get_captured_csv())