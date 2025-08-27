#!/usr/bin/env python3
"""
Demo script for PXOS 6-Pane Workbench
Demonstrates the complete round-trip translation with bulletproof data flow
"""

import sys
import os
import time
import traceback

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

def create_sample_viewer():
    """Create a sample viewer module for testing"""
    sample_viewer_code = '''# Sample viewer for PXOS demo
import viewer_adapter_simple as VA

def main():
    """Demo program showing various PXOS operations"""
    VA.reset()
    
    # Basic rectangle operations
    VA.RECT(20, 20, 40, 20, 128)
    VA.RECT(70, 70, 30, 30, 200)
    
    # Timing operations
    VA.SLEEP(30)
    
    # Hardware operations
    VA.DAC_WRITE(1, 180)
    
    # Analog operations (if supported)
    try:
        VA.INTEGRATE(0.1, 0, 1)
        VA.FILTER("lowpass", 1000, 1, 2)
    except AttributeError:
        pass  # Viewer might not support these yet
    
    VA.COMMIT()

if __name__ == "__main__":
    main()
'''
    
    with open('demo_viewer_main.py', 'w') as f:
        f.write(sample_viewer_code)
    
    print("Created demo_viewer_main.py")

def create_viewer_adapter():
    """Create viewer adapter if it doesn't exist"""
    adapter_code = '''# Simple viewer adapter for PXOS demo
ops = []

def reset():
    """Reset captured operations"""
    global ops
    ops = []

def RECT(x, y, w, h, gray):
    """Capture a rectangle operation"""
    g = int(gray)
    ops.append(f"RECT,{int(x)},{int(y)},{int(w)},{int(h)},{g},{g},{g}")

def SLEEP(ms):
    """Capture a sleep operation"""
    ops.append(f"SLEEP,{int(ms)}")

def DAC_WRITE(ch, val):
    """Capture a DAC write operation"""
    ops.append(f"DAC_WRITE,{int(ch)},{int(val)}")

def INTEGRATE(tau, src, dst):
    """Capture an integrate operation"""
    ops.append(f"INTEGRATE,{tau},{src},{dst}")

def FILTER(filter_type, fc, src, dst):
    """Capture a filter operation"""
    ops.append(f"FILTER,{filter_type},{fc},{src},{dst}")

def COMMIT():
    """Capture a commit operation"""
    ops.append("COMMIT")

def get_captured_csv():
    """Get captured operations as CSV"""
    return '\\n'.join(ops)

def get_ops_count():
    """Get number of captured operations"""
    return len(ops)
'''
    
    if not os.path.exists('viewer_adapter_simple.py'):
        with open('viewer_adapter_simple.py', 'w') as f:
            f.write(adapter_code)
        print("Created viewer_adapter_simple.py")

def test_bus_functionality():
    """Test the PXOS bus functionality independently"""
    print("\\n=== Testing PXOS Bus Functionality ===")
    
    try:
        from pxos_bus import PXOSBus, PaneType, setup_default_bus
        
        # Test basic bus setup
        bus = setup_default_bus()
        print("✓ Bus created successfully")
        
        # Test basic validation
        test_csv = """# pxos-ops/1.0, profile=default, cols=16
RECT,20,20,40,20,128,128,128
SLEEP,30
COMMIT"""
        
        # Test edit event
        result = bus.on_edit(PaneType.P5_HLIR, test_csv)
        print(f"✓ Edit processed: {result}")
        
        # Check build info
        build_info = bus.get_build_info()
        print(f"✓ Build info: {build_info}")
        
        return True
        
    except Exception as e:
        print(f"✗ Bus test failed: {e}")
        traceback.print_exc()
        return False

def test_validator_functionality():
    """Test the PXOS validator functionality"""
    print("\\n=== Testing PXOS Validator ===")
    
    try:
        from pxos_validator import PXOSValidator
        
        validator = PXOSValidator()
        print("✓ Validator created successfully")
        
        # Test CSV to JSON conversion
        test_csv = """# pxos-ops/1.0, profile=default, cols=16
RECT,20,20,40,20,128,128,128
SLEEP,30
DAC_WRITE,1,150
COMMIT"""
        
        json_data = validator.csv_to_json(test_csv)
        print("✓ CSV to JSON conversion successful")
        
        # Test validation
        is_valid, errors = validator.validate_json(json_data)
        if is_valid:
            print("✓ JSON validation successful")
        else:
            print(f"✗ Validation failed: {errors}")
            return False
        
        # Test reverse conversion
        csv_result = validator.json_to_csv(json_data)
        print("✓ JSON to CSV conversion successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Validator test failed: {e}")
        traceback.print_exc()
        return False

def demo_6pane_workbench():
    """Demonstrate the 6-pane workbench functionality"""
    print("\\n=== Starting 6-Pane Workbench Demo ===")
    
    try:
        # Set environment variable for demo viewer
        os.environ["ACW_VIEWER_MODULE"] = "demo_viewer_main"
        os.environ["ACW_VIEWER_FUNC"] = "main"
        
        # Import and run workbench
        from pxos_workbench_6pane import PXOSWorkbench6Pane
        
        print("✓ Workbench imported successfully")
        print("\\n🎉 Starting 6-Pane PXOS Workbench...")
        print("\\n📋 Demo Instructions:")
        print("1. Click 'Run Viewer' to load demo program")
        print("2. Edit any of the text panes (P1, P2, P3, P5) to see live updates")
        print("3. Watch P4 (tiles) and P6 (replay) for visual feedback")
        print("4. Use 📌 Pin buttons to lock panes from auto-updates")
        print("5. Observe how changes propagate through all panes")
        print("\\nFeatures demonstrated:")
        print("• Round-trip translation between Python and Analog DSL")
        print("• Schema validation with pxos-ops/1.0")
        print("• Real-time tile generation and replay")
        print("• Event-driven synchronization with conflict prevention")
        print("• Hardware simulation (DAC/ADC operations)")
        print("\\nClose the window to exit.\\n")
        
        # Create and run workbench
        app = PXOSWorkbench6Pane()
        app.mainloop()
        
        return True
        
    except Exception as e:
        print(f"✗ Workbench demo failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Main demo function"""
    print("PXOS 6-Pane Workbench Demo")
    print("=" * 50)
    
    # Check dependencies
    missing_deps = []
    
    try:
        import tkinter
        print("✓ tkinter available")
    except ImportError:
        missing_deps.append("tkinter")
    
    try:
        from PIL import Image, ImageDraw, ImageTk
        print("✓ Pillow available")
    except ImportError:
        missing_deps.append("pillow")
    
    if missing_deps:
        print(f"\\n❌ Missing dependencies: {', '.join(missing_deps)}")
        print("Install with: pip install pillow")
        return False
    
    # Create necessary files
    print("\\n=== Setting up demo environment ===")
    create_viewer_adapter()
    create_sample_viewer()
    
    # Test components
    all_tests_passed = True
    all_tests_passed &= test_bus_functionality()
    all_tests_passed &= test_validator_functionality()
    
    if not all_tests_passed:
        print("\\n❌ Some tests failed. Check the error messages above.")
        return False
    
    print("\\n✅ All component tests passed!")
    
    # Run main demo
    input("\\nPress Enter to start the 6-pane workbench demo...")
    return demo_6pane_workbench()

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\\n✅ Demo completed successfully!")
        else:
            print("\\n❌ Demo failed!")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\\n\\n⚠ Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\\n❌ Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)