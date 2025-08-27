#!/usr/bin/env python3
"""
Integrated Demo: VisualPython + Analog Code Workbench

This demo shows how to use the viewer adapter to bridge VisualPython 
programs with the Analog Code Workbench for source-to-analog execution.

Run this to see the complete pipeline in action:
1. Write VisualPython-style code
2. Capture operations via adapter
3. Generate analog tiles and CSV
4. Execute on simulated analog hardware

Usage:
    python integrated_demo.py
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

# Import our components
import viewer_adapter as adapter
from analog_code_workbench import AnalogCodeWorkbench

def demo_basic_capture():
    """Demonstrate basic operation capture"""
    print("📡 Demo 1: Basic Operation Capture")
    print("-" * 40)
    
    # Reset adapter
    adapter.reset()
    
    # Simple drawing program
    adapter.CLEAR(0, 20, 40)
    adapter.RECT(50, 50, 100, 60, 128)
    adapter.TEXT(60, 70, "HELLO", 255)
    adapter.COMMIT()
    
    adapter.RECT(200, 100, 80, 40, 200)
    adapter.TEXT(210, 115, "WORLD", 255)
    adapter.COMMIT()
    
    # Show results
    print("Operations captured:")
    print(adapter.get_operations_summary())
    
    print("\nGenerated CSV (first 8 lines):")
    csv_lines = adapter.get_csv().split('\n')
    for i, line in enumerate(csv_lines[:8]):
        print(f"  {i+1}: {line}")
    
    print(f"\nTotal: {len(csv_lines)} CSV lines")

def demo_hardware_control():
    """Demonstrate hardware control operations"""
    print("\n🔧 Demo 2: Hardware Control")
    print("-" * 40)
    
    adapter.reset()
    
    # Hardware control sequence
    adapter.DAC_WRITE(0, 100)    # Channel 0, value 100
    adapter.SLEEP(50)            # Wait 50ms
    adapter.DAC_WRITE(1, 200)    # Channel 1, value 200
    adapter.SYNC_ROW(1)          # Sync marker
    adapter.DAC_WRITE(0, 0)      # Turn off channel 0
    
    print("Hardware operations:")
    print(adapter.get_operations_summary())
    
    print("\nGenerated source code:")
    print(adapter.get_source_code())

def demo_animated_sequence():
    """Demonstrate an animated sequence"""
    print("\n🎬 Demo 3: Animated Sequence")
    print("-" * 40)
    
    adapter.reset()
    
    # Animated bouncing box
    for frame in range(5):
        adapter.CLEAR(0, 10, 20)
        
        # Calculate position
        x = 50 + frame * 30
        y = 50 + abs((frame - 2) * 20)  # Bounce effect
        gray = 100 + frame * 30
        
        adapter.RECT(x, y, 40, 40, gray)
        adapter.TEXT(x + 5, y + 15, f"F{frame}", 255)
        adapter.COMMIT()
        
        if frame < 4:  # Don't sleep on last frame
            adapter.SLEEP(100)
    
    print(f"Animation: {len(adapter._global_adapter.operations)} operations")
    print(adapter.get_operations_summary())

def demo_python_execution():
    """Demonstrate executing Python code with the adapter"""
    print("\n🐍 Demo 4: Python Code Execution")
    print("-" * 40)
    
    # Define a Python program as a string
    python_program = '''
# Python program using adapter functions
adapter.reset()

# Draw a simple house
adapter.CLEAR(135, 206, 235)  # Sky blue background
adapter.RECT(100, 200, 200, 100, 139)  # House base (brown)
adapter.RECT(120, 220, 30, 60, 101)    # Door (dark brown)
adapter.RECT(250, 230, 40, 40, 173)    # Window (light blue)

# Roof (simplified as rectangle)
adapter.RECT(80, 150, 240, 50, 160)    # Roof (gray)

adapter.TEXT(110, 330, "MY HOUSE", 0)  # Label
adapter.COMMIT()

# Add some animation - blinking window
for i in range(3):
    adapter.RECT(250, 230, 40, 40, 255 if i % 2 else 173)  # Blink window
    adapter.COMMIT()
    adapter.sleep(200)
'''
    
    # Execute the program
    print("Executing Python program...")
    
    # Create execution context
    exec_globals = {
        'adapter': adapter,
        'RECT': adapter.RECT,
        'TEXT': adapter.TEXT,
        'CLEAR': adapter.CLEAR,
        'COMMIT': adapter.COMMIT,
        'SLEEP': adapter.SLEEP,
    }
    
    try:
        exec(python_program, exec_globals)
        print("✅ Execution successful!")
        print(adapter.get_operations_summary())
        
        # Show generated analog source
        print("\nEquivalent analog code:")
        analog_source = adapter.get_source_code()
        lines = analog_source.split('\n')
        for i, line in enumerate(lines[:15]):  # Show first 15 lines
            print(f"  {line}")
        if len(lines) > 15:
            print(f"  ... ({len(lines) - 15} more lines)")
            
    except Exception as e:
        print(f"❌ Execution failed: {e}")

def demo_workbench_integration():
    """Demonstrate integration with the workbench"""
    print("\n🛠️  Demo 5: Workbench Integration")
    print("-" * 40)
    print("Starting Analog Code Workbench...")
    print("Features available:")
    print("  • Manual code editing in Pane 1")
    print("  • Tile visualization in Pane 2") 
    print("  • CSV editing in Pane 3")
    print("  • Live results in Pane 4")
    print("  • Viewer Mode for VisualPython integration")
    print("\nInstructions:")
    print("  1. Run the workbench: python analog_code_workbench.py")
    print("  2. Toggle 'Viewer Mode' to enable VisualPython capture")
    print("  3. Click 'Run with VisualPython' to execute and capture")
    print("  4. Edit CSV in Pane 3 for manual tweaking")
    print("  5. Watch live results in Pane 4")

def main():
    """Run the complete demo sequence"""
    print("🚀 Integrated VisualPython + Analog Workbench Demo")
    print("=" * 60)
    print("This demo shows the complete pipeline from VisualPython")
    print("code to analog-executable tiles and CSV operations.")
    print("=" * 60)
    
    # Run all demos
    demo_basic_capture()
    demo_hardware_control()
    demo_animated_sequence()
    demo_python_execution()
    demo_workbench_integration()
    
    print("\n" + "=" * 60)
    print("🎯 Demo Complete!")
    print("Ready for real VisualPython integration!")
    print("\nNext steps:")
    print("  • Connect to your existing VisualPython viewer")
    print("  • Test with real analog hardware (DAC/ADC)")
    print("  • Expand the opcode set for more operations")
    print("  • Add error correction to tile encoding")
    print("=" * 60)

if __name__ == "__main__":
    main()