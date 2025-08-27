# json_diff.py
import json
import difflib
from typing import List, Tuple, Dict, Any

def compute_json_diff(canonical_hlir: Dict[str, Any], drifted_hlir: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    Compute and format a diff between two HLIR JSON structures.
    Returns a list of diff lines with annotations for UI rendering.
    """
    canonical_str = json.dumps(canonical_hlir, indent=2, sort_keys=True)
    drifted_str = json.dumps(drifted_hlir, indent=2, sort_keys=True)

    # Split into lines for diffing
    canonical_lines = canonical_str.splitlines()
    drifted_lines = drifted_str.splitlines()

    # Compute the diff
    differ = difflib.Differ()
    diff_lines = list(differ.compare(canonical_lines, drifted_lines))

    # Format the diff for UI rendering
    formatted_diff = []
    for line in diff_lines:
        if line.startswith('- '):
            formatted_diff.append(('removed', line[2:]))
        elif line.startswith('+ '):
            formatted_diff.append(('added', line[2:]))
        elif line.startswith('? '):
            continue  # Skip the "? " lines
        else:
            formatted_diff.append(('unchanged', line))

    return formatted_diff

def compute_field_level_diff(canonical_hlir: Dict[str, Any], drifted_hlir: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute field-level differences between two HLIR structures.
    Returns a detailed report of added, removed, and modified operations.
    """
    diff_report = {
        "added_ops": [],
        "removed_ops": [],
        "modified_ops": [],
        "field_changes": []
    }
    
    canonical_ops = canonical_hlir.get("program", [])
    drifted_ops = drifted_hlir.get("program", [])
    
    # Find added/removed ops
    canonical_op_ids = {id(op): op for op in canonical_ops}
    drifted_op_ids = {id(op): op for op in drifted_ops}
    
    # Check for removed operations
    for op in canonical_ops:
        if op not in drifted_ops:
            diff_report["removed_ops"].append(op)
    
    # Check for added operations
    for op in drifted_ops:
        if op not in canonical_ops:
            diff_report["added_ops"].append(op)
    
    # Find modified ops by comparing at field level
    for i, canon_op in enumerate(canonical_ops):
        if i < len(drifted_ops):
            curr_op = drifted_ops[i]
            if canon_op != curr_op:
                field_diffs = compare_op_fields(canon_op, curr_op)
                if field_diffs:
                    diff_report["modified_ops"].append({
                        "index": i,
                        "canonical": canon_op,
                        "current": curr_op,
                        "differences": field_diffs
                    })
    
    return diff_report

def compare_op_fields(op1: Dict[str, Any], op2: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Compare fields between two operations"""
    differences = []
    
    # Get all field names from both ops
    all_fields = set(op1.keys()) | set(op2.keys())
    
    for field in all_fields:
        val1 = op1.get(field)
        val2 = op2.get(field)
        
        if val1 != val2:
            differences.append({
                "field": field,
                "canonical": val1,
                "current": val2
            })
    
    return differences