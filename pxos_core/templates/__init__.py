import textwrap

TEMPLATES = {
    "default": {
        "description": "A minimal PXOS program with a moving rectangle.",
        "tags": ["demo", "basic"],
        "perf_budget": {"avg_ms": 1.5, "max_ms": 5.0, "mem_mb": 10.0},
        "files": {
            "main.py": textwrap.dedent(\"""
                #!/usr/bin/env python3
                \"\"\"
                PXOS Program: {{ name }}
                A minimal program that moves a rectangle across the screen.
                \"\"\"
                from pxos_core.pxlib import clear, rect, hud
                import time
                import psutil
                def setup(ctx):
                    "Initialize program state."
                    W, H = ctx["size"]
                    ctx["x"] = W // 4
                    ctx["y"] = H // 2
                    ctx["vx"] = 140
                    ctx["count"] = 0
                    ctx["debug"] = True
                    ctx["ema_ms"] = 0.0
                    ctx["last_run"] = time.ctime()
                    ctx["program_name"] = "{{ name }}"
                def update(ctx, dt):
                    "Update program logic and render."
                    t0 = time.perf_counter()
                    ctx["x"] = (ctx["x"] + ctx["vx"] * dt) % ctx["size"][0]
                    ctx["count"] += 1
                    clear(ctx, (0, 0, 0))
                    rect(ctx, int(ctx["x"]), ctx["y"], 48, 12, (80, 220, 140))
                    if ctx["debug"]:
                        upd_ms = (time.perf_counter() - t0) * 1000.0
                        ctx["ema_ms"] = 0.9 * ctx["ema_ms"] + 0.1 * upd_ms
                        mem_mb = psutil.Process().memory_info().rss / 1024 / 1024
                        hud(ctx, 8, 8, f"Program: {ctx['program_name']}\\nFrames: {ctx['count']}\\nTime: {ctx['ema_ms']:.2f}ms\\nMem: {mem_mb:.2f}MB\\nLast Run: {ctx['last_run']}")
                def on_event(ctx, ev):
                    "Handle input events."
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
            \"""),
            "manifest.yaml": textwrap.dedent(\"""
                name: {{ name }}
                version: 0.1.0
                description: A minimal program that moves a rectangle across the screen.
                tags: {{ tags | tojson }}
                created: {{ created }}
                perf_avg_max_ms: {{ perf_avg_max_ms }}
                perf_spike_max_ms: {{ perf_spike_max_ms }}
                mem_mb: {{ mem_mb }}
            \""")
        }
    },
    "snake": {
        "description": "A classic Snake game with score tracking and collision detection.",
        "tags": ["game", "input", "collision"],
        "perf_budget": {"avg_ms": 0.5, "max_ms": 2.0, "mem_mb": 15.0},
        "files": {
            "main.py": textwrap.dedent(\"""
                #!/usr/bin/env python3
                \"\"\"
                PXOS Program: {{ name }}
                A classic Snake game.
                \"\"\"
                from pxos_core.pxlib import clear, rect, hud
                import random
                def setup(ctx):
                    "Initialize game state."
                    ctx["grid_size"] = (32, 24)
                    ctx["cell_size"] = (ctx["size"][0] // ctx["grid_size"][0], ctx["size"][1] // ctx["grid_size"][1])
                    ctx["snake"] = [(10, 5), (9, 5), (8, 5)]
                    ctx["direction"] = (1, 0)
                    ctx["food"] = (15, 10)
                    ctx["score"] = 0
                    ctx["game_over"] = False
                    ctx["timer"] = 0.0
                def update(ctx, dt):
                    "Update game logic and render."
                    if ctx["game_over"]:
                        hud(ctx, ctx["size"][0] // 2 - 50, ctx["size"][1] // 2 - 10, f"Game Over! Score: {ctx['score']}")
                        return
                    ctx["timer"] += dt
                    if ctx["timer"] < 0.1:
                        return
                    ctx["timer"] = 0.0
                    head = ctx["snake"][0]
                    new_head = (head[0] + ctx["direction"][0], head[1] + ctx["direction"][1])
                    if (new_head in ctx["snake"] or
                        new_head[0] < 0 or new_head[0] >= ctx["grid_size"][0] or
                        new_head[1] < 0 or new_head[1] >= ctx["grid_size"][1]):
                        ctx["game_over"] = True
                        return
                    ctx["snake"].insert(0, new_head)
                    if new_head == ctx["food"]:
                        ctx["score"] += 1
                        while ctx["food"] in ctx["snake"]:
                            ctx["food"] = (random.randint(0, ctx["grid_size"][0] - 1), random.randint(0, ctx["grid_size"][1] - 1))
                    else:
                        ctx["snake"].pop()
                    clear(ctx, (0, 0, 0))
                    for segment in ctx["snake"]:
                        rect(ctx, segment[0] * ctx["cell_size"][0], segment[1] * ctx["cell_size"][1], ctx["cell_size"][0], ctx["cell_size"][1], (0, 255, 0))
                    rect(ctx, ctx["food"][0] * ctx["cell_size"][0], ctx["food"][1] * ctx["cell_size"][1], ctx["cell_size"][0], ctx["cell_size"][1], (255, 0, 0))
                    hud(ctx, 10, 10, f"Score: {ctx['score']}")
                def on_event(ctx, ev):
                    "Handle input events."
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
            \"""),
            "manifest.yaml": textwrap.dedent(\"""
                name: {{ name }}
                version: 1.0.0
                description: A classic Snake game with score tracking and collision detection.
                tags: {{ tags | tojson }}
                created: {{ created }}
                perf_avg_max_ms: {{ perf_avg_max_ms }}
                perf_spike_max_ms: {{ perf_spike_max_ms }}
                mem_mb: {{ mem_mb }}
            \""")
        }
    },
    "conway": {
        "description": "Conway's Game of Life, a zero-player cellular automaton.",
        "tags": ["simulation", "automaton"],
        "perf_budget": {"avg_ms": 2.0, "max_ms": 10.0, "mem_mb": 20.0},
        "files": {
            "main.py": textwrap.dedent(\"""
                #!/usr/bin/env python3
                \"\"\"
                PXOS Program: {{ name }}
                Conway's Game of Life.
                \"\"\"
                from pxos_core.pxlib import clear, rect
                import random
                def setup(ctx):
                    "Initialize game state."
                    ctx["grid_size"] = (64, 48)
                    ctx["cell_size"] = (ctx["size"][0] // ctx["grid_size"][0], ctx["size"][1] // ctx["grid_size"][1])
                    ctx["grid"] = [[random.choice([0, 1]) for _ in range(ctx["grid_size"][0])] for _ in range(ctx["grid_size"][1])]
                    ctx["timer"] = 0.0
                def update(ctx, dt):
                    "Update game logic and render."
                    ctx["timer"] += dt
                    if ctx["timer"] < 0.1:
                        return
                    ctx["timer"] = 0.0
                    new_grid = [[0 for _ in range(ctx["grid_size"][0])] for _ in range(ctx["grid_size"][1])]
                    for y in range(ctx["grid_size"][1]):
                        for x in range(ctx["grid_size"][0]):
                            neighbors = 0
                            for i in range(-1, 2):
                                for j in range(-1, 2):
                                    if i == 0 and j == 0:
                                        continue
                                    nx, ny = x + j, y + i
                                    if 0 <= nx < ctx["grid_size"][0] and 0 <= ny < ctx["grid_size"][1]:
                                        neighbors += ctx["grid"][ny][nx]
                            if ctx["grid"][y][x] == 1 and (neighbors < 2 or neighbors > 3):
                                new_grid[y][x] = 0
                            elif ctx["grid"][y][x] == 0 and neighbors == 3:
                                new_grid[y][x] = 1
                            else:
                                new_grid[y][x] = ctx["grid"][y][x]
                    ctx["grid"] = new_grid
                    clear(ctx, (0, 0, 0))
                    for y in range(ctx["grid_size"][1]):
                        for x in range(ctx["grid_size"][0]):
                            if ctx["grid"][y][x] == 1:
                                rect(ctx, x * ctx["cell_size"][0], y * ctx["cell_size"][1], ctx["cell_size"][0], ctx["cell_size"][1], (255, 255, 255))
                def on_event(ctx, ev):
                    "Handle input events."
                    if ev.get("type") == "click":
                        x, y = ev["x"] // ctx["cell_size"][0], ev["y"] // ctx["cell_size"][1]
                        if 0 <= x < ctx["grid_size"][0] and 0 <= y < ctx["grid_size"][1]:
                            ctx["grid"][y][x] = 1 - ctx["grid"][y][x]
            \"""),
            "manifest.yaml": textwrap.dedent(\"""
                name: {{ name }}
                version: 1.0.0
                description: Conway's Game of Life, a zero-player cellular automaton.
                tags: {{ tags | tojson }}
                created: {{ created }}
                perf_avg_max_ms: {{ perf_avg_max_ms }}
                perf_spike_max_ms: {{ perf_spike_max_ms }}
                mem_mb: {{ mem_mb }}
            \""")
        }
    }
}
