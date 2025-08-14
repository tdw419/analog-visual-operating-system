#!/usr/bin/env python3
# px_cli.py — tiny helper for PXOS programs
# Commands:
#   py px_cli.py new "My First Program" [--dir examples|programs] [--force]
#   py px_cli.py list
#   py px_cli.py run examples/my_first_program.py [--steps 600] [--headless]
#   py px_cli.py validate [--all | --path examples/my_first_program.py]

from __future__ import annotations
import argparse, pathlib, re, sys, os, shutil, tempfile, subprocess, textwrap, datetime as _dt

ROOT = pathlib.Path(__file__).parent.resolve()
EXAMPLES = ROOT / "examples"
PROGRAMS = ROOT / "programs"
SIM = ROOT / "screen_native_sim.py"
VALIDATOR = ROOT / "program_host.py"

DEFAULT_AVG_MS = 1.5
DEFAULT_SPIKE_MS = 5.0

def snake(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "untitled"
    return s

def atomic_write(path: pathlib.Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = pathlib.Path(tempfile.mkstemp(dir=str(path.parent))[1])
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)

def default_template(mod_name: str) -> str:
    return textwrap.dedent(f"""\
    # {mod_name}.py — PXOS program scaffold
    # Hooks: setup(ctx), update(ctx, dt), on_event(ctx, ev) [optional]

    import time

    def setup(ctx):
        W, H = ctx["size"]
        ctx["x"] = W // 4
        ctx["y"] = H // 2
        ctx["vx"] = 140  # px/s
        ctx["count"] = 0
        ctx["debug"] = True
        ctx["ema_ms"] = 0.0

    def update(ctx, dt):
        import pygame, time
        surf = ctx["surface"]; W, H = ctx["size"]
        t0 = time.perf_counter()

        # update state
        ctx["x"] = (ctx["x"] + ctx["vx"] * dt) % W
        ctx["count"] += 1

        # draw
        surf.fill((0, 0, 0))
        pygame.draw.rect(surf, (80, 220, 140), (int(ctx["x"]), ctx["y"], 48, 12))

        # HUD (debug)
        if ctx["debug"]:
            upd_ms = (time.perf_counter() - t0) * 1000.0
            ctx["ema_ms"] = 0.9 * ctx["ema_ms"] + 0.1 * upd_ms
            ctx["draw_text"](surf, 8, 8, f"frames={{ctx['count']}} upd≈{{ctx['ema_ms']:.2f}}ms")

    def on_event(ctx, ev):
        if ev.get("type") == "key" and ev.get("down"):
            k = ev.get("key")
            if k == "space":
                ctx["vx"] = -ctx["vx"]
            elif k in ("+", "equals"):
                ctx["vx"] *= 1.1
            elif k in ("-", "underscore"):
                ctx["vx"] *= 0.9
            elif k == "f1":
                ctx["debug"] = not ctx["debug"]
    """)

def snake_template(mod_name: str) -> str:
    return textwrap.dedent(f"""\
    # {mod_name}.py — PXOS snake game
    # Hooks: setup(ctx), update(ctx, dt), on_event(ctx, ev)

    import pygame
    import random

    def setup(ctx):
        W, H = ctx["size"]
        ctx["snake"] = [(W // 2, H // 2)]
        ctx["direction"] = (1, 0)
        ctx["food"] = (random.randint(0, W - 1), random.randint(0, H - 1))
        ctx["score"] = 0

    def update(ctx, dt):
        W, H = ctx["size"]
        head = ctx["snake"][0]
        new_head = (head[0] + ctx["direction"][0], head[1] + ctx["direction"][1])

        if new_head[0] < 0 or new_head[0] >= W or new_head[1] < 0 or new_head[1] >= H or new_head in ctx["snake"]:
            # Game over
            return

        ctx["snake"].insert(0, new_head)

        if new_head == ctx["food"]:
            ctx["score"] += 1
            ctx["food"] = (random.randint(0, W - 1), random.randint(0, H - 1))
        else:
            ctx["snake"].pop()

        ctx["surface"].fill((0, 0, 0))
        for segment in ctx["snake"]:
            pygame.draw.rect(ctx["surface"], (0, 255, 0), (segment[0] * 10, segment[1] * 10, 10, 10))
        pygame.draw.rect(ctx["surface"], (255, 0, 0), (ctx["food"][0] * 10, ctx["food"][1] * 10, 10, 10))

    def on_event(ctx, ev):
        if ev.get("type") == "key" and ev.get("down"):
            k = ev.get("key")
            if k == "up" and ctx["direction"] != (0, 1):
                ctx["direction"] = (0, -1)
            elif k == "down" and ctx["direction"] != (0, -1):
                ctx["direction"] = (0, 1)
            elif k == "left" and ctx["direction"] != (1, 0):
                ctx["direction"] = (-1, 0)
            elif k == "right" and ctx["direction"] != (-1, 0):
                ctx["direction"] = (1, 0)
    """)

def life_template(mod_name: str) -> str:
    return textwrap.dedent(f"""\
    # {mod_name}.py — PXOS Game of Life
    # Hooks: setup(ctx), update(ctx, dt)

    import pygame
    import numpy as np

    def setup(ctx):
        W, H = ctx["size"]
        ctx["grid"] = np.random.choice([0, 1], size=(W // 10, H // 10), p=[0.8, 0.2])

    def update(ctx, dt):
        grid = ctx["grid"]
        new_grid = grid.copy()
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                total = int((grid[i, (j - 1) % grid.shape[1]] + grid[i, (j + 1) % grid.shape[1]] +
                             grid[(i - 1) % grid.shape[0], j] + grid[(i + 1) % grid.shape[0], j] +
                             grid[(i - 1) % grid.shape[0], (j - 1) % grid.shape[1]] + grid[(i - 1) % grid.shape[0], (j + 1) % grid.shape[1]] +
                             grid[(i + 1) % grid.shape[0], (j - 1) % grid.shape[1]] + grid[(i + 1) % grid.shape[0], (j + 1) % grid.shape[1]]))
                if grid[i, j] == 1:
                    if (total < 2) or (total > 3):
                        new_grid[i, j] = 0
                else:
                    if total == 3:
                        new_grid[i, j] = 1
        ctx["grid"] = new_grid

        ctx["surface"].fill((0, 0, 0))
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                if grid[i, j] == 1:
                    pygame.draw.rect(ctx["surface"], (255, 255, 255), (i * 10, j * 10, 10, 10))
    """)


def manifest_template(name: str, desc: str) -> str:
    ts = _dt.datetime.now().strftime("%Y-%m-%d")
    return textwrap.dedent(f"""\
    name: {name}
    version: 0.1.0
    description: {desc}
    tags: [demo, tutorial]
    created: {ts}
    perf_avg_max_ms: {DEFAULT_AVG_MS}
    perf_spike_max_ms: {DEFAULT_SPIKE_MS}
    """)

def cmd_new(args) -> int:
    target_dir = PROGRAMS if args.dir == "programs" else EXAMPLES
    base = snake(args.name)
    py_path = target_dir / f"{base}.py"
    mf_path = target_dir / f"{base}.manifest.yaml"

    if not args.force and (py_path.exists() or mf_path.exists()):
        print(f"Refusing to overwrite existing files:\n  {py_path}\n  {mf_path}\nUse --force to overwrite.", file=sys.stderr)
        return 2

    templates = {
        "default": default_template,
        "snake": snake_template,
        "life": life_template,
    }
    template_func = templates.get(args.template, default_template)
    program_content = template_func(base)

    atomic_write(py_path, program_content)
    atomic_write(mf_path, manifest_template(args.name, args.desc or f"{args.name} for PXOS"))
    print(f"Created:\n  {py_path}\n  {mf_path}")
    print(f"\nRun:\n  py screen_native_sim.py --steps 600 --program {py_path.relative_to(ROOT)}")
    return 0

def discover() -> list[pathlib.Path]:
    items: list[pathlib.Path] = []
    for d in (EXAMPLES, PROGRAMS):
        if d.exists():
            items += sorted(p for p in d.glob("*.py"))
    return items

def cmd_list(_args) -> int:
    items = discover()
    if not items:
        print("No programs found. Use: py px_cli.py new \"My Program\"")
        return 0
    for p in items:
        print(p.relative_to(ROOT))
    return 0

def run_proc(cmd: list[str]) -> int:
    print(">", " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(ROOT))
    return p.returncode

def cmd_run(args) -> int:
    prog = (ROOT / args.path).resolve() if not os.path.isabs(args.path) else pathlib.Path(args.path)
    if not prog.exists():
        print(f"Program not found: {prog}", file=sys.stderr)
        return 2
    if not SIM.exists():
        print(f"Simulator not found: {SIM}", file=sys.stderr)
        return 2
    cmd = [sys.executable, str(SIM), "--steps", str(args.steps), "--program", str(prog)]
    if args.headless:
        cmd.append("--headless")
    if args.fps:
        cmd += ["--fps", str(args.fps)]
    return run_proc(cmd)

def cmd_validate(args) -> int:
    if not VALIDATOR.exists():
        print(f"validator.py not found at {VALIDATOR} (skipping).")
        return 0
    if args.all and args.path:
        print("Choose either --all or --path, not both.", file=sys.stderr)
        return 2
    cmd = [sys.executable, str(VALIDATOR)]
    if args.all:
        cmd += ["--all", "--validation-report"]
    elif args.path:
        cmd += ["--validate-program", args.path, "--validation-report"]
    else:
        cmd += ["--all", "--validation-report"]
    return run_proc(cmd)

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="PXOS tiny CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("new", help="Create a new PXOS program + manifest")
    sp.add_argument("name", type=str, help="Human-friendly program name")
    sp.add_argument("--dir", choices=["examples", "programs"], default="examples")
    sp.add_argument("--desc", type=str, default="", help="Manifest description")
    sp.add_argument("--force", action="store_true", help="Overwrite if files exist")
    sp.add_argument("--template", choices=["default", "snake", "life"], default="default", help="Starting template for the program")
    sp.set_defaults(func=cmd_new)

    sp = sub.add_parser("list", help="List discovered programs")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("run", help="Run a program through the simulator")
    sp.add_argument("path", type=str, help="Path to program .py (relative to repo or absolute)")
    sp.add_argument("--steps", type=int, default=600)
    sp.add_argument("--fps", type=int, default=60)
    sp.add_argument("--headless", action="store_true")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("validate", help="Run static validator")
    sp.add_argument("--all", action="store_true", help="Validate all programs")
    sp.add_argument("--path", type=str, help="Validate a single program path")
    sp.set_defaults(func=cmd_validate)

    return ap

def main() -> int:
    ap = build_parser()
    args = ap.parse_args()
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
