#!/usr/bin/env python3
"""
Test script to verify the integrated simulator backend works with VisualPython.

This tests the direct Python-to-pixels pipeline using the headless simulator.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path so we can import VisualPython
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from visualpython.core import VisualPythonEngine
    from visualpython.backends import create_backend
    print("✅ Successfully imported VisualPython core modules")
except ImportError as e:
    print(f"❌ Failed to import VisualPython modules: {e}")
    sys.exit(1)


def test_simulator_backend_creation():
    """Test that we can create a simulator backend"""
    print("\n🧪 Testing simulator backend creation...")
    
    try:
        backend = create_backend('simulator', width=400, height=300, out_dir='test_frames')
        print("✅ Successfully created simulator backend")
        return backend
    except Exception as e:
        print(f"❌ Failed to create simulator backend: {e}")
        return None


def test_visual_python_with_simulator():
    """Test VisualPython engine with simulator backend"""
    print("\n🧪 Testing VisualPython engine with simulator...")
    
    try:
        # Create engine with simulator backend
        engine = VisualPythonEngine(
            backend='simulator',
            width=600,
            height=400,
            out_dir='vp_test_frames'
        )
        print("✅ Successfully created VisualPython engine with simulator")
        
        # Test simple code execution
        test_code = """
# Simple variable assignment
x = 42
y = x * 2
result = x + y

# Print statement
print("Hello from VisualPython!")
"""
        
        print("\n🔥 Executing test code...")
        execution_time = engine.execute(test_code)
        print(f"✅ Code executed in {execution_time:.2f}ms")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to test VisualPython with simulator: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_direct_draw_api():
    """Test the direct draw API through the simulator"""
    print("\n🧪 Testing direct draw API...")
    
    try:
        # Create a simulator backend directly
        backend = create_backend('simulator', width=400, height=300, out_dir='draw_test_frames')
        
        # Test direct rendering
        from visualpython.core import VisualElement
        
        elements = [
            VisualElement('output', 'Direct API Test', 50, 50, '#00ff88'),
            VisualElement('variable', 'test_var = 123', 50, 80, '#88ffff'),
            VisualElement('variable_bar', '', 50, 110, '#ffff00', {'bar_width': 100, 'value': 123})
        ]
        
        backend.render_elements(elements)
        print("✅ Successfully rendered elements with simulator")
        
        # Clean up
        backend.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Failed to test direct draw API: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("🚀 Testing VisualPython Simulator Integration")
    print("=" * 50)
    
    tests = [
        test_simulator_backend_creation,
        test_visual_python_with_simulator,
        test_direct_draw_api
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! The simulator integration is working perfectly.")
        print("\nFrame images saved to:")
        print("  - test_frames/")
        print("  - vp_test_frames/") 
        print("  - draw_test_frames/")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)