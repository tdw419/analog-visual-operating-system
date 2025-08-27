#!/usr/bin/env python3
"""
Reverse transpiler: HLIR to Python code generation
Generates clean, idiomatic Python code using ViewerAdapter calls
"""

from typing import Dict, List, Any

def hlir_to_python(hlir: Dict[str, Any]) -> str:
    """
    Generate Python code from PXOS HLIR.
    
    Args:
        hlir: HLIR dictionary
        
    Returns:
        Python source code string
    """
    lines = [
        "#!/usr/bin/env python3",
        "\"\"\"",
        "Generated Python code from PXOS HLIR",
        "\"\"\"",
        "",
        "import viewer_adapter as VA",
        ""
    ]
    
    # Add a main function wrapper
    lines.append("def main():")
    
    program = hlir.get("program", [])
    if not program:
        lines.append("    pass")
        return '\n'.join(lines)
    
    # Generate code for each operation
    for op in program:
        op_type = op.get("op")
        python_line = _generate_operation(op_type, op)
        if python_line:
            lines.append(f"    {python_line}")
    
    lines.extend([
        "",
        "if __name__ == '__main__':",
        "    main()"
    ])
    
    return '\n'.join(lines)

def _generate_operation(op_type: str, op: Dict[str, Any]) -> str:
    """
    Generate Python code for a single operation.
    
    Args:
        op_type: Operation type string
        op: Operation dictionary
        
    Returns:
        Python code line
    """
    if op_type == "RECT":
        # Check if it's grayscale (all RGB components equal)
        r, g, b = op["r"], op["g"], op["b"]
        if r == g == b:
            return f"VA.RECT({op['x']}, {op['y']}, {op['w']}, {op['h']}, {r})"
        else:
            return f"VA.RECT({op['x']}, {op['y']}, {op['w']}, {op['h']}, {r}, {g}, {b})"
    
    elif op_type == "COMMIT":
        return "VA.COMMIT()"
    
    elif op_type == "SLEEP":
        return f"VA.SLEEP({op['ms']})"
    
    elif op_type == "DAC_WRITE":
        return f"VA.DAC_WRITE({op['ch']}, {op['val']})"
    
    elif op_type == "INTEGRATE":
        return f"VA.INTEGRATE({op['tau']}, {op['src']}, {op['dst']})"
    
    elif op_type == "FILTER":
        return f"VA.FILTER('{op['type']}', {op['fc']}, {op['src']}, {op['dst']})"
    
    elif op_type == "MULTIPLY":
        return f"VA.MULTIPLY({op['gain']}, {op['src']}, {op['dst']})"
    
    elif op_type == "SUM":
        inputs = op['inputs']
        if len(inputs) == 1:
            inputs_str = str(inputs[0])
        else:
            inputs_str = str(inputs)
        return f"VA.SUM({inputs_str}, {op['output']})"
    
    elif op_type == "SYNC_ROW":
        return f"VA.SYNC_ROW({op['i']})"
    
    else:
        return f"# Unknown operation: {op_type}"

def hlir_to_python_compact(hlir: Dict[str, Any]) -> str:
    """
    Generate compact Python code without function wrapper.
    
    Args:
        hlir: HLIR dictionary
        
    Returns:
        Compact Python source code
    """
    lines = ["import viewer_adapter as VA"]
    
    for op in hlir.get("program", []):
        op_type = op.get("op")
        python_line = _generate_operation(op_type, op)
        if python_line and not python_line.startswith('#'):
            lines.append(python_line)
    
    return '\n'.join(lines)

def hlir_to_python_with_comments(hlir: Dict[str, Any]) -> str:
    """
    Generate Python code with detailed comments.
    
    Args:
        hlir: HLIR dictionary
        
    Returns:
        Commented Python source code
    """
    lines = [
        "#!/usr/bin/env python3",
        "\"\"\"",
        "Generated Python code from PXOS HLIR",
        f"Schema: {hlir.get('schemaVersion', 'unknown')}",
        f"Operations: {len(hlir.get('program', []))}",
        "\"\"\"",
        "",
        "import viewer_adapter as VA",
        ""
    ]
    
    meta = hlir.get("meta", {})
    if meta:
        lines.append("# Metadata:")
        for key, value in meta.items():
            lines.append(f"# {key}: {value}")
        lines.append("")
    
    lines.append("def main():")
    
    program = hlir.get("program", [])
    if not program:
        lines.append("    pass")
    else:
        for i, op in enumerate(program):
            op_type = op.get("op")
            
            # Add operation comment
            lines.append(f"    # Operation {i+1}: {op_type}")
            
            python_line = _generate_operation(op_type, op)
            if python_line:
                lines.append(f"    {python_line}")
            lines.append("")
    
    lines.extend([
        "if __name__ == '__main__':",
        "    main()"
    ])
    
    return '\n'.join(lines)

if __name__ == "__main__":
    # Test the reverse transpiler
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
            {"op": "INTEGRATE", "tau": 0.1, "src": 0, "dst": 1},
            {"op": "SUM", "inputs": [0, 1], "output": 2},
            {"op": "COMMIT"}
        ]
    }
    
    print("=== Standard Format ===")
    print(hlir_to_python(test_hlir))
    
    print("\n=== Compact Format ===")
    print(hlir_to_python_compact(test_hlir))
    
    print("\n=== With Comments ===")
    print(hlir_to_python_with_comments(test_hlir))