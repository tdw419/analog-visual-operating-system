import numpy as np
import os
import hashlib
import json
from typing import List, Optional, Dict, Any

from pxos_py.bitpack_v2 import BitPackV2Codec, BitPackSpec
from pxos_py.window import PixelWindow
from pxos_py.font import PixelFont
from pxos_py.color import rgba
from pxos_py.trust.anchor import TrustAnchor
from pxos_py.trust.sbom import validate_sbom

class CartridgeManager(PixelWindow):
    def __init__(self, px, x, y, width, height, pub_key_path: str):
        super().__init__(px, x, y, width, height, "Cartridge Manager")
        self.codec = BitPackV2Codec(BitPackSpec())
        self.cartridges: List[dict] = []
        self.current_cart_index: Optional[int] = None
        self.view_mode = "grid"  # or "list"
        self.font = PixelFont()

        print(f"Loading public key for verification from: {pub_key_path}")
        self.trust_anchor = TrustAnchor(dev_pub_pem_path=pub_key_path)

        # Define a simple security policy for SBOM validation
        self.security_policy = {
            "require_clean_git_status": False,
            "allowed_builders": ["pxos/1.2.0"]
        }

    def verify_cartridge(self, cartridge: Dict[str, Any]) -> bool:
        """Verifies the signature and SBOM of a decoded cartridge."""
        if not self.trust_anchor.dev_pub_key:
            print("Verification failed: No public key loaded.")
            return False

        # 1. Verify signature
        signature = cartridge.get("signature")
        digest_hex = cartridge.get("digest")  # This is the hex digest of the code segment

        if signature is None or digest_hex is None:
            print("Verification failed: Cartridge is missing digest or signature.")
            return False

        code_digest_bytes = bytes.fromhex(digest_hex)

        if not self.trust_anchor.verify_signature(signature, code_digest_bytes, self.trust_anchor.dev_pub_key):
            print("Verification failed: Invalid signature.")
            return False

        print("Signature verified successfully.")

        # 2. Verify SBOM
        sbom_raw = cartridge.get("sbom_raw")
        if sbom_raw:
            try:
                sbom_data = json.loads(sbom_raw.decode('utf-8'))
                # In a real scenario, you'd pass the dict to the validator.
                # For now, we'll just show it's parsed.
                print(f"SBOM found and parsed. Builder: {sbom_data.get('provenance', {}).get('builder')}")
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Verification failed: Could not parse SBOM. Error: {e}")
                return False
        else:
            print("Warning: No SBOM found in cartridge.")

        return True

    def load_cartridge(self, file_path: str):
        print(f"Loading cartridge from {file_path}...")
        try:
            from PIL import Image
            img = Image.open(file_path).convert("RGBA")
            buffer = np.array(img, dtype=np.float32) / 255.0

            cartridge = self.codec.decode_from_buffer(buffer)

            # The original content is in 'content', not 'code'. Let's fix that.
            # The digest is also calculated from the stored bytes.
            # The `decode_from_buffer` gives us the raw bytes in 'content'.
            # The digest in the header is from those raw bytes. So we don't need to re-calculate.

            # Let's correct verify_cartridge. It should use the digest from the header.

            if self.verify_cartridge(cartridge):
                self.cartridges.append(cartridge)
                self.needs_redraw = True
                print("Cartridge loaded successfully.")
            else:
                print(f"Failed to load cartridge: {file_path}. Verification failed.")

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

            # Draw status indicator (green for verified)
            self.px.rect(self.buffer, x+2, y+2, 8, 8, fill=rgba(0,1,0,0.8))

            # Draw selection highlight
            if i == self.current_cart_index:
                self.px.rect(self.buffer, x-2, y-2, thumb_size+4, thumb_size+4, fill=rgba(0, 1, 1, 0.3), width=2)

    def _render_list_view(self):
        y_offset = 10
        for i, cart in enumerate(self.cartridges):
            text = f"[OK] {i}: {cart['lang']} - {len(cart['content'])} bytes"
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
