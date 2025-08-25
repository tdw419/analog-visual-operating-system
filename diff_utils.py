from typing import Any, Dict, List
from diff_models import JsonDiff, OpDiff, FieldDiff
from PIL import Image, ImageDraw, ImageChops, ImageOps
from raster import rasterize_rects

COMPARABLE_KEYS = ("op", "x", "y", "w", "h", "r", "g", "b", "ms", "ch", "val", "tau", "src", "dst", "type", "fc", "gain", "inputs", "output")

def json_diff(canonical: Dict[str, Any], current: Dict[str, Any]) -> JsonDiff:
    """Compute structured JSON diff between canonical and current HLIR"""
    def _normalize_op(op: Dict[str, Any]) -> Dict[str, Any]:
        return {k: op[k] for k in COMPARABLE_KEYS if k in op}

    def _field_level_diff(left: Dict[str, Any], right: Dict[str, Any]) -> List[FieldDiff]:
        diffs: List[FieldDiff] = []
        keys = set(left.keys()) | set(right.keys())
        for k in sorted(keys):
            lv = left.get(k, None)
            rv = right.get(k, None)
            if lv != rv:
                diffs.append(FieldDiff(field=k, left=lv, right=rv))
        return diffs

    L = canonical.get("program", [])
    R = current.get("program", [])
    nL, nR = len(L), len(R)
    max_len = max(nL, nR)
    ops: List[OpDiff] = []
    same = changed = added = removed = 0
    for idx in range(max_len):
        left = L[idx] if idx < nL else None
        right = R[idx] if idx < nR else None
        if left is None and right is not None:
            ops.append(OpDiff(index=idx, status="added", op_right=right))
            added += 1
            continue
        if right is None and left is not None:
            ops.append(OpDiff(index=idx, status="removed", op_left=left))
            removed += 1
            continue
        nl = _normalize_op(left) if left else {}
        nr = _normalize_op(right) if right else {}
        if nl == nr:
            ops.append(OpDiff(index=idx, status="same", op_left=left, op_right=right))
            same += 1
        else:
            diffs = _field_level_diff(nl, nr)
            ops.append(OpDiff(index=idx, status="changed", op_left=left, op_right=right, field_diffs=diffs))
            changed += 1
    return JsonDiff(ops=ops, same_count=same, changed_count=changed, added_count=added, removed_count=removed)

def compute_overlay(canonical: Dict[str, Any], current: Dict[str, Any], size: tuple[int, int] = (256, 256)) -> Image.Image:
    """Compute pixel-level overlay diff for visual comparison"""
    left = rasterize_rects(canonical, size=size)
    right = rasterize_rects(current, size=size)
    diff = ImageChops.difference(left, right)
    diff = ImageOps.autocontrast(diff)
    heat = ImageOps.colorize(diff, black=(0, 0, 0), white=(255, 0, 0)).convert("RGBA")
    base = right.convert("RGBA")
    return Image.blend(base, heat, alpha=0.5)
