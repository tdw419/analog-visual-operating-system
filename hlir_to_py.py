# hlir_to_py.py
from typing import Any, Dict, List

def _args(xs: List[str]) -> str:
    return ", ".join(xs)

def hlir_to_python(hlir: Dict[str, Any], alias: str = "VA") -> str:
    """
    Render pxos-ops/1.0 HLIR to idiomatic Python using `viewer_adapter as {alias}`.
    Matches your AST parser's calling convention:
      - RECT(x,y,w,h, g [, r=..][, b=..])  # r/b emitted only if != g
      - other ops: direct positional args
    Unknown ops are ignored (forward-compatible).
    """
    lines = [f"import viewer_adapter as {alias}"]
    for op in hlir.get("program", []):
        kind = op.get("op")
        if kind == "RECT":
            x, y, w, h = (int(op["x"]), int(op["y"]), int(op["w"]), int(op["h"]))
            g = int(op.get("g", op.get("r", 0)))
            parts: List[str] = [str(x), str(y), str(w), str(h), str(g)]
            # emit r/b only if they differ from g (your AST accepts named overrides)
            r = int(op.get("r", g))
            b = int(op.get("b", g))
            if r != g:
                parts.append(f"r={r}")
            if b != g:
                parts.append(f"b={b}")
            lines.append(f"{alias}.RECT({_args(parts)})")

        elif kind == "COMMIT":
            lines.append(f"{alias}.COMMIT()")

        elif kind == "SLEEP":
            lines.append(f"{alias}.SLEEP({int(op['ms'])})")

        elif kind == "SYNC_ROW":
            lines.append(f"{alias}.SYNC_ROW({int(op['i'])})")

        elif kind == "DAC_WRITE":
            lines.append(f"{alias}.DAC_WRITE({int(op['ch'])}, {int(op['val'])})")

        elif kind == "INTEGRATE":
            lines.append(
                f"{alias}.INTEGRATE({float(op['tau'])}, {int(op['src'])}, {int(op['dst'])})"
            )

        elif kind == "FILTER":
            # type is a string in HLIR (e.g., "lp", "hp"); quote it in Python
            lines.append(
                f"{alias}.FILTER({op['type']!r}, {int(op['fc'])}, {int(op['src'])}, {int(op['dst'])})"
            )

        elif kind == "MULTIPLY":
            lines.append(
                f"{alias}.MULTIPLY({float(op['gain'])}, {int(op['src'])}, {int(op['dst'])})"
            )

        elif kind == "SUM":
            ins = ", ".join(str(int(i)) for i in op["inputs"])
            lines.append(f"{alias}.SUM([{ins}], {int(op['output'])})")

        else:
            # ignore unknowns to stay forward-compatible
            continue

    return "\n".join(lines) + "\n"