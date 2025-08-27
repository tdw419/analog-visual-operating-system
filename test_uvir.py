#!/usr/bin/env python3
"""
UVIR System Test Script

This script tests the UVIR system components to ensure everything works correctly.
It can run without dependencies for basic validation.
"""

import json
import sys
import os
import asyncio
from pathlib import Path

def test_imports():
    """Test if all dependencies are available"""
    print("🧪 Testing imports...")
    
    results = {}
    
    # Test FastAPI
    try:
        import fastapi
        results['fastapi'] = f"✓ {fastapi.__version__}"
    except ImportError:
        results['fastapi'] = "✗ Missing (pip install fastapi)"
    
    # Test pydantic
    try:
        import pydantic
        results['pydantic'] = f"✓ {pydantic.__version__}"
    except ImportError:
        results['pydantic'] = "✗ Missing (pip install pydantic)"
    
    # Test pyserial
    try:
        import serial
        results['pyserial'] = f"✓ {serial.__version__}"
    except ImportError:
        results['pyserial'] = "✗ Missing (pip install pyserial)"
    
    # Test json-repair
    try:
        import json_repair
        results['json-repair'] = "✓ Available"
    except ImportError:
        results['json-repair'] = "✗ Missing (pip install json-repair)"
    
    # Test llama-cpp-python (optional)
    try:
        import llama_cpp
        results['llama-cpp-python'] = f"✓ {llama_cpp.__version__}"
    except ImportError:
        results['llama-cpp-python'] = "○ Optional (pip install llama-cpp-python)"
    
    print("\nDependency Status:")
    for package, status in results.items():
        print(f"  {package}: {status}")
    
    return results

def test_uvir_validation():
    """Test UVIR operation validation"""
    print("\n🧪 Testing UVIR validation...")
    
    # Import our validation function
    sys.path.append(str(Path(__file__).parent))
    try:
        from uvir_server import validate_uvir_ops
    except ImportError as e:
        print(f"✗ Cannot import uvir_server: {e}")
        return False
    
    # Test valid operations
    valid_ops = [
        {"op": "TEXT", "x": 100, "y": 50, "text": "Hello UVIR", "color": "#00FF00"},
        {"op": "BAR", "x": 50, "y": 100, "len": 200, "label": "Progress", "value": 0.75},
        {"op": "RECT", "x": 10, "y": 10, "w": 100, "h": 60, "color": "#00FFFF", "fill": False},
        {"op": "LINK", "x1": 50, "y1": 50, "x2": 150, "y2": 150, "arrow": True},
        {"op": "TICK", "t": 5}
    ]
    
    validated = validate_uvir_ops(valid_ops)
    if len(validated) == len(valid_ops):
        print("✓ Valid operations passed validation")
    else:
        print(f"✗ Validation failed: {len(validated)}/{len(valid_ops)} operations")
        return False
    
    # Test invalid operations (should be filtered out)
    invalid_ops = [
        {"op": "INVALID", "x": 100, "y": 50},  # Invalid op
        {"not_an_op": True},  # Missing op field
        {"op": "TEXT", "x": 9999, "y": 50, "text": "Out of bounds"},  # Out of bounds
    ]
    
    validated_invalid = validate_uvir_ops(invalid_ops)
    if len(validated_invalid) == 0:
        print("✓ Invalid operations correctly filtered")
    else:
        print(f"✗ Invalid operations not filtered: {len(validated_invalid)} passed")
        return False
    
    return True

def test_serial_simulation():
    """Test serial communication simulation"""
    print("\n🧪 Testing serial simulation...")
    
    # Test tool call structure
    tool_call = {
        "type": "tool_call",
        "run_id": "test_123",
        "name": "serial_pwm",
        "args": {"pin": 13, "value": 128}
    }
    
    # Validate structure
    required_fields = ["type", "run_id", "name", "args"]
    for field in required_fields:
        if field not in tool_call:
            print(f"✗ Missing field: {field}")
            return False
    
    # Validate args
    if "pin" not in tool_call["args"] or "value" not in tool_call["args"]:
        print("✗ Missing pin or value in args")
        return False
    
    pin = tool_call["args"]["pin"]
    value = tool_call["args"]["value"]
    
    if not (0 <= pin <= 13):
        print(f"✗ Invalid pin: {pin}")
        return False
    
    if not (0 <= value <= 255):
        print(f"✗ Invalid value: {value}")
        return False
    
    print("✓ Tool call structure validation passed")
    print(f"✓ Hardware command: PWM Pin {pin} = {value}")
    
    return True

def test_frontend_files():
    """Test if frontend files exist and are valid"""
    print("\n🧪 Testing frontend files...")
    
    base_path = Path(__file__).parent
    
    # Check required files
    required_files = [
        "uvir_frontend.html",
        "uvir_server.py",
        "requirements-uvir.txt",
        "README-UVIR.md"
    ]
    
    for file_name in required_files:
        file_path = base_path / file_name
        if file_path.exists():
            print(f"✓ {file_name} exists ({file_path.stat().st_size} bytes)")
        else:
            print(f"✗ {file_name} missing")
            return False
    
    # Test HTML file for key elements
    html_file = base_path / "uvir_frontend.html"
    html_content = html_file.read_text()
    
    key_elements = [
        "UVIRRenderer",
        "generateUVIR",
        "handleUVIREvent", 
        "tool_call",
        "testHardware"
    ]
    
    for element in key_elements:
        if element in html_content:
            print(f"✓ Frontend contains {element}")
        else:
            print(f"✗ Frontend missing {element}")
            return False
    
    return True

async def test_mock_generation():
    """Test mock LLM generation"""
    print("\n🧪 Testing mock generation...")
    
    try:
        from uvir_server import mock_generation
    except ImportError as e:
        print(f"✗ Cannot import mock_generation: {e}")
        return False
    
    events = []
    async for event in mock_generation("Test prompt", "test_run"):
        events.append(event)
    
    # Check we got the expected event types
    event_types = [event["type"] for event in events]
    expected_types = ["token", "ir", "ir_summary", "done"]
    
    for expected_type in expected_types:
        if expected_type in event_types:
            print(f"✓ Generated {expected_type} events")
        else:
            print(f"✗ Missing {expected_type} events")
            return False
    
    print(f"✓ Generated {len(events)} total events")
    return True

def main():
    """Run all tests"""
    print("🚀 UVIR System Test Suite")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_uvir_validation, 
        test_serial_simulation,
        test_frontend_files,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)
    
    # Run async test
    try:
        result = asyncio.run(test_mock_generation())
        results.append(result)
    except Exception as e:
        print(f"✗ Mock generation test failed: {e}")
        results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Test Results")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        print("\n✅ Your UVIR system is ready to use!")
        print("\nNext steps:")
        print("1. pip install -r requirements-uvir.txt")
        print("2. python uvir_server.py")
        print("3. python -m http.server 8080")
        print("4. Open http://localhost:8080/uvir_frontend.html")
        return 0
    else:
        print(f"❌ {total - passed} tests failed ({passed}/{total} passed)")
        print("\n🔧 Please fix the issues above and run tests again.")
        return 1

if __name__ == "__main__":
    sys.exit(main())