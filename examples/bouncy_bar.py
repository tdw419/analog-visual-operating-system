# bouncy_bar.py — PXOS program scaffold
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
