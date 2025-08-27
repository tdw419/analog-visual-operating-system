# tests/test_reverse_pretty.py
from hlir_to_py import hlir_to_python
from transpiler import T_py_to_hlir

def test_rect_roundtrip_minimal():
    h = {"schemaVersion":"pxos-ops/1.0","program":[{"op":"RECT","x":1,"y":2,"w":3,"h":4,"r":5,"g":5,"b":5},{"op":"COMMIT"}]}
    py = hlir_to_python(h, alias="VA")
    h2 = T_py_to_hlir(py)
    assert h2["program"][0]["op"] == "RECT"
    assert h2["program"][1]["op"] == "COMMIT"
    print("✅ RECT round-trip test passed")

def test_complex_roundtrip():
    """Test round-trip with multiple operations"""
    h = {
        "schemaVersion": "pxos-ops/1.0",
        "program": [
            {"op": "RECT", "x": 20, "y": 20, "w": 40, "h": 20, "r": 64, "g": 64, "b": 64},
            {"op": "SLEEP", "ms": 30},
            {"op": "DAC_WRITE", "ch": 1, "val": 180},
            {"op": "COMMIT"}
        ]
    }
    
    # HLIR → Python
    py = hlir_to_python(h, alias="VA")
    print(f"Generated Python:\n{py}")
    
    # Python → HLIR
    h2 = T_py_to_hlir(py)
    
    # Verify structure preservation
    assert h2["schemaVersion"] == "pxos-ops/1.0"
    assert len(h2["program"]) == 4
    assert h2["program"][0]["op"] == "RECT"
    assert h2["program"][1]["op"] == "SLEEP"
    assert h2["program"][2]["op"] == "DAC_WRITE"
    assert h2["program"][3]["op"] == "COMMIT"
    
    # Verify parameter preservation
    assert h2["program"][0]["x"] == 20
    assert h2["program"][1]["ms"] == 30
    assert h2["program"][2]["ch"] == 1
    assert h2["program"][2]["val"] == 180
    
    print("✅ Complex round-trip test passed")

def test_schema_validation():
    """Test that schema validation works correctly"""
    from validate_hlir import validate_hlir, ValidationError
    
    # Valid HLIR should pass
    valid_hlir = {
        "schemaVersion": "pxos-ops/1.0",
        "program": [
            {"op": "RECT", "x": 0, "y": 0, "w": 10, "h": 10, "r": 255, "g": 255, "b": 255}
        ]
    }
    
    try:
        validate_hlir(valid_hlir)
        print("✅ Schema validation test passed")
    except ValidationError:
        assert False, "Valid HLIR should not raise ValidationError"
    
    # Invalid HLIR should fail
    invalid_hlir = {
        "schemaVersion": "pxos-ops/1.0",
        "program": [
            {"op": "RECT"}  # Missing required fields
        ]
    }
    
    try:
        validate_hlir(invalid_hlir)
        assert False, "Invalid HLIR should raise ValidationError"
    except ValidationError:
        print("✅ Schema validation rejection test passed")

if __name__ == "__main__":
    test_rect_roundtrip_minimal()
    test_complex_roundtrip()
    test_schema_validation()
    print("\n🎉 All round-trip tests passed! System is ready to ship.")