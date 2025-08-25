import ast, operator
from typing import Any, Dict, List, Union
from pxos_sync_engine import ValidationError

class PyToHLIR(ast.NodeVisitor):
    ALLOWED_FUNCS = {
        "RECT","COMMIT","SLEEP","SYNC_ROW","DAC_WRITE",
        "INTEGRATE","FILTER","MULTIPLY","SUM"
    }
    BINOPS = {
        ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
        ast.Pow: operator.pow
    }
    UNOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}

    def __init__(self):
        self.env: Dict[str, Any] = {}
        self.program: List[Dict[str,Any]] = []

    # ---- evaluation of safe expressions ----
    def eval(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float, str, bool, type(None))):
                return node.value
            raise ValueError("unsupported constant")
        if isinstance(node, ast.Name):
            if node.id in self.env: return self.env[node.id]
            raise ValueError(f"unknown name '{node.id}'")
        if isinstance(node, ast.BinOp) and type(node.op) in self.BINOPS:
            return self.BINOPS[type(node.op)](self.eval(node.left), self.eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in self.UNOPS:
            return self.UNOPS[type(node.op)](self.eval(node.operand))
        if isinstance(node, ast.List):
            return [self.eval(e) for e in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self.eval(e) for e in node.elts)
        raise ValueError("unsafe expression")

    # ---- visitors ----
    def visit_Assign(self, node: ast.Assign):
        val = self.eval(node.value)
        for tgt in node.targets:
            if isinstance(tgt, ast.Name):
                self.env[tgt.id] = val
            else:
                raise ValueError("only simple names on LHS")
        return None

    def _call_name(self, node: ast.Call) -> str:
        # RECT(...) or VA.RECT(...)
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            return node.func.attr
        return ""

    def visit_Expr(self, node: ast.Expr):
        if isinstance(node.value, ast.Call):
            self._handle_call(node.value)
        # ignore bare strings / docstrings etc.

    def _handle_call(self, call: ast.Call):
        name = self._call_name(call).upper()
        if name not in self.ALLOWED_FUNCS:
            return  # ignore other calls safely

        # map each op to HLIR object
        def args(*ix):
            vals = []
            # positional first
            for i in ix:
                if i < len(call.args):
                    vals.append(self.eval(call.args[i]))
                else:
                    vals.append(None)
            # named override
            kwargs = {kw.arg: self.eval(kw.value) for kw in call.keywords if kw.arg}
            return vals, kwargs

        if name == "RECT":
            (x,y,w,h,g), kw = args(0,1,2,3,4)
            r = kw.get("r", g); b = kw.get("b", g); gg = kw.get("g", g)
            self.program.append({"op":"RECT","x":int(x),"y":int(y),"w":int(w),"h":int(h),
                                 "r":int(r),"g":int(gg),"b":int(b)})
        elif name == "COMMIT":
            self.program.append({"op":"COMMIT"})
        elif name == "SLEEP":
            (ms,), _ = args(0)
            self.program.append({"op":"SLEEP","ms":int(ms)})
        elif name == "SYNC_ROW":
            (i,), _ = args(0)
            self.program.append({"op":"SYNC_ROW","i":int(i)})
        elif name == "DAC_WRITE":
            (ch,val), _ = args(0,1)
            self.program.append({"op":"DAC_WRITE","ch":int(ch),"val":int(val)})
        elif name == "INTEGRATE":
            (tau,src,dst), _ = args(0,1,2)
            self.program.append({"op":"INTEGRATE","tau":float(tau),"src":int(src),"dst":int(dst)})
        elif name == "FILTER":
            (typ,fc,src,dst), _ = args(0,1,2,3)
            self.program.append({"op":"FILTER","type":str(typ),"fc":int(fc),"src":int(src),"dst":int(dst)})
        elif name == "MULTIPLY":
            (gain,src,dst), _ = args(0,1,2)
            self.program.append({"op":"MULTIPLY","gain":float(gain),"src":int(src),"dst":int(dst)})
        elif name == "SUM":
            (inputs,output), _ = args(0,1)
            self.program.append({"op":"SUM","inputs":[int(i) for i in inputs],"output":int(output)})

    def to_hlir(self) -> Dict[str,Any]:
        return {
            "schemaVersion": "pxos-ops/1.0",
            "meta": {"profile":"default","cols":16},
            "program": self.program
        }

def T_py_to_hlir(code: str) -> Dict[str,Any]:
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as e:
        raise ValidationError(f"Python syntax error: {e.msg} at {e.lineno}:{e.offset}")
    v = PyToHLIR()
    for node in tree.body:
        v.visit(node)
    return v.to_hlir()
