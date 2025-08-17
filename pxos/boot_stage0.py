from .boot_stage1 import main as boot1

def main(host):
    """
    PXOS Boot Stage 0:
    - Allocates the primary framebuffer.
    - Passes control to Stage 1.
    """
    host.log("🚀 PXOS Stage 0: Allocating framebuffer...")
    buf = host.alloc_buffer(640, 480)
    host.log("✅ PXOS Stage 0: Framebuffer ready. Handing off to Stage 1.")
    boot1(host, buf)
