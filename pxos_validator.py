# pxos_validator.py
"""
PXOS Schema Validator and Converter
Implements the formal PXOS-ops/1.0 specification with JSON Schema validation
"""

import json
import re
from typing import Dict, List, Any, Tuple, Optional

# PXOS Schema Definition (JSON Schema Draft 2020-12 compatible)
PXOS_SCHEMA = {
    "$schema": "http://json-schema.org/draft/2020-12/schema",
    "$id": "https://pxos.io/schema/ops/1.0",
    "title": "PXOS Operations Schema v1.0",
    "description": "Schema for PXOS analog execution operations",
    "type": "object",
    "required": ["schemaVersion", "program"],
    "properties": {
        "schemaVersion": {
            "type": "string",
            "pattern": "^pxos-ops/1\\.0$",
            "description": "Schema version identifier"
        },
        "meta": {
            "type": "object",
            "properties": {
                "profile": {"type": "string", "default": "default"},
                "cols": {"type": "integer", "minimum": 1, "maximum": 64, "default": 16},
                "rows": {"type": "integer", "minimum": 1, "maximum": 64},
                "page": {"type": "integer", "minimum": 0, "default": 0},
                "pageCount": {"type": "integer", "minimum": 1},
                "nextPageHint": {"type": "string"}
            },
            "additionalProperties": True
        },
        "program": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["op"],
                "properties": {
                    "op": {
                        "type": "string",
                        "enum": [
                            "NOP", "COMMIT", "SLEEP", "SYNC_ROW", "SYNC_PAGE",
                            "RECT", "LINE", "TEXT", "SET_GRAY", "MOVE_X", "MOVE_Y",
                            "SET_W", "SET_H", "DAC_WRITE", "ADC_READ", 
                            "FILTER", "INTEGRATE", "MIX", "MULTIPLY", "SUM",
                            "LABEL", "JUMP", "JUMP_IF_ZERO", "LOG", "META"
                        ]
                    }
                },
                "oneOf": [
                    # Basic operations
                    {
                        "properties": {"op": {"const": "NOP"}},
                        "additionalProperties": False
                    },
                    {
                        "properties": {"op": {"const": "COMMIT"}},
                        "additionalProperties": False
                    },
                    {
                        "properties": {
                            "op": {"const": "SLEEP"},
                            "ms": {"type": "integer", "minimum": 0, "maximum": 65535}
                        },
                        "required": ["op", "ms"],
                        "additionalProperties": False
                    },
                    {
                        "properties": {
                            "op": {"const": "SYNC_ROW"},
                            "i": {"type": "integer", "minimum": 0, "maximum": 255}
                        },
                        "required": ["op", "i"],
                        "additionalProperties": False
                    },
                    {
                        "properties": {
                            "op": {"const": "SYNC_PAGE"},
                            "i": {"type": "integer", "minimum": 0, "maximum": 255}
                        },
                        "required": ["op", "i"],
                        "additionalProperties": False
                    },
                    
                    # Graphics operations
                    {
                        "properties": {
                            "op": {"const": "RECT"},
                            "x": {"type": "integer", "minimum": 0, "maximum": 255},
                            "y": {"type": "integer", "minimum": 0, "maximum": 255},
                            "w": {"type": "integer", "minimum": 0, "maximum": 255},
                            "h": {"type": "integer", "minimum": 0, "maximum": 255},
                            "r": {"type": "integer", "minimum": 0, "maximum": 255},
                            "g": {"type": "integer", "minimum": 0, "maximum": 255},
                            "b": {"type": "integer", "minimum": 0, "maximum": 255}
                        },
                        "required": ["op", "x", "y", "w", "h", "r", "g", "b"],
                        "additionalProperties": False
                    },
                    {
                        "properties": {
                            "op": {"const": "LINE"},
                            "x1": {"type": "integer", "minimum": 0, "maximum": 255},
                            "y1": {"type": "integer", "minimum": 0, "maximum": 255},
                            "x2": {"type": "integer", "minimum": 0, "maximum": 255},
                            "y2": {"type": "integer", "minimum": 0, "maximum": 255},
                            "gray": {"type": "integer", "minimum": 0, "maximum": 255}
                        },
                        "required": ["op", "x1", "y1", "x2", "y2", "gray"],
                        "additionalProperties": False
                    },
                    {
                        "properties": {
                            "op": {"const": "TEXT"},
                            "x": {"type": "integer", "minimum": 0, "maximum": 255},
                            "y": {"type": "integer", "minimum": 0, "maximum": 255},
                            "text": {"type": "string", "maxLength": 256},
                            "gray": {"type": "integer", "minimum": 0, "maximum": 255}
                        },
                        "required": ["op", "x", "y", "text", "gray"],
                        "additionalProperties": False
                    },
                    
                    # State operations
                    {
                        "properties": {
                            "op": {"const": "SET_GRAY"},
                            "gray": {"type": "integer", "minimum": 0, "maximum": 255}
                        },
                        "required": ["op", "gray"],
                        "additionalProperties": False
                    },
                    {
                        "properties": {
                            "op": {"const": "MOVE_X"},
                            "dx": {"type": "integer", "minimum": -128, "maximum": 127}
                        },
                        "required": ["op", "dx"],
                        "additionalProperties": False
                    },
                    {
                        "properties": {
                            "op": {"const": "MOVE_Y"},
                            "dy": {"type": "integer", "minimum": -128, "maximum": 127}
                        },
                        "required": ["op", "dy"],
                        "additionalProperties": False
                    },
                    
                    # Hardware operations
                    {
                        "properties": {
                            "op": {"const": "DAC_WRITE"},
                            "ch": {"type": "integer", "minimum": 0, "maximum": 7},
                            "val": {"type": "integer", "minimum": 0, "maximum": 255}
                        },
                        "required": ["op", "ch", "val"],
                        "additionalProperties": False
                    },
                    {
                        "properties": {
                            "op": {"const": "ADC_READ"},
                            "ch": {"type": "integer", "minimum": 0, "maximum": 7},
                            "dst": {"type": "string"}
                        },
                        "required": ["op", "ch"],
                        "additionalProperties": False
                    },
                    
                    # Analog operations
                    {
                        "properties": {
                            "op": {"const": "FILTER"},
                            "type": {"type": "string", "enum": ["lowpass", "highpass", "bandpass", "notch"]},
                            "fc": {"type": "integer", "minimum": 0, "maximum": 65535},
                            "src": {"type": "integer", "minimum": 0, "maximum": 7},
                            "dst": {"type": "integer", "minimum": 0, "maximum": 7}
                        },
                        "required": ["op", "type", "fc", "src", "dst"],
                        "additionalProperties": False
                    },
                    {
                        "properties": {
                            "op": {"const": "INTEGRATE"},
                            "tau": {"type": "number", "minimum": 0},
                            "src": {"type": "integer", "minimum": 0, "maximum": 7},
                            "dst": {"type": "integer", "minimum": 0, "maximum": 7}
                        },
                        "required": ["op", "tau", "src", "dst"],
                        "additionalProperties": False
                    },
                    {
                        "properties": {
                            "op": {"const": "MIX"},
                            "srcA": {"type": "integer", "minimum": 0, "maximum": 7},
                            "srcB": {"type": "integer", "minimum": 0, "maximum": 7},
                            "gainA": {"type": "number", "minimum": 0, "maximum": 2.0},
                            "gainB": {"type": "number", "minimum": 0, "maximum": 2.0},
                            "dst": {"type": "integer", "minimum": 0, "maximum": 7}
                        },
                        "required": ["op", "srcA", "srcB", "gainA", "gainB", "dst"],
                        "additionalProperties": False
                    }
                ]
            }
        }
    },
    "additionalProperties": False
}

class PXOSValidator:
    """PXOS Schema Validator with CSV/JSON conversion"""
    
    def __init__(self):
        self.schema = PXOS_SCHEMA
        self.errors = []
        self.warnings = []
    
    def validate_json(self, json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate JSON data against PXOS schema"""
        self.errors = []
        self.warnings = []
        
        try:
            # Basic structure validation
            if not isinstance(json_data, dict):
                self.errors.append("Root must be an object")
                return False, self.errors
            
            # Check required fields
            if "schemaVersion" not in json_data:
                self.errors.append("Missing required field: schemaVersion")
            elif json_data["schemaVersion"] != "pxos-ops/1.0":
                self.errors.append(f"Invalid schema version: {json_data['schemaVersion']}")
            
            if "program" not in json_data:
                self.errors.append("Missing required field: program")
            elif not isinstance(json_data["program"], list):
                self.errors.append("Field 'program' must be an array")
            else:
                # Validate each operation
                for i, op in enumerate(json_data["program"]):
                    self._validate_operation(op, i)
            
            # Validate metadata if present
            if "meta" in json_data:
                self._validate_metadata(json_data["meta"])
            
            return len(self.errors) == 0, self.errors
            
        except Exception as e:
            self.errors.append(f"Validation error: {str(e)}")
            return False, self.errors
    
    def _validate_operation(self, op: Dict[str, Any], index: int):
        """Validate a single operation"""
        if not isinstance(op, dict):
            self.errors.append(f"Operation {index}: Must be an object")
            return
        
        if "op" not in op:
            self.errors.append(f"Operation {index}: Missing 'op' field")
            return
        
        op_type = op["op"]
        
        # Define validation rules for each operation type
        validation_rules = {
            "NOP": [],
            "COMMIT": [],
            "SLEEP": [("ms", int, 0, 65535)],
            "SYNC_ROW": [("i", int, 0, 255)],
            "SYNC_PAGE": [("i", int, 0, 255)],
            "RECT": [
                ("x", int, 0, 255), ("y", int, 0, 255),
                ("w", int, 0, 255), ("h", int, 0, 255),
                ("r", int, 0, 255), ("g", int, 0, 255), ("b", int, 0, 255)
            ],
            "LINE": [
                ("x1", int, 0, 255), ("y1", int, 0, 255),
                ("x2", int, 0, 255), ("y2", int, 0, 255),
                ("gray", int, 0, 255)
            ],
            "DAC_WRITE": [("ch", int, 0, 7), ("val", int, 0, 255)],
            "ADC_READ": [("ch", int, 0, 7)],
            "FILTER": [
                ("type", str), ("fc", int, 0, 65535),
                ("src", int, 0, 7), ("dst", int, 0, 7)
            ],
            "INTEGRATE": [
                ("tau", (int, float), 0, None),
                ("src", int, 0, 7), ("dst", int, 0, 7)
            ]
        }
        
        if op_type not in validation_rules:
            self.errors.append(f"Operation {index}: Unknown operation type '{op_type}'")
            return
        
        rules = validation_rules[op_type]
        
        # Check required fields
        for field_info in rules:
            field_name = field_info[0]
            expected_type = field_info[1]
            
            if field_name not in op:
                self.errors.append(f"Operation {index} ({op_type}): Missing required field '{field_name}'")
                continue
            
            value = op[field_name]
            
            # Type checking
            if isinstance(expected_type, tuple):
                if not isinstance(value, expected_type):
                    self.errors.append(f"Operation {index} ({op_type}): Field '{field_name}' must be {expected_type}")
                    continue
            else:
                if not isinstance(value, expected_type):
                    self.errors.append(f"Operation {index} ({op_type}): Field '{field_name}' must be {expected_type.__name__}")
                    continue
            
            # Range checking for numeric values
            if len(field_info) >= 4 and isinstance(value, (int, float)):
                min_val, max_val = field_info[2], field_info[3]
                if min_val is not None and value < min_val:
                    self.errors.append(f"Operation {index} ({op_type}): Field '{field_name}' must be >= {min_val}")
                if max_val is not None and value > max_val:
                    self.errors.append(f"Operation {index} ({op_type}): Field '{field_name}' must be <= {max_val}")
            
            # Special validation for filter types
            if field_name == "type" and op_type == "FILTER":
                valid_types = ["lowpass", "highpass", "bandpass", "notch"]
                if value not in valid_types:
                    self.errors.append(f"Operation {index} (FILTER): Invalid filter type '{value}', must be one of {valid_types}")
    
    def _validate_metadata(self, meta: Dict[str, Any]):
        """Validate metadata section"""
        if "cols" in meta:
            if not isinstance(meta["cols"], int) or not (1 <= meta["cols"] <= 64):
                self.errors.append("Metadata: 'cols' must be an integer between 1 and 64")
        
        if "rows" in meta:
            if not isinstance(meta["rows"], int) or not (1 <= meta["rows"] <= 64):
                self.errors.append("Metadata: 'rows' must be an integer between 1 and 64")
        
        if "page" in meta:
            if not isinstance(meta["page"], int) or meta["page"] < 0:
                self.errors.append("Metadata: 'page' must be a non-negative integer")
    
    def csv_to_json(self, csv_text: str) -> Dict[str, Any]:
        """Convert CSV to JSON format"""
        lines = csv_text.strip().split('\n')
        program = []
        meta = {"profile": "default", "cols": 16, "page": 0}
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                # Parse metadata from header comments
                if line.startswith('# pxos-ops/1.0'):
                    # Extract metadata: # pxos-ops/1.0, profile=default, cols=16
                    parts = line.split(',')
                    for part in parts[1:]:
                        if '=' in part:
                            key, value = part.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            if key in ['cols', 'rows', 'page']:
                                try:
                                    meta[key] = int(value)
                                except ValueError:
                                    self.warnings.append(f"Line {line_num}: Invalid {key} value: {value}")
                            else:
                                meta[key] = value
                continue
            
            # Parse operation
            try:
                op = self._parse_csv_line(line, line_num)
                if op:
                    program.append(op)
            except Exception as e:
                self.errors.append(f"Line {line_num}: Parse error: {str(e)}")
        
        return {
            "schemaVersion": "pxos-ops/1.0",
            "meta": meta,
            "program": program
        }
    
    def _parse_csv_line(self, line: str, line_num: int) -> Optional[Dict[str, Any]]:
        """Parse a single CSV line into an operation"""
        parts = [p.strip() for p in line.split(',')]
        if not parts:
            return None
        
        op_type = parts[0].upper()
        
        try:
            if op_type == "NOP":
                return {"op": "NOP"}
            elif op_type == "COMMIT":
                return {"op": "COMMIT"}
            elif op_type == "SLEEP":
                if len(parts) < 2:
                    raise ValueError("SLEEP requires ms parameter")
                return {"op": "SLEEP", "ms": int(parts[1])}
            elif op_type == "SYNC_ROW":
                if len(parts) < 2:
                    raise ValueError("SYNC_ROW requires i parameter")
                return {"op": "SYNC_ROW", "i": int(parts[1])}
            elif op_type == "RECT":
                if len(parts) < 8:
                    raise ValueError("RECT requires x,y,w,h,r,g,b parameters")
                return {
                    "op": "RECT",
                    "x": int(parts[1]), "y": int(parts[2]),
                    "w": int(parts[3]), "h": int(parts[4]),
                    "r": int(parts[5]), "g": int(parts[6]), "b": int(parts[7])
                }
            elif op_type == "LINE":
                if len(parts) < 6:
                    raise ValueError("LINE requires x1,y1,x2,y2,gray parameters")
                return {
                    "op": "LINE",
                    "x1": int(parts[1]), "y1": int(parts[2]),
                    "x2": int(parts[3]), "y2": int(parts[4]),
                    "gray": int(parts[5])
                }
            elif op_type == "DAC_WRITE":
                if len(parts) < 3:
                    raise ValueError("DAC_WRITE requires ch,val parameters")
                return {"op": "DAC_WRITE", "ch": int(parts[1]), "val": int(parts[2])}
            elif op_type == "ADC_READ":
                if len(parts) < 2:
                    raise ValueError("ADC_READ requires ch parameter")
                op_dict = {"op": "ADC_READ", "ch": int(parts[1])}
                if len(parts) >= 3:
                    op_dict["dst"] = parts[2]
                return op_dict
            elif op_type == "FILTER":
                if len(parts) < 5:
                    raise ValueError("FILTER requires type,fc,src,dst parameters")
                return {
                    "op": "FILTER",
                    "type": parts[1], "fc": int(parts[2]),
                    "src": int(parts[3]), "dst": int(parts[4])
                }
            elif op_type == "INTEGRATE":
                if len(parts) < 4:
                    raise ValueError("INTEGRATE requires tau,src,dst parameters")
                return {
                    "op": "INTEGRATE",
                    "tau": float(parts[1]),
                    "src": int(parts[2]), "dst": int(parts[3])
                }
            else:
                self.warnings.append(f"Line {line_num}: Unknown operation type: {op_type}")
                return None
                
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid parameters for {op_type}: {str(e)}")
    
    def json_to_csv(self, json_data: Dict[str, Any]) -> str:
        """Convert JSON to CSV format"""
        lines = []
        
        # Add header with metadata
        meta = json_data.get("meta", {})
        header_parts = ["# pxos-ops/1.0"]
        
        for key, value in meta.items():
            header_parts.append(f"{key}={value}")
        
        lines.append(", ".join(header_parts))
        lines.append("")  # Empty line after header
        
        # Convert operations
        for op in json_data.get("program", []):
            csv_line = self._operation_to_csv(op)
            if csv_line:
                lines.append(csv_line)
        
        return "\n".join(lines)
    
    def _operation_to_csv(self, op: Dict[str, Any]) -> str:
        """Convert a single operation to CSV format"""
        op_type = op["op"]
        
        if op_type == "NOP":
            return "NOP"
        elif op_type == "COMMIT":
            return "COMMIT"
        elif op_type == "SLEEP":
            return f"SLEEP,{op['ms']}"
        elif op_type == "SYNC_ROW":
            return f"SYNC_ROW,{op['i']}"
        elif op_type == "RECT":
            return f"RECT,{op['x']},{op['y']},{op['w']},{op['h']},{op['r']},{op['g']},{op['b']}"
        elif op_type == "LINE":
            return f"LINE,{op['x1']},{op['y1']},{op['x2']},{op['y2']},{op['gray']}"
        elif op_type == "DAC_WRITE":
            return f"DAC_WRITE,{op['ch']},{op['val']}"
        elif op_type == "ADC_READ":
            result = f"ADC_READ,{op['ch']}"
            if "dst" in op:
                result += f",{op['dst']}"
            return result
        elif op_type == "FILTER":
            return f"FILTER,{op['type']},{op['fc']},{op['src']},{op['dst']}"
        elif op_type == "INTEGRATE":
            return f"INTEGRATE,{op['tau']},{op['src']},{op['dst']}"
        else:
            return f"# Unknown operation: {op_type}"

# Test function
def test_validator():
    """Test the PXOS validator with sample data"""
    validator = PXOSValidator()
    
    # Test CSV parsing
    test_csv = """# pxos-ops/1.0, profile=default, cols=16
RECT,20,20,40,20,64,64,64
SLEEP,30
DAC_WRITE,1,150
FILTER,lowpass,1000,0,1
INTEGRATE,0.1,1,2
COMMIT"""
    
    print("Testing CSV to JSON conversion:")
    json_data = validator.csv_to_json(test_csv)
    print(json.dumps(json_data, indent=2))
    
    print("\nValidating JSON:")
    is_valid, errors = validator.validate_json(json_data)
    print(f"Valid: {is_valid}")
    if errors:
        for error in errors:
            print(f"  Error: {error}")
    
    print("\nConverting back to CSV:")
    csv_result = validator.json_to_csv(json_data)
    print(csv_result)

if __name__ == "__main__":
    test_validator()