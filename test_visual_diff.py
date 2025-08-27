# test_visual_diff.py
import json
from json_diff import compute_json_diff, compute_field_level_diff
from pixel_overlay import compute_pixel_overlay

def test_json_diff():
    """Test the JSON diff computation with a simple example"""
    canonical = {
        "schemaVersion": "pxos-ops/1.0",
        "program": [
            {"op": "RECT", "x": 10, "y": 20, "w": 30, "h": 40, "r": 255, "g": 0, "b": 0},
            {"op": "COMMIT"}
        ]
    }
    
    drifted = {
        "schemaVersion": "pxos-ops/1.0",
        "program": [
            {"op": "RECT", "x": 10, "y": 20, "w": 30, "h": 40, "r": 254, "g": 0, "b": 0},  # Slightly different 'r' value
            {"op": "COMMIT"}
        ]
    }

    diff = compute_json_diff(canonical, drifted)
    
    # Check that we have some differences
    assert len(diff) > 0, "Expected to find differences"
    
    # Check that we have both removed and added lines
    removed_lines = [line for line_type, line in diff if line_type == 'removed']
    added_lines = [line for line_type, line in diff if line_type == 'added']
    
    assert len(removed_lines) > 0, "Expected to find removed lines"
    assert len(added_lines) > 0, "Expected to find added lines"
    
    print("✅ JSON diff test passed")

def test_field_level_diff():
    """Test the field-level diff computation"""
    canonical = {
        "schemaVersion": "pxos-ops/1.0",
        "program": [
            {"op": "RECT", "x": 10, "y": 20, "w": 30, "h": 40, "r": 255, "g": 0, "b": 0},
            {"op": "COMMIT"}
        ]
    }
    
    drifted = {
        "schemaVersion": "pxos-ops/1.0",
        "program": [
            {"op": "RECT", "x": 10, "y": 20, "w": 30, "h": 40, "r": 254, "g": 0, "b": 0},  # Slightly different 'r' value
            {"op": "COMMIT"}
        ]
    }
    
    diff = compute_field_level_diff(canonical, drifted)
    
    # Check that we found modified operations
    assert len(diff["modified_ops"]) > 0, "Expected to find modified operations"
    
    # Check that the modification is correctly identified
    modified_op = diff["modified_ops"][0]
    assert modified_op["index"] == 0, "Expected modification at index 0"
    assert len(modified_op["differences"]) > 0, "Expected to find field differences"
    
    # Check that the 'r' field difference is correctly identified
    r_diff = [d for d in modified_op["differences"] if d["field"] == "r"]
    assert len(r_diff) > 0, "Expected to find difference in 'r' field"
    assert r_diff[0]["canonical"] == 255, "Expected canonical 'r' value to be 255"
    assert r_diff[0]["current"] == 254, "Expected current 'r' value to be 254"
    
    print("✅ Field-level diff test passed")

def test_pixel_overlay():
    """Test the pixel overlay computation"""
    canonical = {
        "schemaVersion": "pxos-ops/1.0",
        "program": [
            {"op": "RECT", "x": 10, "y": 10, "w": 20, "h": 20, "r": 255, "g": 0, "b": 0}
        ]
    }
    
    drifted = {
        "schemaVersion": "pxos-ops/1.0",
        "program": [
            {"op": "RECT", "x": 10, "y": 10, "w": 20, "h": 20, "r": 254, "g": 0, "b": 0}
        ]
    }

    overlay = compute_pixel_overlay(canonical, drifted)
    
    # Check that we got an image back
    assert overlay is not None, "Expected to get an overlay image"
    assert overlay.size == (256, 256), "Expected overlay to be 256x256 pixels"
    
    print("✅ Pixel overlay test passed")

if __name__ == "__main__":
    test_json_diff()
    test_field_level_diff()
    test_pixel_overlay()
    print("🎉 All visual diff tests passed!")