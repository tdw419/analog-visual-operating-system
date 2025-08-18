import pygame
import sys
import logging
from typing import Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("pxweb_host.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# These imports assume the files are in the same root directory
try:
    from strict_runner import StrictRunner, VMConfig, MEM, CMD_KEY
    from pxweb_cart import build_pxweb_cart
    from pxos_input_driver import PXOSInputEngine, pygame_key_to_vk
except ImportError as e:
    logging.error(f"Failed to import required modules: {e}")
    logging.error("Please ensure strict_runner.py, pxweb_cart.py, and pxos_input_driver.py are in the same directory.")
    sys.exit(1)


def frame_rgba_bytes(vm: StrictRunner) -> bytes:
    """Extracts the framebuffer from the VM as raw RGBA bytes."""
    out = bytearray()
    for row in vm.fb:
        for r, g, b, a in row:
            out += bytes((r, g, b, a))
    return bytes(out)

def run_pxweb(vm: StrictRunner, cart_bytes: bytes, input_driver: PXOSInputEngine, step_per_frame: int = 2000, scale: int = 1):
    """Main interactive loop for the pxweb host."""
    vm.load_cart_bytes(cart_bytes)
    pygame.init()
    w, h = vm.cfg.width, vm.cfg.height
    window = pygame.display.set_mode((w * scale, h * scale))
    pygame.display.set_caption("pxweb")
    clock = pygame.time.Clock()

    running = True
    logging.info("Starting pxweb host...")

    while running:
        # --- Input Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.KEYDOWN:
                # Convert pygame key to a virtual keycode string
                vk_string = pygame_key_to_vk(event)
                if vk_string:
                    # The input driver handles writing to the mailbox
                    input_driver.send_key(vk_string)

        if not running:
            break

        # --- VM Execution ---
        vm.run(step_per_frame)

        # --- Rendering ---
        buf = frame_rgba_bytes(vm)
        surf = pygame.image.frombuffer(buf, (w, h), "RGBA")
        if scale != 1:
            surf = pygame.transform.scale(surf, (w * scale, h * scale))
        window.blit(surf, (0, 0))
        pygame.display.flip()

        clock.tick(60)

    logging.info("Shutting down pxweb host.")
    pygame.quit()


if __name__ == "__main__":
    try:
        vm = StrictRunner(VMConfig(width=640, height=480))
        cart = build_pxweb_cart()

        # The input driver needs a reference to the VM's memory to write to the mailbox
        input_driver = PXOSInputEngine(vm.mem)

        run_pxweb(vm, cart, input_driver, step_per_frame=5000)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)
