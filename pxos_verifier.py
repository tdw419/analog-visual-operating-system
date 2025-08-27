from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Callable
from PIL import Image
import os

from pxos_device_interfaces import FrameSink, FrameSource
from py2px_runtime import Px, Op

@dataclass
class DecodedOp:
    """Result of decoding a single operation from a captured image."""
    op: Op
    status: str # 'OK', 'CORRECTED', 'BAD_ECC', 'UNREADABLE'

@dataclass
class VerificationReport:
    """Summary of a round-trip verification test."""
    passed: bool
    ok_count: int = 0
    corrected_count: int = 0
    bad_count: int = 0
    mismatches: List[Dict] = field(default_factory=list)

def decode_ops_from_image(image: Image.Image, original_ops: List[Op]) -> List[DecodedOp]:
    """
    Decodes drawing operations from a captured image.

    NOTE: This is a STUB for the digital-first phase. It cheats by looking at the
    original op log. The real implementation will perform image analysis.
    """
    decoded_ops = []
    for op in original_ops:
        # --- STUB ---
        # In a real implementation, we would:
        # 1. Find control strips/fiducials in the `image`.
        # 2. Decode the operations from the visual representation (e.g., tiles).
        # 3. Run ECC checks.

        # For now, we simulate a perfect read.
        decoded_ops.append(DecodedOp(
            op=op,
            status='OK'
        ))
    return decoded_ops

def verify_digital_program(
    program_fn: Callable[[Px], None],
    sink: FrameSink,
    source: FrameSource
) -> VerificationReport:
    """
    Runs a Python-to-pixels program and verifies its output frame-by-frame.
    This is the core of the digital-first testing strategy.
    """
    # 1. Execute the program function. The runtime will render frames and log ops.
    # We need a way to capture the output of the Px runtime.
    # Let's modify the Px class to make this easier.
    # For now, we assume the Px class saves frames and we can re-run to get logs.

    # Let's create a custom Px instance for verification
    out_dir = "verification_run"
    px = Px(out_dir=out_dir)
    program_fn(px)
    # Commit the final frame if it hasn't been already
    if px._op_log_for_frame:
        px.tick()

    report = VerificationReport(passed=True)

    # This is a simplified loop. A real one would get logs from the Px instance.
    # Let's assume we can get the logs after the run.
    # A better Px would yield (frame_path, op_log) from each tick().
    # For now, we'll re-run to get the logs (inefficient but works for a demo).

    # This part of the logic needs to be re-thought with the new runtime.
    # The verifier should drive the runtime tick by tick.
    # Let's simplify for now: we'll assume the verifier has access to the op logs.
    # This highlights the need for a tighter integration, which is a great next step.

    print("Verification stub complete. A full implementation would now loop through frames.")
    # In a real implementation, you would loop through each saved frame,
    # capture it, decode it, and compare it to the original op log for that frame.
    return report