"""
Enhanced simulator with integrated kernel system and performance optimization.
"""
import argparse
import pygame
import importlib.util
import numpy as np
import psutil
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from pxos_py.surface import Surface, Bus
from pxos_py.kernels import kernel_registry, MoveKernel, ThreshKernel
from pxos_py.logutil import get_logger, log_json
from pxos_py.errors import PxosError, SimulationHaltError
from pxos_py.profiler import PerfSession

logger = get_logger()

def parse_args():
    parser = argparse.ArgumentParser(description="PXOS Pixel-Native Simulator")
    parser.add_argument("--program", type=str, required=True, help="Path to program (.py or .png)")
    parser.add_argument("--steps", type=int, default=600, help="Number of simulation steps")
    parser.add_argument("--headless", action="store_true", help="Run without display")
    parser.add_argument("--fps", type=int, default=60, help="Frames per second")
    parser.add_argument("--color-space", type=str, default="rgb", choices=["rgb", "hsl"], help="Color space for rendering")
    parser.add_argument("--profile", action="store_true", help="Enable performance profiling")
    return parser.parse_args()

def setup_simulation_context(args) -> Dict[str, Any]:
    """Initialize simulation context with kernel system."""
    pygame.init()
    W, H = 512, 512

    # Create surface
    if not args.headless:
        surface = pygame.display.set_mode((W, H))
        pygame.display.set_caption("PXOS Enhanced Simulator")
    else:
        surface = pygame.Surface((W, H))

    # Initialize context
    ctx = {
        "surface": surface,
        "steps": args.steps,
        "headless": args.headless,
        "fps": args.fps,
        "color_space": args.color_space,
        "pid": str(uuid.uuid4())[:8],
        "kernels": kernel_registry,
        "profiler": PerfSession() if args.profile else None,
        "debug": False,
        "execution_counts": np.zeros((H, W), dtype=np.int32),
        "fb_class": Surface
    }

    log_json(logger, "sim_setup",
             width=W, height=H,
             color_space=args.color_space,
             profile=args.profile)

    return ctx

def load_program(ctx: Dict[str, Any], program_path: str) -> Any:
    """Load program module or pixel grid."""
    program_path = Path(program_path)

    if not program_path.exists():
        log_json(logger, "sim_error", error=f"Program not found: {program_path}")
        raise FileNotFoundError(f"Program not found: {program_path}")

    if program_path.suffix.lower() == ".png":
        from pxos_py.px_bitpack_v1 import decode_from_png
        try:
            cartridge = decode_from_png(str(program_path))
            lang = cartridge["lang"]
            content = cartridge["content"]

            if lang.lower() in ("pixelpy", "python"):
                code = content.decode("utf-8")
                # Create a temporary file to store the decoded code
                import tempfile
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                    f.write(code)
                    temp_program_path = f.name

                # Load the temporary file as a Python module
                spec = importlib.util.spec_from_file_location("pxprog", temp_program_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Initialize program
                if hasattr(module, "setup"):
                    module.setup(ctx)

                return getattr(module, "update", None)

            elif lang.lower() == "pxasm":
                # This is where you would handle pxasm programs
                raise NotImplementedError("PXASM support is not yet implemented.")
            else:
                raise PxosError(f"Unsupported language: {lang}")

        except Exception as e:
            log_json(logger, "sim_error", error=f"Failed to load cartridge: {e}")
            raise PxosError(f"Failed to load cartridge: {e}")

    else:
        # Load Python module
        spec = importlib.util.spec_from_file_location("pxprog", program_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Initialize program
        if hasattr(module, "setup"):
            module.setup(ctx)

        return getattr(module, "update", None)

def execute_pixel_opcode(ctx: Dict[str, Any], opcode: str, x: int, y: int, p1: float, p2: float):
    """Execute a single pixel opcode."""
    try:
        fb = ctx["fb"]

        if opcode == "MOVE":
            mask = np.zeros(fb.buf.shape[:2], dtype=bool)
            mask[y, x] = True
            dir_field = np.full(fb.buf.shape[:2], int(p1 * 7), dtype=np.int32)
            ctx["fb"].buf = ctx["kernels"].get_kernel("move").apply(
                fb.buf, mask=mask, dir_field=dir_field, step=1, color_space=ctx["color_space"]
            )
        elif opcode == "DRAW":
            fb.buf[y, x] = [p1, p2, 0, 1]
        elif opcode == "COPY":
            if y > 0:
                fb.buf[y, x] = fb.buf[y-1, x]

        log_json(logger, "opcode_execute", opcode=opcode, x=x, y=y, pid=ctx["pid"])

    except Exception as e:
        log_json(logger, "opcode_error", opcode=opcode, x=x, y=y, error=str(e))
        raise PxosError(f"Failed to execute opcode {opcode}: {e}")

def render_debug_overlay(ctx: Dict[str, Any]):
    """Render debug visualization overlay."""
    surface = ctx["surface"]

    # Create heatmap overlay
    heatmap = ctx["execution_counts"].astype(np.float32)
    heatmap = (heatmap * 255 / (heatmap.max() or 1)).astype(np.uint8)

    # Create overlay surface
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 0))

    # Draw heatmap
    H, W = heatmap.shape
    heatmap_surface = pygame.surfarray.make_surface(
        (heatmap * 255).astype(np.uint8).repeat(3).reshape(H, W, 3)
    )
    heatmap_surface.set_alpha(128)
    overlay.blit(heatmap_surface, (0, 0))

    # Blit overlay
    surface.blit(overlay, (0, 0), special_flags=pygame.BLEND_ADD)

def main_loop(ctx: Dict[str, Any], update_func, args):
    """Main simulation loop with enhanced kernel integration."""
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24) if not args.headless else None

    log_json(logger, "sim_start", program=args.program, steps=args.steps)

    try:
        for frame in range(args.steps):
            ctx["ticks"] = frame

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    log_json(logger, "sim_complete", frame=frame)
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F1:
                        ctx["debug"] = not ctx["debug"]
                    elif event.key == pygame.K_F2:
                        args.profile = not args.profile

            # Update simulation
            dt_ms = clock.tick(args.fps) if not args.headless else 1000 / args.fps

            with ctx["profiler"].frame("update") if ctx["profiler"] else ctx:
                update_func(ctx, dt_ms)

            # Render debug info
            if not args.headless:
                if args.profile and ctx["profiler"]:
                    render_profiler_overlay(ctx, font)
                pygame.display.flip()

            # Log performance every 60 frames
            if frame % 60 == 0 and ctx["profiler"]:
                log_rre(ctx, args.program, frame)

    except Exception as e:
        log_json(logger, "sim_error", error=str(e), frame=frame)
        raise SimulationHaltError(f"Simulation failed at frame {frame}: {e}")

    log_json(logger, "sim_complete", frame=args.steps)

def render_profiler_overlay(ctx: Dict[str, Any], font):
    """Render performance profiler overlay."""
    summary = ctx["profiler"].to_dict()

    text_lines = [
        f"FPS: {1000/summary['avg_frame_time_ms']:.1f}",
        f"Mem: {summary['mem_peak_kb']/1024:.1f}MB",
        f"Frames: {summary['n_frames']}"
    ]

    y_offset = 10
    for line in text_lines:
        text_surface = font.render(line, True, (255, 255, 255))
        ctx["surface"].blit(text_surface, (10, y_offset))
        y_offset += 25

def log_rre(ctx: Dict[str, Any], program: str, frame: int):
    """Log Runtime Resource Estimates."""
    process = psutil.Process()
    cpu_percent = process.cpu_percent(interval=0.1)
    memory_mb = process.memory_info().rss / (1024 * 1024)

    summary = ctx["profiler"].to_dict()

    log_json(logger, "rre",
             program=program,
             frame=frame,
             pid=ctx["pid"],
             cpu_percent=cpu_percent,
             memory_mb=memory_mb,
             fps=1000/summary['avg_frame_time_ms'],
             frames=summary['n_frames'])

def main():
    args = parse_args()

    # Setup simulation context
    ctx = setup_simulation_context(args)

    # Load program
    update_func = load_program(ctx, args.program)
    if not update_func:
        log_json(logger, "sim_error", error="No update function found in program")
        return

    # Run simulation
    main_loop(ctx, update_func, args)

    # Cleanup
    pygame.quit()

    # Save profiler data
    if args.profile and ctx["profiler"]:
        ctx["profiler"].save_jsonl(Path("logs/profiler.jsonl"))

if __name__ == "__main__":
    main()
