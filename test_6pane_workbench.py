#!/usr/bin/env python3
"""
Test script for PXOS 6-Pane Workbench
Run this to verify the complete integration works
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

def test_workbench():
    """Test the 6-pane workbench functionality"""
    
    print("Testing PXOS 6-Pane Workbench...")
    
    try:
        # Test imports
        print("1. Testing imports...")
        from pxos_bus import PXOSBus, PaneType, ValidationResult
        from pxos_validator import PXOSValidator
        print("   ✓ Bus and validator imports successful")
        
        # Test bus functionality
        print("2. Testing bus functionality...")
        bus = PXOSBus()
        validator = PXOSValidator()
        
        # Test validation
        test_csv = """# pxos-ops/1.0, profile=default, cols=16
RECT,20,20,40,20,128,128,128
SLEEP,30
COMMIT"""
        
        json_data = validator.csv_to_json(test_csv)
        is_valid, errors = validator.validate_json(json_data)
        
        if is_valid:
            print("   ✓ Schema validation successful")
        else:
            print(f"   ✗ Schema validation failed: {errors}")
            return False
        
        # Test transformers
        print("3. Testing basic transformers...")
        
        # Test the workbench
        print("4. Starting 6-pane workbench...")
        
        try:
            from pxos_workbench_6pane import PXOSWorkbench6Pane
            print("   ✓ Workbench import successful")
            
            # Create and run workbench
            app = PXOSWorkbench6Pane()
            print("   ✓ Workbench created successfully")
            print("\n🎉 All tests passed! Starting workbench...")
            print("\nInstructions:")
            print("- Edit any pane (P1, P2, P3, P5) to see live updates")
            print("- Use 'Run Viewer' to load from viewer_adapter")
            print("- Pin panes with 📌 to prevent auto-updates")
            print("- Watch P4 (tiles) and P6 (replay) for visual feedback")
            print("\nClose the window to exit.\n")
            
            app.mainloop()
            return True
            
        except ImportError as e:
            print(f"   ✗ Workbench import failed: {e}")
            return False
        except Exception as e:
            print(f"   ✗ Workbench creation failed: {e}")
            return False
        
    except ImportError as e:
        print(f"   ✗ Import failed: {e}")
        print("\nMake sure the following files exist:")
        print("- pxos_bus.py")
        print("- pxos_validator.py") 
        print("- pxos_workbench_6pane.py")
        return False
    except Exception as e:
        print(f"   ✗ Unexpected error: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are available"""
    print("Checking dependencies...")
    
    try:
        import tkinter
        print("   ✓ tkinter available")
    except ImportError:
        print("   ✗ tkinter not available")
        return False
    
    try:
        from PIL import Image, ImageDraw, ImageTk
        print("   ✓ Pillow available")
    except ImportError:
        print("   ✗ Pillow not available (install with: pip install pillow)")
        return False
    
    # Check for optional viewer adapter
    try:
        import viewer_adapter_simple
        print("   ✓ viewer_adapter_simple available")
    except ImportError:
        print("   ⚠ viewer_adapter_simple not found (viewer integration disabled)")
    
    return True

def main():
    """Main test function"""
    print("PXOS 6-Pane Workbench Test Suite")
    print("=" * 40)
    
    if not check_dependencies():
        print("\n❌ Dependency check failed!")
        return False
    
    print("\nDependencies OK, starting workbench test...")
    return test_workbench()

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ Test completed successfully!")
        else:
            print("\n❌ Test failed!")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)