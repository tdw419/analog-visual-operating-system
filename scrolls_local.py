#!/usr/bin/env python3
"""
Scrolls Local State Management
------------------------------
Handles the creation, reading, writing, and validation of the manifest.yaml file.
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

MANIFEST_FILENAME = "manifest.yaml"

def get_manifest_path() -> Path:
    """Returns the path to the manifest file in the current directory."""
    return Path.cwd() / MANIFEST_FILENAME

def init_manifest() -> bool:
    """
    Creates a new manifest.yaml file in the current directory if one doesn't exist.

    Returns:
        bool: True if the manifest was created, False if it already existed.
    """
    manifest_path = get_manifest_path()
    if manifest_path.exists():
        print(f"'{MANIFEST_FILENAME}' already exists.")
        return False

    default_manifest = {
        "version": "1.0",
        "project_name": "Untitled Scrolls Project",
        "files": {},
        "last_sync": None,
    }

    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            yaml.dump(default_manifest, f, default_flow_style=False, sort_keys=False)
        print(f"Initialized new '{MANIFEST_FILENAME}'.")
        return True
    except IOError as e:
        print(f"Error: Could not write to '{manifest_path}': {e}")
        return False

def read_manifest() -> Optional[Dict[str, Any]]:
    """
    Reads and parses the manifest.yaml file from the current directory.

    Returns:
        dict: The parsed manifest data, or None if the file doesn't exist or is invalid.
    """
    manifest_path = get_manifest_path()
    if not manifest_path.exists():
        print(f"Error: '{MANIFEST_FILENAME}' not found. Run 'scrolls init' to create one.")
        return None

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            # Use safe_load to prevent arbitrary code execution from YAML
            data = yaml.safe_load(f)
            if validate_manifest(data):
                return data
            else:
                print(f"Error: '{MANIFEST_FILENAME}' has an invalid structure.")
                return None
    except (IOError, yaml.YAMLError) as e:
        print(f"Error: Could not read or parse '{manifest_path}': {e}")
        return None

def write_manifest(data: Dict[str, Any]) -> bool:
    """
    Writes the given data to the manifest.yaml file.

    Args:
        data (dict): The data to write to the manifest.

    Returns:
        bool: True on success, False on failure.
    """
    manifest_path = get_manifest_path()
    if not validate_manifest(data):
        print("Error: Attempted to write invalid data to manifest.")
        return False

    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        return True
    except IOError as e:
        print(f"Error: Could not write to '{manifest_path}': {e}")
        return False

def validate_manifest(data: Dict[str, Any]) -> bool:
    """
    Validates the structure of the manifest data.

    Args:
        data (dict): The manifest data to validate.

    Returns:
        bool: True if the data is valid, False otherwise.
    """
    if not isinstance(data, dict):
        return False

    required_keys = ["version", "project_name", "files"]
    for key in required_keys:
        if key not in data:
            print(f"Validation Error: Missing required key '{key}'.")
            return False

    if not isinstance(data["files"], dict):
        print("Validation Error: 'files' key must be a dictionary.")
        return False

    return True

if __name__ == '__main__':
    # Example usage and self-test
    print("Running self-test for scrolls_local.py...")

    # Clean up previous test files if they exist
    if get_manifest_path().exists():
        get_manifest_path().unlink()

    # Test initialization
    assert init_manifest() is True, "Test failed: init_manifest should succeed on first run."
    assert get_manifest_path().exists(), "Test failed: manifest.yaml should exist after init."
    assert init_manifest() is False, "Test failed: init_manifest should fail if file exists."

    # Test reading
    manifest_data = read_manifest()
    assert manifest_data is not None, "Test failed: read_manifest should return data."
    assert manifest_data["project_name"] == "Untitled Scrolls Project", "Test failed: incorrect default project name."

    # Test writing
    manifest_data["project_name"] = "My Awesome Project"
    manifest_data["files"]["src/main.py"] = {
        "checksum": "abcde12345",
        "last_modified": "2025-08-13T18:00:00Z"
    }
    assert write_manifest(manifest_data) is True, "Test failed: write_manifest should succeed."

    # Test re-reading modified data
    updated_data = read_manifest()
    assert updated_data["project_name"] == "My Awesome Project", "Test failed: project name not updated."
    assert "src/main.py" in updated_data["files"], "Test failed: new file not added."
    assert updated_data["files"]["src/main.py"]["checksum"] == "abcde12345", "Test failed: checksum mismatch."

    # Test validation failure
    invalid_data = {"foo": "bar"}
    assert validate_manifest(invalid_data) is False, "Test failed: validation should fail for invalid data."
    assert write_manifest(invalid_data) is False, "Test failed: write_manifest should fail for invalid data."

    print("\nAll self-tests passed!")

    # Clean up the test file
    get_manifest_path().unlink()
