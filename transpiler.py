import ast
import operator
from typing import Any, Dict, List, Union
from validate_hlir import ValidationError

def clamp(v, lo, hi): 
    return max(lo, min(hi, v))

class PyToHLIR(ast.NodeVisitor):
    ALLOWED_FUNCS = {"RECT", "COMMIT", "SLEEP", "DAC_WRITE"}  # Minimal set for Phase 1
    EXTENDED_FUNCS = {"INTEGRATE", "FILTER", "MULTIPLY", "SUM"}  # For later expansion
    BINOPS = {
        ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
        ast.Pow: operator.pow
    }
    UNOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}

    def __init__(self):
        self.env: Dict[str, Any] = {}
        self.program: List[Dict[str, Any]] = []

    def eval(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float, str, bool, type(None))):
                return node.value
            raise ValidationError(f"Unsupported constant at line {node.lineno}")
        if isinstance(node, ast.Name):
            if node.id in self.env:
                return self.env[node.id]
            raise ValidationError(f"Unknown name '{node.id}' at line {node.lineno}")
        if isinstance(node, ast.BinOp) and type(node.op) in self.BINOPS:
            return self.BINOPS[type(node.op)](self.eval(node.left), self.eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in self.UNOPS:
            return self.UNOPS[type(node.op)](self.eval(node.operand))
        if isinstance(node, ast.List):
            return [self.eval(e) for e in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self.eval(e) for e in node.elts)
        raise ValidationError(f"Unsafe expression at line {node.lineno}")

    def visit_Assign(self, node: ast.Assign):
        val = self.eval(node.value)
        for tgt in node.targets:
            if isinstance(tgt, ast.Name):
                self.env[tgt.id] = val
            else:
                raise ValidationError(f"Only simple names allowed on LHS at line {node.lineno}")
        return None

    def _call_name(self, node: ast.Call) -> str:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            return node.func.attr
        return ""

    def visit_Expr(self, node: ast.Expr):
        if isinstance(node.value, ast.Call):
            self._handle_call(node.value)

    def _handle_call(self, call: ast.Call):
        name = self._call_name(call).upper()
        if name not in self.ALLOWED_FUNCS:
            return  # Ignore unsupported calls safely
        args = [self.eval(arg) for arg in call.args]
        kwargs = {kw.arg: self.eval(kw.value) for kw in call.keywords if kw.arg}
        try:
            if name == "RECT":
                if len(args) != 5:
                    raise ValidationError(f"RECT requires 5 args at line {call.lineno}")
                x, y, w, h, g = map(int, args)
                x, y, w, h = [clamp(v, 0, 255) for v in (x, y, w, h)]
                g = clamp(g, 0, 255)
                r = clamp(kwargs.get("r", g), 0, 255)
                g_val = clamp(kwargs.get("g", g), 0, 255)
                b = clamp(kwargs.get("b", g), 0, 255)
                self.program.append({"op": "RECT", "x": x, "y": y, "w": w, "h": h, "r": r, "g": g_val, "b": b})
            elif name == "COMMIT":
                if len(args) != 0:
                    raise ValidationError(f"COMMIT takes no args at line {call.lineno}")
                self.program.append({"op": "COMMIT"})
            elif name == "SLEEP":
                if len(args) != 1:
                    raise ValidationError(f"SLEEP requires 1 arg at line {call.lineno}")
                self.program.append({"op": "SLEEP", "ms": clamp(int(args[0]), 0, 10000)})
            elif name == "DAC_WRITE":
                if len(args) != 2:
                    raise ValidationError(f"DAC_WRITE requires 2 args at line {call.lineno}")
                ch, val = map(int, args)
                self.program.append({"op": "DAC_WRITE", "ch": clamp(ch, 0, 7), "val": clamp(val, 0, 255)})
        except ValueError as e:
            raise ValidationError(f"Invalid argument type at line {call.lineno}: {e}")

    def to_hlir(self) -> Dict[str, Any]:
        return {
            "schemaVersion": "pxos-ops/1.0",
            "meta": {"profile": "default", "cols": 16},
            "program": self.program
        }

def T_py_to_hlir(code: str) -> Dict[str, Any]:
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as e:
        raise ValidationError(f"Python syntax error: {e.msg} at {e.lineno}:{e.offset}")
    v = PyToHLIR()
    for node in tree.body:
        v.visit(node)
    return v.to_hlir()