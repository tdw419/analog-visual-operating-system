import dis
import io
import sys
from math import *
from types import SimpleNamespace
from PIL import Image, ImageDraw, ImageFont

# ------------------------------
# Safe environment (whitelist)
# ------------------------------
def _whitelist_math():
    import math
    allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
    # Handy builtins
    allowed.update({
        "abs": abs, "round": round, "min": min, "max": max, "pow": pow,
        "int": int, "float": float, "complex": complex,
        # common constants already included from math, but ensure presence:
        "pi": math.pi, "e": math.e, "tau": math.tau,
    })
    return allowed

ALLOWED = _whitelist_math()

class VisualCalcVM:
    """Tiny bytecode VM tuned for calculator use (Python 3.11+ friendly)."""
    def __init__(self):
        self.stack = []
        self.vars = {"Ans": 0}
        self.exec_log = []  # for visualization

    def _jump_to(self, target_offset, offset_to_index, nins):
        return offset_to_index.get(target_offset, nins)

    def run(self, code_str, mode="auto"):
        """Execute code_str. Returns (value, stdout_str).
        mode: 'eval', 'exec', or 'auto' (detect).
        """
        # Detect mode
        detected_mode = mode
        if mode == "auto":
            detected_mode = "eval" if self._looks_like_expr(code_str) else "exec"

        # Compile
        co = compile(code_str, "<calc>", detected_mode)
        instructions = list(dis.get_instructions(co))
        offset_to_index = {ins.offset: i for i, ins in enumerate(instructions)}
        ip = 0
        nins = len(instructions)

        # Prepare stdout capture
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            while ip < nins:
                ins = instructions[ip]
                op = ins.opname
                self.exec_log.append((ip, op, ins.argval))

                # --- No-ops / housekeeping for 3.11 ---
                if op in ("RESUME", "CACHE", "EXTENDED_ARG"):
                    ip += 1

                # --- Constants & names ---
                elif op == "LOAD_CONST":
                    self.stack.append(ins.argval); ip += 1
                elif op in ("LOAD_NAME", "LOAD_GLOBAL"):
                    name = ins.argval
                    if name in self.vars:
                        self.stack.append(self.vars[name])
                    elif name in ALLOWED:
                        self.stack.append(ALLOWED[name])
                    elif name == "__builtins__":  # some code objects may try to load this; block
                        raise NameError("access to __builtins__ is not allowed")
                    else:
                        raise NameError(f"name '{name}' is not defined (or not allowed)")
                    ip += 1
                elif op == "STORE_NAME":
                    self.vars[ins.argval] = self.stack.pop(); ip += 1

                # --- Unary ops ---
                elif op == "UNARY_NEGATIVE":
                    self.stack.append(-self.stack.pop()); ip += 1
                elif op == "UNARY_POSITIVE":
                    self.stack.append(+self.stack.pop()); ip += 1
                elif op == "UNARY_NOT":
                    self.stack.append(not self.stack.pop()); ip += 1

                # --- Binary ops (3.11 unified) ---
                elif op == "BINARY_OP":
                    b, a = self.stack.pop(), self.stack.pop()
                    sym = ins.argrepr  # operator symbol, e.g. "+", "-", "*", "/", "//", "%", "**", "@"
                    if sym == '+':   self.stack.append(a + b)
                    elif sym == '-': self.stack.append(a - b)
                    elif sym == '*': self.stack.append(a * b)
                    elif sym == '/': self.stack.append(a / b)
                    elif sym == '//': self.stack.append(a // b)
                    elif sym == '%': self.stack.append(a % b)
                    elif sym == '**': self.stack.append(a ** b)
                    elif sym == '@':
                        if hasattr(a, '__matmul__'): self.stack.append(a @ b)
                        else: raise TypeError("@ not supported for operands")
                    else:
                        raise NotImplementedError(f"BINARY_OP {sym}")
                    ip += 1
                # Legacy add/mul for older versions (harmless if unused)
                elif op == "BINARY_ADD":
                    b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a + b); ip += 1
                elif op == "BINARY_MULTIPLY":
                    b, a = self.stack.pop(), self.stack.pop(); self.stack.append(a * b); ip += 1

                # --- Comparisons ---
                elif op == "COMPARE_OP":
                    b, a = self.stack.pop(), self.stack.pop()
                    cmp = ins.argrepr
                    res = {
                        '==': a == b, '!=': a != b, '<': a < b,  '<=': a <= b,
                        '>': a > b,  '>=': a >= b, 'in': a in b, 'not in': a not in b,
                        'is': a is b, 'is not': a is not b
                    }[cmp]
                    self.stack.append(res); ip += 1

                # --- Jumps ---
                elif op in ("POP_JUMP_FORWARD_IF_FALSE", "POP_JUMP_BACKWARD_IF_FALSE"):
                    cond = self.stack.pop()
                    if not cond:
                        ip = self._jump_to(ins.argval, offset_to_index, nins)
                    else:
                        ip += 1
                elif op in ("POP_JUMP_FORWARD_IF_TRUE", "POP_JUMP_BACKWARD_IF_TRUE"):
                    cond = self.stack.pop()
                    if cond:
                        ip = self._jump_to(ins.argval, offset_to_index, nins)
                    else:
                        ip += 1
                elif op in ("JUMP_FORWARD", "JUMP_BACKWARD", "JUMP_ABSOLUTE"):
                    ip = self._jump_to(ins.argval, offset_to_index, nins)

                # --- Calls (3.11 pattern) ---
                elif op == "PUSH_NULL":
                    self.stack.append(None); ip += 1
                elif op == "PRECALL":
                    ip += 1  # no-op
                elif op == "CALL":
                    argc = ins.arg
                    args = [self.stack.pop() for _ in range(argc)][::-1]
                    func = self.stack.pop()
                    # Only allow whitelisted functions or user-defined callables in vars
                    if func in ALLOWED.values() or any((k for k,v in self.vars.items() if v is func)):
                        result = func(*args)
                        self.stack.append(result)
                    elif func is print:
                        print(*args); self.stack.append(None)
                    else:
                        raise PermissionError("function call not allowed in calculator")
                    ip += 1

                # --- Stack / return ---
                elif op == "POP_TOP":
                    if self.stack: self.stack.pop()
                    ip += 1
            elif op == "RETURN_CONST":
                self.stack.append(ins.argval)
                break
                elif op == "RETURN_VALUE":
                    break

                else:
                    raise NotImplementedError(f"Opcode not supported: {op}")
        finally:
            out = sys.stdout.getvalue()
            sys.stdout = old_stdout

        # Value to return: top of stack if present (eval mode), else None
        value = self.stack[-1] if self.stack else None
        self.vars["Ans"] = value if value is not None else self.vars.get("Ans", None)
        return value, out

    def _looks_like_expr(self, s):
        # Heuristic: if there's an '=' at top level, treat as exec; else eval
        # This is simplistic but fine for calculator usage
        return '=' not in s.strip().split('#', 1)[0]  # ignore comments


# ------------------------------
# 4-pane artifact rendering
# ------------------------------
def render_4pane(expr, vm: VisualCalcVM, outfile):
    # Compile & disassemble
    co = compile(expr, "<calc-pane>", "eval" if vm._looks_like_expr(expr) else "exec")
    instructions = list(dis.get_instructions(co))

    # Execute via VM
    vm.exec_log.clear()
    val, out = vm.run(expr, mode="auto")

    W, H = 1400, 900
    img = Image.new("RGB", (W, H), "#0a0f1a")
    d = ImageDraw.Draw(img)
    try:
        font_code = ImageFont.truetype("DejaVuSansMono.ttf", 28)
        font_ui = ImageFont.truetype("DejaVuSans.ttf", 16)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 14)
    except:
        font_code = ImageFont.load_default()
        font_ui = ImageFont.load_default()
        font_small = ImageFont.load_default()

    def pane(x, y, w, h, title):
        d.rounded_rectangle([x, y, x+w, y+h], radius=14, fill="#0b1220", outline="#1f2a44", width=2)
        d.text((x+14, y-24), title, fill="#a5b4fc", font=font_ui)
        return (x, y, x+w, y+h)

    P = []
    gap = 18
    w = (W - gap*3)//2
    h = (H - gap*3)//2
    P.append(pane(gap, gap*2, w, h, "Pane 1 — Source"))
    P.append(pane(gap*2+w, gap*2, w, h, "Pane 2 — Pixelized text"))
    P.append(pane(gap, gap*3+h, w, h, "Pane 3 — Bytecode tiles"))
    P.append(pane(gap*2+w, gap*3+h, w, h, "Pane 4 — Result"))

    # Pane 1: source
    x0, y0, x1, y1 = P[0]
    y = y0+20
    for line in expr.splitlines() or ['']:
        d.text((x0+20, y), line, fill="#e2e8f0", font=font_code)
        y += 34

    # Pane 2: pixelized text
    x0, y0, x1, y1 = P[1]
    cell_w, cell_h = 18, 24
    gx, gy = x0+16, y0+16
    # grid
    for r, line in enumerate(expr.splitlines() or ['']):
        for c, ch in enumerate(line):
            cx, cy = gx + c*cell_w, gy + r*cell_h
            d.rectangle([cx, cy, cx+cell_w-2, cy+cell_h-2], fill="#1e293b")
            d.text((cx+3, cy+2), ch, fill="#c7d2fe", font=font_small)

    # Pane 3: bytecode tiles
    x0, y0, x1, y1 = P[2]
    tile = 48
    cols = max(1, (w-40)//(tile+6))
    ox, oy = x0+20, y0+24
    for i, ins in enumerate(instructions):
        cx = ox + (i%cols)*(tile+6)
        cy = oy + (i//cols)*(tile+6)
        color = {
            "LOAD_CONST": "#3b82f6",
            "LOAD_NAME": "#a855f7",
            "LOAD_GLOBAL": "#a855f7",
            "STORE_NAME": "#f97316",
            "BINARY_OP": "#ef4444",
            "COMPARE_OP": "#8b5cf6",
            "PRECALL": "#94a3b8",
            "CALL": "#10b981",
            "POP_TOP": "#f59e0b",
            "RETURN_VALUE": "#94a3b8",
            "PUSH_NULL": "#64748b",
        }.get(ins.opname, "#475569")
        d.rounded_rectangle([cx, cy, cx+tile, cy+tile], radius=10, fill=color)
        lab = ins.opname if ins.argval is None else f"{ins.opname}\n{ins.argval}"
        d.text((cx+tile/2, cy+tile/2), lab, anchor="mm", fill="#ffffff", font=font_small)

    # Pane 4: results
    x0, y0, x1, y1 = P[3]
    y = y0+16
    d.text((x0+16, y), "Output:", fill="#e2e8f0", font=font_ui); y+=22
    if out.strip():
        for line in out.strip().splitlines():
            d.text((x0+24, y), line, fill="#facc15", font=font_ui); y+=20
    else:
        d.text((x0+24, y), "(no stdout)", fill="#64748b", font=font_ui); y+=20
    y+=8
    d.text((x0+16, y), f"Result value: {val}", fill="#22c55e", font=font_ui); y+=22
    d.text((x0+16, y), f"Ans = {vm.vars.get('Ans')}", fill="#22c55e", font=font_ui); y+=22

    img.save(outfile)
    return outfile

# ------------------------------
# REPL
# ------------------------------
HELP = """
Commands:
  :help        show this help
  :vars        show variables (including Ans)
  :history     show past inputs/results
  :quit        exit
Examples:
  2+3*4
  sin(pi/2) + sqrt(9)
  x = 10
  2 * Ans
""".strip()

def repl():
    vm = VisualCalcVM()
    history = []
    print("Visual Calculator — type :help for help. Ctrl+C or :quit to exit.")
    while True:
        try:
            line = input("calc> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break
        if not line:
            continue
        if line.startswith(":"):
            cmd = line[1:].strip()
            if cmd == "help": print(HELP)
            elif cmd == "vars":
                for k,v in vm.vars.items():
                    print(f"{k} = {v}")
            elif cmd == "history":
                for i,(src,res) in enumerate(history,1):
                    print(f"{i:02d}: {src} => {res}")
            elif cmd == "quit":
                print("bye"); break
            else:
                print("unknown command; try :help")
            continue
        try:
            val, out = vm.run(line, mode="auto")
            if out.strip(): print(out.strip())
            if val is not None:
                print(val)
            history.append((line, val))
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    repl()
