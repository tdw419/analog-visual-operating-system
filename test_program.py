"""PXOS Program: test_program
Hooks:
  - setup(ctx): One-time initialization
  - update(ctx, dt): Per-frame update
  - on_event(ctx, ev): Optional event handler
"""
def setup(ctx):
    """Initialize regions and state."""
    ctx.log("setup: hello from test_program")
    ctx.phase = 0.0

def update(ctx, dt):
    """Update parameters per frame."""
    ctx.phase = (ctx.phase + dt) % 1.0

def on_event(ctx, ev):
    """Handle click events."""
    if ev.get("type") == "click":
        ctx.log(f"[test_program] click @ ({ev['x']},{ev['y']})")
