"""
PXOS PIXEL Integration: Text-to-pixel encoding using ViT
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import json
from datetime import datetime
from typing import Optional
from ..pixel_buffer import PixelBuffer
from ..trust.anchor import TrustAnchor
from ..build.sbom import SBOMGenerator
from ..compliance.dashboard import ComplianceDashboard

class PixelEncoder:
    """Encodes text as pixels using ViT-based approach"""

    def __init__(self, font_path: Optional[str] = None):
        self.font_path = font_path or "pxos/fonts/GoNotoCurrent.ttf"
        try:
            self.font = ImageFont.truetype(self.font_path, size=24)
        except IOError:
            print(f"Warning: Font '{self.font_path}' not found. Using default font.")
            # Fallback to default font
            self.font = ImageFont.load_default()

        self.trust_anchor = TrustAnchor()
        self.sbom_generator = SBOMGenerator(self.trust_anchor, ComplianceDashboard())

    def text_to_pixels(self, text: str, width: int = 512, height: int = 128) -> np.ndarray:
        """Convert text to pixel array"""
        # Create image
        img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        # Calculate text position (centered)
        try:
            bbox = draw.textbbox((0, 0), text, font=self.font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except AttributeError: # Fallback for older Pillow versions
            text_width, text_height = draw.textsize(text, font=self.font)

        x = (width - text_width) // 2
        y = (height - text_height) // 2

        # Draw text
        draw.text((x, y), text, font=self.font, fill=(0, 0, 0, 255))

        return np.array(img)

    def pixels_to_text(self, pixel_array: np.ndarray) -> str:
        """Convert pixels back to text (placeholder)"""
        # In a real implementation, this would use OCR or the PIXEL decoder
        # For now, we return a placeholder string.
        print("[PIXEL] Decoding pixels to text (simulation)...")
        if np.sum(pixel_array) > 0:
            return "[Decoded text from pixels]"
        else:
            return ""

    def create_bitpack(self, text: str, output_path: str):
        """Create a BitPack from text"""
        print(f"[PIXEL] Creating BitPack for text: '{text}' at '{output_path}'")
        # Convert to pixels
        pixels = self.text_to_pixels(text)

        # Create cartridge
        cartridge = {
            "format": "pxos-pixel-text-v1",
            "metadata": {
                "text": text,
                "timestamp": datetime.utcnow().isoformat(),
                "font": self.font_path,
                "dimensions": pixels.shape[:2]
            },
            "pixel_data": pixels.tobytes().hex()
        }

        # Save as BitPack
        cartridge_bytes = json.dumps(cartridge).encode('utf-8')
        signature = self.trust_anchor.sign(cartridge_bytes)

        # Generate SBOM
        self.sbom_generator.generate(
            [{"name": "pixel_text", "data": cartridge_bytes.decode('utf-8'), "version": "1.0.0"}],
            f"{output_path}.sbom.json",
            [text]
        )

        # Save files
        with open(output_path, "wb") as f:
            f.write(cartridge_bytes)
        with open(f"{output_path}.sig", "w") as f:
            json.dump({"signature": signature.hex()}, f)

        print(f"[PIXEL] BitPack '{output_path}' created successfully.")
        return output_path
