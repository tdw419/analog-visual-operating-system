#!/usr/bin/env python3
"""
AST-based Python to HLIR transpiler for PXOS
Safely converts Python ViewerAdapter calls to pxos-ops/1.0 HLIR format
"""

import ast
import operator
from typing import Any, Dict, List, Union
from pxos_sync_engine_enhanced import ValidationError

class PyToHLIR(ast.NodeVisitor):
    """
    Transpiles Python code using ViewerAdapter calls to PXOS HLIR format.
    Handles RECT, INTEGRATE, FILTER, MULTIPLY, SUM, DAC_WRITE, COMMIT, SLEEP, and SYNC_ROW operations.
    """
    
    # Minimal set for Phase 1
    ALLOWED_FUNCS = {"RECT", "COMMIT", "SLEEP", "DAC_WRITE"}
    # Extended set for future expansion
    EXTENDED_FUNCS = {"INTEGRATE", "FILTER", "MULTIPLY", "SUM", "SYNC_ROW"}
    
    # Safe binary operations
    BINOPS = {
        ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
        ast.Pow: operator.pow
    }
    
    # Safe unary operations
    UNOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}

    def __init__(self, enable_extended=False):
        self.env: Dict[str, Any] = {}
        self.program: List[Dict[str, Any]] = []
        self.allowed_ops = self.ALLOWED_FUNCS.copy()
        if enable_extended:
            self.allowed_ops.update(self.EXTENDED_FUNCS)

    def eval_safe(self, node: ast.AST) -> Any:
        """Safely evaluate AST expressions"""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float, str, bool, type(None))):
                return node.value
            raise ValidationError(f"Unsupported constant type at line {node.lineno}")
        
        if isinstance(node, ast.Name):
            if node.id in self.env:
                return self.env[node.id]
            raise ValidationError(f"Unknown variable '{node.id}' at line {node.lineno}")
        
        if isinstance(node, ast.BinOp) and type(node.op) in self.BINOPS:
            left = self.eval_safe(node.left)
            right = self.eval_safe(node.right)
            return self.BINOPS[type(node.op)](left, right)
        
        if isinstance(node, ast.UnaryOp) and type(node.op) in self.UNOPS:
            operand = self.eval_safe(node.operand)
            return self.UNOPS[type(node.op)](operand)
        
        if isinstance(node, ast.List):
            return [self.eval_safe(e) for e in node.elts]
        
        if isinstance(node, ast.Tuple):
            return tuple(self.eval_safe(e) for e in node.elts)
        
        raise ValidationError(f"Unsafe expression at line {node.lineno}")

    def visit_Assign(self, node: ast.Assign):
        """Handle variable assignments"""
        try:
            val = self.eval_safe(node.value)
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    self.env[tgt.id] = val
                else:
                    raise ValidationError(f"Only simple names allowed on LHS at line {node.lineno}")
        except Exception as e:
            raise ValidationError(f"Assignment error at line {node.lineno}: {e}")

    def _call_name(self, node: ast.Call) -> str:
        """Extract function name from call node"""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                # Handle ViewerAdapter.FUNC or VA.FUNC calls
                return node.func.attr
        return ""

    def visit_Expr(self, node: ast.Expr):
        """Handle expression statements"""
        if isinstance(node.value, ast.Call):
            self._handle_call(node.value)

    def _handle_call(self, call: ast.Call):
        """Process function calls to ViewerAdapter methods"""
        name = self._call_name(call).upper()
        
        if name not in self.allowed_ops:
            return  # Ignore unsupported calls safely
        
        try:
            args = [self.eval_safe(arg) for arg in call.args]
            kwargs = {kw.arg: self.eval_safe(kw.value) for kw in call.keywords if kw.arg}
            
            if name == "RECT":
                self._process_rect(args, kwargs, call.lineno)
            elif name == "COMMIT":
                self._process_commit(args, call.lineno)
            elif name == "SLEEP":
                self._process_sleep(args, call.lineno)
            elif name == "DAC_WRITE":
                self._process_dac_write(args, call.lineno)
            elif name == "INTEGRATE":
                self._process_integrate(args, call.lineno)
            elif name == "FILTER":
                self._process_filter(args, call.lineno)
            elif name == "MULTIPLY":
                self._process_multiply(args, call.lineno)
            elif name == "SUM":
                self._process_sum(args, call.lineno)
            elif name == "SYNC_ROW":
                self._process_sync_row(args, call.lineno)
                
        except ValueError as e:
            raise ValidationError(f"Invalid argument type at line {call.lineno}: {e}")
        except Exception as e:
            raise ValidationError(f"Error processing {name} at line {call.lineno}: {e}")

    def _process_rect(self, args: List[Any], kwargs: Dict[str, Any], lineno: int):
        """Process RECT operation"""
        if len(args) < 5:
            raise ValidationError(f"RECT requires at least 5 args at line {lineno}")
        
        x, y, w, h, gray = args[:5]
        
        # Handle optional RGB arguments
        r = args[5] if len(args) > 5 else kwargs.get("r", gray)
        g = args[6] if len(args) > 6 else kwargs.get("g", gray)  
        b = args[7] if len(args) > 7 else kwargs.get("b", gray)
        
        # Clamp values to valid ranges
        def clamp(v, lo, hi): 
            return max(lo, min(hi, int(v)))
        
        self.program.append({
            "op": "RECT",
            "x": clamp(x, 0, 255),
            "y": clamp(y, 0, 255),
            "w": clamp(w, 0, 255),
            "h": clamp(h, 0, 255),
            "r": clamp(r, 0, 255),
            "g": clamp(g, 0, 255),
            "b": clamp(b, 0, 255)
        })

    def _process_commit(self, args: List[Any], lineno: int):
        """Process COMMIT operation"""
        if len(args) != 0:
            raise ValidationError(f"COMMIT takes no args at line {lineno}")
        self.program.append({"op": "COMMIT"})

    def _process_sleep(self, args: List[Any], lineno: int):
        """Process SLEEP operation"""
        if len(args) != 1:
            raise ValidationError(f"SLEEP requires 1 arg at line {lineno}")
        self.program.append({"op": "SLEEP", "ms": int(args[0])})

    def _process_dac_write(self, args: List[Any], lineno: int):
        """Process DAC_WRITE operation"""
        if len(args) != 2:
            raise ValidationError(f"DAC_WRITE requires 2 args at line {lineno}")
        
        def clamp(v, lo, hi): 
            return max(lo, min(hi, int(v)))
            
        ch = clamp(args[0], 0, 7)
        val = clamp(args[1], 0, 255)
        
        self.program.append({
            "op": "DAC_WRITE", 
            "ch": ch, 
            "val": val
        })

    def _process_integrate(self, args: List[Any], lineno: int):
        """Process INTEGRATE operation"""
        if len(args) != 3:
            raise ValidationError(f"INTEGRATE requires 3 args at line {lineno}")
        tau, src, dst = args
        self.program.append({
            "op": "INTEGRATE",
            "tau": float(tau),
            "src": int(src),
            "dst": int(dst)
        })

    def _process_filter(self, args: List[Any], lineno: int):
        """Process FILTER operation"""
        if len(args) != 4:
            raise ValidationError(f"FILTER requires 4 args at line {lineno}")
        filter_type, fc, src, dst = args
        self.program.append({
            "op": "FILTER",
            "type": str(filter_type),
            "fc": int(fc),
            "src": int(src),
            "dst": int(dst)
        })

    def _process_multiply(self, args: List[Any], lineno: int):
        """Process MULTIPLY operation"""
        if len(args) != 3:
            raise ValidationError(f"MULTIPLY requires 3 args at line {lineno}")
        gain, src, dst = args
        self.program.append({
            "op": "MULTIPLY",
            "gain": float(gain),
            "src": int(src),
            "dst": int(dst)
        })

    def _process_sum(self, args: List[Any], lineno: int):
        """Process SUM operation"""
        if len(args) != 2:
            raise ValidationError(f"SUM requires 2 args at line {lineno}")
        inputs, output = args
        
        # Ensure inputs is a list
        if not isinstance(inputs, list):
            inputs = [inputs]
        
        self.program.append({
            "op": "SUM",
            "inputs": [int(i) for i in inputs],
            "output": int(output)
        })

    def _process_sync_row(self, args: List[Any], lineno: int):
        """Process SYNC_ROW operation"""
        if len(args) != 1:
            raise ValidationError(f"SYNC_ROW requires 1 arg at line {lineno}")
        self.program.append({"op": "SYNC_ROW", "i": int(args[0])})

    def to_hlir(self) -> Dict[str, Any]:
        """Convert accumulated operations to HLIR format"""
        return {
            "schemaVersion": "pxos-ops/1.0",
            "meta": {
                "profile": "default",
                "cols": 16
            },
            "program": self.program
        }

def T_py_to_hlir(code: str, enable_extended: bool = False) -> Dict[str, Any]:
    """
    Transform Python code to PXOS HLIR using AST parsing.
    
    Args:
        code: Python source code using ViewerAdapter calls
        enable_extended: Enable extended operation set (INTEGRATE, FILTER, etc.)
        
    Returns:
        PXOS HLIR as a dictionary
    """
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as e:
        raise ValidationError(f"Python syntax error: {e.msg} at line {e.lineno}:{e.offset}")
    
    transpiler = PyToHLIR(enable_extended=enable_extended)
    
    for node in tree.body:
        transpiler.visit(node)
    
    return transpiler.to_hlir()

if __name__ == "__main__":
    # Test the transpiler
    test_code = """
import viewer_adapter as VA

# Simple test program
width = 40
height = 20

VA.RECT(20, 20, width, height, 64)
VA.SLEEP(30)
VA.DAC_WRITE(1, 180)
VA.COMMIT()
"""
    
    try:
        hlir = T_py_to_hlir(test_code)
        import json
        print(json.dumps(hlir, indent=2))
    except ValidationError as e:
        print(f"Validation error: {e}")