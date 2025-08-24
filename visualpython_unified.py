"""
VisualPython Unified Engine — v0.7 (headless-safe)

Merged features:
- Backend abstraction: auto-selects tkinter if available, otherwise falls back to a 24-bit ANSI terminal renderer.
- Minimal draw API (set_pixel/rect/text/clear/commit/SPACE) for immediate-mode Python → screen.
- AST-driven execution (assignments, print, for range, if/elif/else) with optional loop-body stepping.
- Keyframe-5 font grid and optional boot sequence overlay.
- CLI modes: run, live, step, raw, info, and a new `selftest` command.

Quickstart
---------
# Run with auto-detected backend (will use ANSI in this environment)
python visualpython_unified.py run demo.py

# Force a specific backend
python visualpython_unified.py live demo.py --backend ansi

# Step through loops (press Enter or Space in ANSI mode)
python visualpython_unified.py step demo_loops.py --backend ansi

# Run a self-test to check the renderer
python visualpython_unified.py selftest --backend ansi
"""
from __future__ import annotations
import ast, os, time, argparse, traceback, math, types, sys, select
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# -------------------------
# Renderer Abstraction & Implementations
# -------------------------
BG = "#001100"

class Renderer:
    def __init__(self, width:int, height:int, scale:int, title:str):
        self.w, self.h, self.scale, self.title = width, height, scale, title
    def space(self) -> bool: raise NotImplementedError
    def clear(self, color: str = BG): raise NotImplementedError
    def set_pixel(self, x:int, y:int, r:int, g:int, b:int): raise NotImplementedError
    def rect(self, x:int, y:int, w:int, h:int, r:int, g:int, b:int): raise NotImplementedError
    def text(self, x:int, y:int, msg:str, r:int=144, g:int=238, b:int=144): raise NotImplementedError
    def commit(self): raise NotImplementedError
    def close(self): pass

class TkRenderer(Renderer):
    def __init__(self, width:int=800, height:int=600, scale:int=2, title:str="VisualPython"):
        super().__init__(width, height, scale, title)
        try:
            import tkinter as tk
            self.tk = tk
        except ImportError:
            raise RuntimeError("tkinter is not available")
        self.root = self.tk.Tk(); self.root.title(title)
        self.cv = self.tk.Canvas(self.root, width=width*scale, height=height*scale,
                                 bg=BG, highlightthickness=0)
        self.cv.pack()
        self._batch: List[Tuple[int,int,int,int,str]] = []
        self._space = False
        self.root.bind("<space>", lambda e: self._set_space())
    def _set_space(self): self._space = True
    def space(self) -> bool: v = self._space; self._space = False; return v
    def clear(self, color: str = BG): self.cv.delete("all"); self.cv.configure(bg=color)
    def set_pixel(self, x:int, y:int, r:int, g:int, b:int):
        if 0 <= x < self.w and 0 <= y < self.h:
            s = self.scale; c=f"#{r:02x}{g:02x}{b:02x}"
            self._batch.append((x*s, y*s, (x+1)*s, (y+1)*s, c))
    def rect(self, x:int, y:int, w:int, h:int, r:int, g:int, b:int):
        s=self.scale; c=f"#{r:02x}{g:02x}{b:02x}"
        self.cv.create_rectangle(x*s, y*s, (x+w)*s, (y+h)*s, outline="", fill=c)
    def text(self, x:int, y:int, msg:str, r:int=144, g:int=238, b:int=144):
        c=f"#{r:02x}{g:02x}{b:02x}"; self.cv.create_text(x*self.scale, y*self.scale,
            anchor="nw", text=str(msg), fill=c, font=("Courier", 10))
    def commit(self):
        if self._batch:
            for x0,y0,x1,y1,c in self._batch:
                self.cv.create_rectangle(x0,y0,x1,y1, outline="", fill=c)
            self._batch.clear()
        self.root.update_idletasks(); self.root.update()
    def close(self):
        try: self.root.destroy()
        except Exception: pass

class AnsiRenderer(Renderer):
    def __init__(self, width:int=80, height:int=40, scale:int=1, title:str=""):
        super().__init__(width, height, scale, title)
        self.buffer = [[' ' for _ in range(width)] for _ in range(height)]
    def space(self) -> bool:
        return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []) and sys.stdin.read(1) in (' ', '\n')
    def clear(self, color: str = BG): sys.stdout.write("\033[2J\033[H")
    def set_pixel(self, x:int, y:int, r:int, g:int, b:int): self.rect(x,y,1,1,r,g,b)
    def rect(self, x:int, y:int, w:int, h:int, r:int, g:int, b:int):
        sys.stdout.write(f"\033[48;2;{r};{g};{b}m")
        for i in range(h):
            sys.stdout.write(f"\033[{y+i+1};{x+1}H")
            sys.stdout.write(" " * w)
        sys.stdout.write("\033[0m")
    def text(self, x:int, y:int, msg:str, r:int=144, g:int=238, b:int=144):
        sys.stdout.write(f"\033[38;2;{r};{g};{b}m")
        sys.stdout.write(f"\033[{y+1};{x+1}H{msg}")
        sys.stdout.write("\033[0m")
    def commit(self): sys.stdout.flush()

# ... (FONT_5x7 and draw functions remain the same, but accept a Renderer instance)
FONT_5x7: Dict[str, List[int]] = {
    'A':[0x0E,0x11,0x1F,0x11,0x11], 'B':[0x1E,0x11,0x1E,0x11,0x1E],
    'C':[0x0E,0x11,0x10,0x11,0x0E], 'D':[0x1E,0x11,0x11,0x11,0x1E],
    'E':[0x1F,0x10,0x1E,0x10,0x1F], 'F':[0x1F,0x10,0x1E,0x10,0x10],
    'G':[0x0E,0x11,0x13,0x11,0x0E], 'H':[0x11,0x11,0x1F,0x11,0x11],
    'I':[0x0E,0x04,0x04,0x04,0x0E], 'J':[0x07,0x01,0x01,0x11,0x0E],
    'K':[0x11,0x12,0x1C,0x12,0x11], 'L':[0x10,0x10,0x10,0x10,0x1F],
    'M':[0x11,0x1B,0x15,0x11,0x11], 'N':[0x11,0x19,0x15,0x13,0x11],
    'O':[0x0E,0x11,0x11,0x11,0x0E], 'P':[0x1E,0x11,0x1E,0x10,0x10],
    'Q':[0x0E,0x11,0x11,0x15,0x0E], 'R':[0x1E,0x11,0x1E,0x14,0x13],
    'S':[0x0F,0x10,0x0E,0x01,0x1E], 'T':[0x1F,0x04,0x04,0x04,0x04],
    'U':[0x11,0x11,0x11,0x11,0x0E], 'V':[0x11,0x11,0x11,0x0A,0x04],
    'W':[0x11,0x11,0x15,0x1B,0x11], 'X':[0x11,0x0A,0x04,0x0A,0x11],
    'Y':[0x11,0x0A,0x04,0x04,0x04], 'Z':[0x1F,0x02,0x04,0x08,0x1F],
    '0':[0x0E,0x13,0x15,0x19,0x0E], '1':[0x04,0x0C,0x04,0x04,0x0E],
    '2':[0x0E,0x11,0x02,0x08,0x1F], '3':[0x1F,0x02,0x06,0x01,0x1E],
    '4':[0x02,0x06,0x0A,0x1F,0x02], '5':[0x1F,0x10,0x1E,0x01,0x1E],
    '6':[0x06,0x08,0x1E,0x11,0x0E], '7':[0x1F,0x01,0x02,0x04,0x08],
    '8':[0x0E,0x11,0x0E,0x11,0x0E], '9':[0x0E,0x11,0x0F,0x02,0x0C],
    ' ':[0x00,0x00,0x00,0x00,0x00], '!':[0x04,0x04,0x04,0x00,0x04],
    ':':[0x00,0x04,0x00,0x04,0x00], '.':[0x00,0x00,0x00,0x00,0x04],
    ',':[0x00,0x00,0x00,0x04,0x08], '-':[0x00,0x00,0x1F,0x00,0x00],
}

def draw_glyph(r: Renderer, ch: str, x:int, y:int, scale:int=2, color=(144,238,144)):
    bits = FONT_5x7.get(ch.upper(), FONT_5x7[' '])
    rr,gg,bb = color
    for cx, col in enumerate(bits):
        for row in range(7):
            if col & (1 << (6-row)):
                if isinstance(r, AnsiRenderer):
                    r.rect(x+cx, y+row, 1, 1, rr,gg,bb)
                else:
                    r.rect(x+cx*scale, y+row*scale, scale, scale, rr,gg,bb)

def draw_text_bitmap(r: Renderer, text:str, x:int, y:int, scale:int=2, color=(144,238,144)):
    ox = x
    for ch in text:
        draw_glyph(r, ch, ox, y, scale, color)
        ox += 6* (1 if isinstance(r, AnsiRenderer) else scale)

# ... (DrawAPI, MiniEvaluator, VisualPythonEngine, CLI updated to use the renderer instance)

class DrawAPI:
    def __init__(self, r: Renderer):
        self.r = r
    def set_pixel(self, x:int,y:int,r:int,g:int,b:int): self.r.set_pixel(x,y,r,g,b)
    def rect(self, x:int,y:int,w:int,h:int,r:int,g:int,b:int): self.r.rect(x,y,w,h,r,g,b)
    def text(self, x:int,y:int,msg:str,r:int=144,g:int=238,b:int=144): self.r.text(x,y,msg,r,g,b)
    def clear(self, color: str = BG): self.r.clear(color)
    def commit(self): self.r.commit()
    def SPACE(self) -> bool: return self.r.space()

@dataclass
class ExecOptions:
    step_loops: bool = False
    boot_banner: bool = False
    display_mode: Optional[str] = None

class MiniEvaluator(ast.NodeVisitor):
    def __init__(self, env: Dict[str, Any]):
        self.env = env
    def visit_Constant(self, node: ast.Constant): return node.value
    def visit_Name(self, node: ast.Name):
        if node.id in self.env:
            return self.env[node.id]
        builtins = self.env.get("__builtins__", {})
        if isinstance(builtins, dict) and node.id in builtins:
            return builtins[node.id]
        return None
    def visit_BinOp(self, node: ast.BinOp):
        l = self.visit(node.left); r = self.visit(node.right)
        if isinstance(node.op, ast.Add): return l + r
        if isinstance(node.op, ast.Sub): return l - r
        if isinstance(node.op, ast.Mult): return l * r
        if isinstance(node.op, ast.Div): return l / r
        if isinstance(node.op, ast.FloorDiv): return l // r
        if isinstance(node.op, ast.Mod): return l % r
        raise RuntimeError("Unsupported binop")
    def visit_Compare(self, node: ast.Compare):
        left = self.visit(node.left)
        ok = True; cur = left
        for op, comp in zip(node.ops, node.comparators):
            val = self.visit(comp)
            if isinstance(op, ast.Gt): ok = ok and (cur > val)
            elif isinstance(op, ast.Lt): ok = ok and (cur < val)
            elif isinstance(op, ast.Eq): ok = ok and (cur == val)
            elif isinstance(op, ast.NotEq): ok = ok and (cur != val)
            elif isinstance(op, ast.GtE): ok = ok and (cur >= val)
            elif isinstance(op, ast.LtE): ok = ok and (cur <= val)
            else: raise RuntimeError("Unsupported compare op")
            cur = val
        return ok
    def visit_Call(self, node: ast.Call):
        fn = self.visit(node.func)
        args = [self.visit(a) for a in node.args]
        kwargs = {kw.arg: self.visit(kw.value) for kw in node.keywords}
        return fn(*args, **kwargs)

class VisualPythonEngine:
    def __init__(self, backend_choice:str, width=800, height=600, scale=2, title="VisualPython"):
        if backend_choice == 'tk':
            try:
                self.r: Renderer = TkRenderer(width, height, scale, title)
            except Exception:
                print("Tkinter not available, falling back to ANSI.")
                self.r: Renderer = AnsiRenderer(width//10, height//15)
        elif backend_choice == 'ansi':
            self.r: Renderer = AnsiRenderer(width//10, height//15)
        else:
            raise ValueError(f"Unknown backend: {backend_choice}")

        self.api = DrawAPI(self.r)

    def run_selftest(self):
        self.r.clear()
        self.r.text(1, 1, "SELF TEST", 255, 255, 0)
        self.r.rect(1, 3, 10, 5, 0, 0, 255)
        for i in range(10):
            self.r.set_pixel(15+i, 5, 255, 255, 255)
        self.r.commit()

    # ... (rest of the engine code is the same, just uses self.r)
    def _boot_banner(self):
        self.r.clear()
        draw_text_bitmap(self.r, "BOOTING", 2, 2, 1, (255,255,0))
        self.r.commit(); time.sleep(0.18)
        self.r.clear(); draw_text_bitmap(self.r, "INIT SYSTEM", 2, 2, 1, (255,255,0))
        self.r.commit(); time.sleep(0.18)
        self.r.clear(); draw_text_bitmap(self.r, "LOAD DRIVERS", 2, 2, 1, (255,255,0))
        self.r.commit(); time.sleep(0.18)
        self.r.clear(); draw_text_bitmap(self.r, "READY", 2, 2, 1, (0,255,0))
        self.r.commit(); time.sleep(0.14)

    def _font_grid(self):
        self.r.clear()
        draw_text_bitmap(self.r, "FONT SYSTEM LOADED", 2, 1, 1, (255,255,255))
        cols=16; sx=2; sy=4; sc=1
        keys = list(FONT_5x7.keys())
        keys.sort()
        for idx,ch in enumerate(keys):
            gx = sx + (idx % cols) * (6*sc + 2)
            gy = sy + (idx // cols) * (8*sc)
            draw_glyph(self.r, ch, gx, gy, sc)
        self.r.commit()

    def _base_env(self) -> Dict[str, Any]:
        # Expose draw API and some constants
        env: Dict[str, Any] = {
            "set_pixel": self.api.set_pixel, "rect": self.api.rect, "text": self.api.text,
            "clear": self.api.clear, "commit": self.api.commit, "SPACE": self.api.SPACE,
            "WIDTH": self.r.w, "HEIGHT": self.r.h, "math": math,
            "__builtins__": {"range": range, "min": min, "max": max, "abs": abs, "int": int, "float": float, "str": str, "print": print},
        }
        return env

    def exec_raw(self, code:str):
        env = self._base_env()
        self.r.clear()
        try:
            exec(compile(code, "<raw>", "exec"), env, env)
        except Exception:
            self.r.text(1,1, "EXCEPTION:", 255,80,80); self.r.text(1,2, traceback.format_exc(), 255,160,160)
        self.r.commit()

    def exec_ast(self, code:str, opts: ExecOptions):
        self.r.clear()
        env = self._base_env()
        try:
            tree = ast.parse(code)
        except SyntaxError:
            self.r.text(1,1, "SYNTAX ERROR", 255,80,80); self.r.text(1,2, traceback.format_exc(), 255,160,160)
            self.r.commit(); return

        if opts.boot_banner: self._boot_banner()
        if opts.display_mode == "font_grid": self._font_grid()

        ev = MiniEvaluator(env)
        def run_block(stmts: List[ast.stmt]):
            for stmt in stmts: self._exec_stmt(stmt, env, ev, opts)
        try:
            run_block(tree.body)
        except Exception:
            self.r.text(1,1, "EXCEPTION:", 255,80,80); self.r.text(1,2, traceback.format_exc(), 255,160,160)
        self.r.commit()

    def _exec_stmt(self, stmt: ast.stmt, env: Dict[str,Any], ev: MiniEvaluator, opts: ExecOptions):
        if isinstance(stmt, ast.Assign):
            if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                env[stmt.targets[0].id] = ev.visit(stmt.value)
        elif isinstance(stmt, ast.Expr):
            ev.visit(stmt.value)
        elif isinstance(stmt, ast.For):
            if isinstance(stmt.iter, ast.Call) and isinstance(stmt.iter.func, ast.Name) and stmt.iter.func.id == 'range':
                args = [ev.visit(a) for a in stmt.iter.args]
                seq = range(*args)
                itvar = stmt.target.id if isinstance(stmt.target, ast.Name) else None
                for i in seq:
                    if itvar: env[itvar] = i
                    if opts.step_loops:
                        self.r.text(1, 1, f"STEP i={i}", 180,220,255); self.r.commit()
                        while not self.r.space(): time.sleep(0.01); self.r.commit()
                    for sub in stmt.body: self._exec_stmt(sub, env, ev, opts)
        elif isinstance(stmt, ast.If):
            block = stmt.body if ev.visit(stmt.test) else stmt.orelse
            for sub in block: self._exec_stmt(sub, env, ev, opts)

def main():
    def _read(path:str) -> str:
        with open(path, 'r', encoding='utf-8') as f: return f.read()
    ap = argparse.ArgumentParser(prog="visualpython_unified", description="VisualPython Unified Engine")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_common(p):
        p.add_argument("script", nargs='?', default=None)
        p.add_argument("--backend", choices=['tk', 'ansi'], default='tk')
        p.add_argument("--width", type=int, default=800); p.add_argument("--height", type=int, default=600)
        p.add_argument("--scale", type=int, default=2); p.add_argument("--boot", action="store_true")
        p.add_argument("--font-grid", action="store_true")

    p_run = sub.add_parser("run", help="AST: run once"); add_common(p_run)
    p_live = sub.add_parser("live", help="AST: live reload on save"); add_common(p_live); p_live.add_argument("--interval", type=float, default=0.2)
    p_step = sub.add_parser("step", help="AST: live + step loop bodies"); add_common(p_step)
    p_raw = sub.add_parser("raw", help="RAW: execute script using draw API"); add_common(p_raw); p_raw.add_argument("--live", action="store_true"); p_raw.add_argument("--interval", type=float, default=0.2)
    p_info = sub.add_parser("info", help="Show help for the draw API")
    p_selftest = sub.add_parser("selftest", help="Run a backend self-test"); p_selftest.add_argument("--backend", choices=['tk', 'ansi'], default='tk')

    args = ap.parse_args()

    if args.cmd == "info":
        print("Draw API available to your scripts: set_pixel, rect, text, clear, commit, SPACE, WIDTH, HEIGHT")
        return

    engine = VisualPythonEngine(args.backend, getattr(args, 'width', 800), getattr(args, 'height', 600), getattr(args, 'scale', 2), "VisualPython")

    if args.cmd == "selftest":
        engine.run_selftest()
        time.sleep(2)
        return

    opts = ExecOptions(boot_banner=args.boot, display_mode="font_grid" if args.font_grid else None)

    if args.cmd == "run":
        engine.exec_ast(_read(args.script), opts)
        if args.backend == 'tk':
            while True:
                try:
                    engine.r.commit()
                    time.sleep(0.016)
                except Exception:
                    break
    elif args.cmd == "live":
        last = 0.0
        while True:
            try:
                m = os.path.getmtime(args.script)
                if m != last: last = m; engine.exec_ast(_read(args.script), opts)
                time.sleep(args.interval)
            except FileNotFoundError: engine.r.clear(); engine.r.text(1,1,"Waiting...",255,200,0); engine.r.commit(); time.sleep(args.interval)
    elif args.cmd == "step":
        opts.step_loops = True
        last = 0.0
        while True:
            try:
                m = os.path.getmtime(args.script)
                if m != last: last = m; engine.exec_ast(_read(args.script), opts)
                time.sleep(0.1)
            except FileNotFoundError: engine.r.clear(); engine.r.text(1,1,"Waiting...",255,200,0); engine.r.commit(); time.sleep(0.1)
    elif args.cmd == "raw":
        last = 0.0
        if not args.live:
            engine.exec_raw(_read(args.script))
            while True: engine.r.commit(); time.sleep(0.016)
        else:
            while True:
                try:
                    m = os.path.getmtime(args.script)
                    if m != last: last = m; engine.exec_raw(_read(args.script))
                    time.sleep(args.interval)
                except FileNotFoundError: engine.r.clear(); engine.r.text(1,1,"Waiting...",255,200,0); engine.r.commit(); time.sleep(args.interval)

if __name__ == "__main__":
    main()
