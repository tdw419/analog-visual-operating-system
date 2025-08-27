import numpy as np
from typing import List, Optional
from pxos_py.bitpack_v2 import BitPackV2Codec, BitPackSpec
from pxos_py.window import PixelWindow
from pxos_py.font import PixelFont
from pxos_py.color import rgba

class CartridgeManager(PixelWindow):
    def __init__(self, px, x, y, width, height):
        super().__init__(px, x, y, width, height, "Cartridge Manager")
        self.codec = BitPackV2Codec(BitPackSpec())
        self.cartridges: List[dict] = []
        self.current_cart_index: Optional[int] = None
        self.view_mode = "grid"  # or "list"
        self.font = PixelFont()

    def load_cartridge(self, file_path: str):
        try:
            from PIL import Image
            img = Image.open(file_path).convert("RGBA")
            buffer = np.array(img, dtype=np.float32) / 255.0
            cartridge = self.codec.decode_from_buffer(buffer)
            self.cartridges.append(cartridge)
            self.needs_redraw = True
        except Exception as e:
            print(f"Error loading cartridge: {e}")

    def render_content(self):
        # Draw background
        self.px.rect(self.buffer, 0, 0, self.width, self.height, fill=rgba(0.1, 0.1, 0.15, 1))

        if self.view_mode == "grid":
            self._render_grid_view()
        else:
            self._render_list_view()

    def _render_grid_view(self):
        thumb_size = 64
        cols = self.width // (thumb_size + 10)

        for i, cart in enumerate(self.cartridges):
            col = i % cols
            row = i // cols
            x = 10 + col * (thumb_size + 10)
            y = 10 + row * (thumb_size + 10)

            # Draw thumbnail placeholder
            self.px.rect(self.buffer, x, y, thumb_size, thumb_size, fill=rgba(0.2, 0.2, 0.3, 1))

            # Draw selection highlight
            if i == self.current_cart_index:
                self.px.rect(self.buffer, x-2, y-2, thumb_size+4, thumb_size+4, fill=rgba(0, 1, 1, 0.3), width=2)

    def _render_list_view(self):
        y_offset = 10
        for i, cart in enumerate(self.cartridges):
            text = f"{i}: {cart['lang']} - {len(cart['content'])} bytes"
            color = rgba(1,1,1,1) if i == self.current_cart_index else rgba(0.8,0.8,0.8,1)
            self.font.render_string(self.buffer, 10, y_offset, text, color)
            y_offset += 10

    def handle_key(self, key: str):
        if key == "UP":
            if self.current_cart_index is not None and self.current_cart_index > 0:
                self.current_cart_index -= 1
            elif self.current_cart_index is None and self.cartridges:
                self.current_cart_index = 0
            self.needs_redraw = True
        elif key == "DOWN":
            if self.current_cart_index is not None and self.current_cart_index < len(self.cartridges) - 1:
                self.current_cart_index += 1
            elif self.current_cart_index is None and self.cartridges:
                self.current_cart_index = 0
            self.needs_redraw = True
        elif key == "ENTER":
            if self.current_cart_index is not None:
                # Run the cartridge
                pass
        elif key == "V":
            self.view_mode = "list" if self.view_mode == "grid" else "grid"
            self.needs_redraw = True
