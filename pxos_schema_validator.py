#!/usr/bin/env python3
"""
JSON Schema validator for pxos-ops/1.0 HLIR format
Ensures all HLIR operations comply with the canonical schema
"""

import json
from typing import Dict, Any
try:
    import jsonschema
except ImportError:
    print("Warning: jsonschema not installed. Install with: pip install jsonschema")
    jsonschema = None

from pxos_sync_engine_enhanced import ValidationError

# Canonical pxos-ops/1.0 JSON Schema
PXOS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://pxos.io/schema/ops/1.0",
    "title": "PXOS Operations Schema v1.0",
    "description": "Schema for PXOS High-Level Intermediate Representation (HLIR)",
    "type": "object",
    "properties": {
        "schemaVersion": {
            "type": "string",
            "const": "pxos-ops/1.0",
            "description": "Schema version identifier"
        },
        "meta": {
            "type": "object",
            "properties": {
                "profile": {
                    "type": "string",
                    "default": "default",
                    "description": "Hardware profile name"
                },
                "cols": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 256,
                    "default": 16,
                    "description": "Number of columns in tile grid"
                },
                "rows": {
                    "type": "integer", 
                    "minimum": 1,
                    "maximum": 256,
                    "description": "Number of rows in tile grid"
                },
                "page": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Memory page number"
                }
            },
            "required": ["profile"],
            "additionalProperties": True
        },
        "program": {
            "type": "array",
            "description": "Array of PXOS operations",
            "items": {
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "op": {"const": "COMMIT"}
                        },
                        "required": ["op"],
                        "additionalProperties": False,
                        "description": "Commit/flush operation"
                    },
                    {
                        "type": "object", 
                        "properties": {
                            "op": {"const": "SLEEP"},
                            "ms": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 60000,
                                "description": "Sleep duration in milliseconds"
                            }
                        },
                        "required": ["op", "ms"],
                        "additionalProperties": False,
                        "description": "Sleep/delay operation"
                    },
                    {
                        "type": "object",
                        "properties": {
                            "op": {"const": "RECT"},
                            "x": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 255,
                                "description": "Rectangle X coordinate"
                            },
                            "y": {
                                "type": "integer", 
                                "minimum": 0,
                                "maximum": 255,
                                "description": "Rectangle Y coordinate"
                            },
                            "w": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 255,
                                "description": "Rectangle width"
                            },
                            "h": {
                                "type": "integer",
                                "minimum": 0, 
                                "maximum": 255,
                                "description": "Rectangle height"
                            },
                            "r": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 255,
                                "description": "Red color component"
                            },
                            "g": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 255,
                                "description": "Green color component"
                            },
                            "b": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 255,
                                "description": "Blue color component"
                            }
                        },
                        "required": ["op", "x", "y", "w", "h", "r", "g", "b"],
                        "additionalProperties": False,
                        "description": "Draw rectangle operation"
                    },
                    {
                        "type": "object",
                        "properties": {
                            "op": {"const": "DAC_WRITE"},
                            "ch": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 7,
                                "description": "DAC channel number"
                            },
                            "val": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 255,
                                "description": "DAC output value"
                            }
                        },
                        "required": ["op", "ch", "val"],
                        "additionalProperties": False,
                        "description": "Write to DAC output"
                    },
                    {
                        "type": "object",
                        "properties": {
                            "op": {"const": "INTEGRATE"},
                            "tau": {
                                "type": "number",
                                "minimum": 0.001,
                                "maximum": 10.0,
                                "description": "Integration time constant"
                            },
                            "src": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 7,
                                "description": "Source channel"
                            },
                            "dst": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 7,
                                "description": "Destination channel"
                            }
                        },
                        "required": ["op", "tau", "src", "dst"],
                        "additionalProperties": False,
                        "description": "Analog integration operation"
                    },
                    {
                        "type": "object",
                        "properties": {
                            "op": {"const": "FILTER"},
                            "type": {
                                "type": "string",
                                "enum": ["lowpass", "highpass", "bandpass", "bandstop"],
                                "description": "Filter type"
                            },
                            "fc": {
                                "type": "number",
                                "minimum": 0.1,
                                "maximum": 20000.0,
                                "description": "Cutoff frequency in Hz"
                            },
                            "src": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 7,
                                "description": "Source channel"
                            },
                            "dst": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 7,
                                "description": "Destination channel"
                            }
                        },
                        "required": ["op", "type", "fc", "src", "dst"],
                        "additionalProperties": False,
                        "description": "Analog filter operation"
                    },
                    {
                        "type": "object",
                        "properties": {
                            "op": {"const": "MULTIPLY"},
                            "gain": {
                                "type": "number",
                                "minimum": -100.0,
                                "maximum": 100.0,
                                "description": "Multiplication gain factor"
                            },
                            "src": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 7,
                                "description": "Source channel"
                            },
                            "dst": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 7,
                                "description": "Destination channel"
                            }
                        },
                        "required": ["op", "gain", "src", "dst"],
                        "additionalProperties": False,
                        "description": "Analog multiplication operation"
                    },
                    {
                        "type": "object",
                        "properties": {
                            "op": {"const": "SUM"},
                            "inputs": {
                                "type": "array",
                                "items": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": 7
                                },
                                "minItems": 1,
                                "maxItems": 8,
                                "description": "Input channel array"
                            },
                            "output": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 7,
                                "description": "Output channel"
                            }
                        },
                        "required": ["op", "inputs", "output"],
                        "additionalProperties": False,
                        "description": "Analog summation operation"
                    },
                    {
                        "type": "object",
                        "properties": {
                            "op": {"const": "SYNC_ROW"},
                            "i": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 255,
                                "description": "Row index to synchronize"
                            }
                        },
                        "required": ["op", "i"],
                        "additionalProperties": False,
                        "description": "Row synchronization operation"
                    }
                ]
            }
        }
    },
    "required": ["schemaVersion", "program"],
    "additionalProperties": False
}

def validate_hlir(hlir: Dict[str, Any]) -> None:
    """
    Validate HLIR against the pxos-ops/1.0 schema.
    
    Args:
        hlir: HLIR dictionary to validate
        
    Raises:
        ValidationError: If the HLIR doesn't conform to the schema
    """
    if not jsonschema:
        # Fallback validation without jsonschema
        _basic_validation(hlir)
        return
    
    try:
        jsonschema.validate(instance=hlir, schema=PXOS_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValidationError(f"Schema validation failed: {e.message}")
    except jsonschema.SchemaError as e:
        raise ValidationError(f"Schema error: {e.message}")

def _basic_validation(hlir: Dict[str, Any]) -> None:
    """
    Basic validation without jsonschema dependency.
    
    Args:
        hlir: HLIR dictionary to validate
        
    Raises:
        ValidationError: If basic validation fails
    """
    # Check required fields
    if not isinstance(hlir, dict):
        raise ValidationError("HLIR must be a dictionary")
    
    if "schemaVersion" not in hlir:
        raise ValidationError("Missing required field: schemaVersion")
    
    if hlir["schemaVersion"] != "pxos-ops/1.0":
        raise ValidationError(f"Invalid schema version: {hlir['schemaVersion']}")
    
    if "program" not in hlir:
        raise ValidationError("Missing required field: program")
    
    if not isinstance(hlir["program"], list):
        raise ValidationError("Program must be an array")
    
    # Validate each operation
    for i, op in enumerate(hlir["program"]):
        if not isinstance(op, dict):
            raise ValidationError(f"Operation {i} must be a dictionary")
        
        if "op" not in op:
            raise ValidationError(f"Operation {i} missing 'op' field")
        
        op_type = op["op"]
        
        # Basic validation for each operation type
        if op_type == "RECT":
            required = ["x", "y", "w", "h", "r", "g", "b"]
            for field in required:
                if field not in op:
                    raise ValidationError(f"RECT operation {i} missing field: {field}")
                if not isinstance(op[field], int) or not (0 <= op[field] <= 255):
                    raise ValidationError(f"RECT operation {i} field {field} must be int 0-255")
        
        elif op_type == "DAC_WRITE":
            if "ch" not in op or not isinstance(op["ch"], int) or not (0 <= op["ch"] <= 7):
                raise ValidationError(f"DAC_WRITE operation {i} invalid channel")
            if "val" not in op or not isinstance(op["val"], int) or not (0 <= op["val"] <= 255):
                raise ValidationError(f"DAC_WRITE operation {i} invalid value")
        
        elif op_type == "SLEEP":
            if "ms" not in op or not isinstance(op["ms"], int) or op["ms"] < 0:
                raise ValidationError(f"SLEEP operation {i} invalid milliseconds")
        
        elif op_type == "COMMIT":
            # COMMIT has no additional fields to validate
            pass
        
        else:
            # For extended operations, just check they exist
            if op_type not in ["INTEGRATE", "FILTER", "MULTIPLY", "SUM", "SYNC_ROW"]:
                raise ValidationError(f"Unknown operation type: {op_type}")

def export_schema() -> Dict[str, Any]:
    """
    Export the pxos-ops/1.0 schema for external use.
    
    Returns:
        The complete JSON schema dictionary
    """
    return PXOS_SCHEMA

if __name__ == "__main__":
    # Test the validator
    test_hlir = {
        "schemaVersion": "pxos-ops/1.0",
        "meta": {
            "profile": "default",
            "cols": 16
        },
        "program": [
            {"op": "RECT", "x": 20, "y": 20, "w": 40, "h": 20, "r": 64, "g": 64, "b": 64},
            {"op": "SLEEP", "ms": 30},
            {"op": "DAC_WRITE", "ch": 1, "val": 180},
            {"op": "COMMIT"}
        ]
    }
    
    try:
        validate_hlir(test_hlir)
        print("✅ Validation passed")
        print(json.dumps(test_hlir, indent=2))
    except ValidationError as e:
        print(f"❌ Validation failed: {e}")