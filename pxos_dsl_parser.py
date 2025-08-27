#!/usr/bin/env python3
"""
Minimal DSL parser for PXOS Analog Domain Specific Language
Converts analog DSL text to HLIR and vice versa
"""

import re
from typing import Dict, List, Any, Union
from pxos_sync_engine_enhanced import ValidationError

class AnalogDSLParser:
    """
    Parser for PXOS Analog DSL format.
    Handles operations like RECT(x=20,y=20,w=40,h=20,g=64), SLEEP(ms=30), etc.
    """
    
    def __init__(self):
        self.operations: List[Dict[str, Any]] = []
        
        # Regex patterns for each operation type
        self.patterns = {
            'RECT': re.compile(r'RECT\s*\(\s*(?:x\s*=\s*)?(\d+)\s*,\s*(?:y\s*=\s*)?(\d+)\s*,\s*(?:w\s*=\s*)?(\d+)\s*,\s*(?:h\s*=\s*)?(\d+)\s*,\s*(?:(?:g|gray)\s*=\s*)?(\d+)(?:\s*,\s*(?:r\s*=\s*)?(\d+))?(?:\s*,\s*(?:g\s*=\s*)?(\d+))?(?:\s*,\s*(?:b\s*=\s*)?(\d+))?\s*\)', re.IGNORECASE),
            'SLEEP': re.compile(r'SLEEP\s*\(\s*(?:ms\s*=\s*)?(\d+)\s*\)', re.IGNORECASE),
            'DAC_WRITE': re.compile(r'DAC_WRITE\s*\(\s*(?:ch\s*=\s*)?(\d+)\s*,\s*(?:val\s*=\s*)?(\d+)\s*\)', re.IGNORECASE),
            'COMMIT': re.compile(r'COMMIT\s*\(\s*\)', re.IGNORECASE),
            'INTEGRATE': re.compile(r'INTEGRATE\s*\(\s*(?:tau\s*=\s*)?([0-9]*\.?[0-9]+)\s*,\s*(?:src\s*=\s*)?(\d+)\s*,\s*(?:dst\s*=\s*)?(\d+)\s*\)', re.IGNORECASE),
            'FILTER': re.compile(r'FILTER\s*\(\s*(?:type\s*=\s*)?([a-z]+)\s*,\s*(?:fc\s*=\s*)?([0-9]*\.?[0-9]+)\s*,\s*(?:src\s*=\s*)?(\d+)\s*,\s*(?:dst\s*=\s*)?(\d+)\s*\)', re.IGNORECASE),
            'MULTIPLY': re.compile(r'MULTIPLY\s*\(\s*(?:gain\s*=\s*)?([0-9\-]*\.?[0-9]+)\s*,\s*(?:src\s*=\s*)?(\d+)\s*,\s*(?:dst\s*=\s*)?(\d+)\s*\)', re.IGNORECASE),
            'SUM': re.compile(r'SUM\s*\(\s*(?:inputs\s*=\s*)?\[([0-9,\s]+)\]\s*,\s*(?:output\s*=\s*)?(\d+)\s*\)', re.IGNORECASE),
            'SYNC_ROW': re.compile(r'SYNC_ROW\s*\(\s*(?:i\s*=\s*)?(\d+)\s*\)', re.IGNORECASE),
        }

    def parse_line(self, line: str) -> None:
        """Parse a single line of DSL code"""
        line = line.strip()
        if not line or line.startswith('#'):
            return
        
        # Try to match each operation pattern
        for op_name, pattern in self.patterns.items():
            match = pattern.match(line)
            if match:
                self._process_match(op_name, match.groups())
                return
        
        # If no pattern matched, it might be an invalid line
        if line:
            raise ValidationError(f"Invalid DSL syntax: {line}")

    def _process_match(self, op_name: str, groups: tuple) -> None:
        """Process a matched operation"""
        try:
            if op_name == 'RECT':
                x, y, w, h, gray, r, g, b = groups
                # Use gray value for missing RGB components
                r = int(r) if r else int(gray)
                g = int(g) if g else int(gray)
                b = int(b) if b else int(gray)
                
                self.operations.append({
                    "op": "RECT",
                    "x": int(x), "y": int(y), "w": int(w), "h": int(h),
                    "r": r, "g": g, "b": b
                })
            
            elif op_name == 'SLEEP':
                ms = groups[0]
                self.operations.append({"op": "SLEEP", "ms": int(ms)})
            
            elif op_name == 'DAC_WRITE':
                ch, val = groups
                self.operations.append({"op": "DAC_WRITE", "ch": int(ch), "val": int(val)})
            
            elif op_name == 'COMMIT':
                self.operations.append({"op": "COMMIT"})
            
            elif op_name == 'INTEGRATE':
                tau, src, dst = groups
                self.operations.append({
                    "op": "INTEGRATE",
                    "tau": float(tau),
                    "src": int(src),
                    "dst": int(dst)
                })
            
            elif op_name == 'FILTER':
                filter_type, fc, src, dst = groups
                self.operations.append({
                    "op": "FILTER",
                    "type": filter_type.lower(),
                    "fc": float(fc),
                    "src": int(src),
                    "dst": int(dst)
                })
            
            elif op_name == 'MULTIPLY':
                gain, src, dst = groups
                self.operations.append({
                    "op": "MULTIPLY",
                    "gain": float(gain),
                    "src": int(src),
                    "dst": int(dst)
                })
            
            elif op_name == 'SUM':
                inputs_str, output = groups
                inputs = [int(x.strip()) for x in inputs_str.split(',') if x.strip()]
                self.operations.append({
                    "op": "SUM",
                    "inputs": inputs,
                    "output": int(output)
                })
            
            elif op_name == 'SYNC_ROW':
                i = groups[0]
                self.operations.append({"op": "SYNC_ROW", "i": int(i)})
                
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Error parsing {op_name} operation: {e}")

    def parse(self, dsl_text: str) -> Dict[str, Any]:
        """
        Parse complete DSL text into HLIR format.
        
        Args:
            dsl_text: Multi-line DSL text
            
        Returns:
            HLIR dictionary
        """
        self.operations = []
        
        for line_no, line in enumerate(dsl_text.split('\n'), 1):
            try:
                self.parse_line(line)
            except ValidationError as e:
                raise ValidationError(f"Line {line_no}: {e}")
        
        return {
            "schemaVersion": "pxos-ops/1.0",
            "meta": {
                "profile": "default",
                "cols": 16
            },
            "program": self.operations
        }

def T_analog_to_hlir(dsl_text: str) -> Dict[str, Any]:
    """
    Transform analog DSL text to HLIR format.
    
    Args:
        dsl_text: DSL source code
        
    Returns:
        HLIR dictionary
    """
    parser = AnalogDSLParser()
    return parser.parse(dsl_text)

def T_hlir_to_analog(hlir: Dict[str, Any]) -> str:
    """
    Transform HLIR back to analog DSL format.
    
    Args:
        hlir: HLIR dictionary
        
    Returns:
        DSL source code string
    """
    lines = []
    
    for op in hlir.get("program", []):
        op_type = op.get("op")
        
        if op_type == "RECT":
            # Check if RGB components are all the same (grayscale)
            r, g, b = op["r"], op["g"], op["b"]
            if r == g == b:
                lines.append(f"RECT(x={op['x']},y={op['y']},w={op['w']},h={op['h']},g={r})")
            else:
                lines.append(f"RECT(x={op['x']},y={op['y']},w={op['w']},h={op['h']},r={r},g={g},b={b})")
        
        elif op_type == "SLEEP":
            lines.append(f"SLEEP(ms={op['ms']})")
        
        elif op_type == "DAC_WRITE":
            lines.append(f"DAC_WRITE(ch={op['ch']},val={op['val']})")
        
        elif op_type == "COMMIT":
            lines.append("COMMIT()")
        
        elif op_type == "INTEGRATE":
            lines.append(f"INTEGRATE(tau={op['tau']},src={op['src']},dst={op['dst']})")
        
        elif op_type == "FILTER":
            lines.append(f"FILTER(type={op['type']},fc={op['fc']},src={op['src']},dst={op['dst']})")
        
        elif op_type == "MULTIPLY":
            lines.append(f"MULTIPLY(gain={op['gain']},src={op['src']},dst={op['dst']})")
        
        elif op_type == "SUM":
            inputs_str = ','.join(map(str, op['inputs']))
            lines.append(f"SUM(inputs=[{inputs_str}],output={op['output']})")
        
        elif op_type == "SYNC_ROW":
            lines.append(f"SYNC_ROW(i={op['i']})")
    
    return '\n'.join(lines)

if __name__ == "__main__":
    # Test the DSL parser
    test_dsl = """
# Test program
RECT(x=20,y=20,w=40,h=20,g=64)
SLEEP(ms=30)
DAC_WRITE(ch=1,val=180)
INTEGRATE(tau=0.1,src=0,dst=1)
COMMIT()
"""
    
    try:
        print("Parsing DSL:")
        print(test_dsl)
        
        hlir = T_analog_to_hlir(test_dsl)
        print("\nGenerated HLIR:")
        import json
        print(json.dumps(hlir, indent=2))
        
        print("\nBack to DSL:")
        dsl_back = T_hlir_to_analog(hlir)
        print(dsl_back)
        
    except ValidationError as e:
        print(f"❌ Error: {e}")