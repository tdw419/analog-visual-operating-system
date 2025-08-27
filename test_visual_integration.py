# test_visual_integration.py - Test the integration of visual diff components
import json
import tempfile
import os
from pathlib import Path
from hall_of_drift import DriftStorage, HallOfDriftController
from visual_diff_ui import TkJsonDiffPane, TkOverlayPane
from json_diff import compute_json_diff, compute_field_level_diff
from pixel_overlay import compute_pixel_overlay

def test_visual_components_integration():
    """Test that all visual components integrate correctly"""
    print("Testing visual components integration...")
    
    # Test JSON diff computation
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
    
    # Test JSON diff
    diff_result = compute_json_diff(canonical, drifted)
    assert len(diff_result) > 0, "Expected JSON diff to find differences"
    print("✅ JSON diff computation works")
    
    # Test field-level diff
    field_diff = compute_field_level_diff(canonical, drifted)
    assert len(field_diff["modified_ops"]) > 0, "Expected field-level diff to find modified operations"
    print("✅ Field-level diff computation works")
    
    # Test pixel overlay
    overlay_img = compute_pixel_overlay(canonical, drifted)
    assert overlay_img is not None, "Expected pixel overlay to return an image"
    assert overlay_img.size == (256, 256), "Expected overlay to be 256x256 pixels"
    print("✅ Pixel overlay computation works")
    
    print("🎉 All visual components integration tests passed!")

def test_drift_storage_with_visual_components():
    """Test DriftStorage with visual components"""
    print("Testing DriftStorage with visual components...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = DriftStorage(Path(temp_dir))
        
        # Create sample drift data
        sample_dir = Path(temp_dir) / "drift_test_1"
        sample_dir.mkdir()
        
        canonical = {
            "schemaVersion": "pxos-ops/1.0",
            "program": [
                {"op": "RECT", "x": 10, "y": 10, "w": 50, "h": 50, "r": 255, "g": 0, "b": 0},
                {"op": "COMMIT"}
            ]
        }
        
        drifted = {
            "schemaVersion": "pxos-ops/1.0",
            "program": [
                {"op": "RECT", "x": 10, "y": 10, "w": 50, "h": 50, "r": 250, "g": 10, "b": 0},
                {"op": "COMMIT"}
            ]
        }
        
        # Write sample files
        with open(sample_dir / "canonical.json", "w") as f:
            json.dump(canonical, f, indent=2)
            
        with open(sample_dir / "drifted.json", "w") as f:
            json.dump(drifted, f, indent=2)
            
        with open(sample_dir / "path.txt", "w") as f:
            f.write("P1 -> P3 -> P5")
            
        with open(sample_dir / "seed.txt", "w") as f:
            f.write("99999")
        
        # Test listing scrolls
        scrolls = storage.list_scrolls()
        assert len(scrolls) == 1, "Expected to find one scroll"
        assert scrolls[0]["id"] == "drift_test_1", "Expected scroll ID to match"
        print("✅ DriftStorage can list scrolls")
        
        # Test loading scroll
        scroll = storage.load_scroll("drift_test_1")
        assert scroll["id"] == "drift_test_1", "Expected loaded scroll ID to match"
        assert "canonical" in scroll, "Expected loaded scroll to have canonical data"
        assert "drifted" in scroll, "Expected loaded scroll to have drifted data"
        print("✅ DriftStorage can load scrolls")
        
    print("🎉 DriftStorage with visual components tests passed!")

if __name__ == "__main__":
    test_visual_components_integration()
    test_drift_storage_with_visual_components()
    print("\n🎊 All integration tests passed!")