"""
PXOS LLM Visualization: Neural oscilloscope for AI operations
"""
import numpy as np
import json
from typing import List, Dict, Any
from datetime import datetime
from .pixel_buffer import PixelBuffer
from .trust.anchor import TrustAnchor
from .build.sbom import SBOMGenerator
from .compliance.dashboard import ComplianceDashboard

class LLMVisualizer:
    """Visualizes LLM operations as pixel patterns"""

    def __init__(self, pixel_buffer: PixelBuffer):
        self.buffer = pixel_buffer
        self.trust_anchor = TrustAnchor()
        self.sbom_generator = SBOMGenerator(self.trust_anchor, ComplianceDashboard())
        self.frames = []

        # Layout for visualization
        self.layout = {
            "tokens": {"y": 0, "height": 80},
            "logits": {"y": 100, "height": 400},
            "attention": {"y": 520, "height": 200}
        }
        print("[LLM-VIZ] Initialized LLM Visualizer.")

    def visualize_token_stripes(self, tokens: List[str], width: int = 800) -> np.ndarray:
        """Render tokens as colored vertical stripes"""
        if not tokens:
            return np.zeros((self.layout["tokens"]["height"], width, 4), dtype=np.uint8)

        stripe_width = max(1, (width - 20) // len(tokens))
        frame = np.zeros((self.layout["tokens"]["height"], width, 4), dtype=np.uint8)

        x_pos = 10
        for token in tokens:
            # Generate color based on token hash
            color = self._token_to_color(token)

            # Draw stripe
            x_end = min(x_pos + stripe_width, width - 10)
            frame[:, x_pos:x_end] = color

            x_pos = x_end + 2

        return frame

    def visualize_logits_spectrogram(self, logits: List[List[float]], width: int = 800) -> np.ndarray:
        """Render logits as a spectrogram"""
        if not logits:
            return np.zeros((self.layout["logits"]["height"], width, 4), dtype=np.uint8)

        frame = np.zeros((self.layout["logits"]["height"], width, 4), dtype=np.uint8)

        for step_idx, step_logits in enumerate(logits[:self.layout["logits"]["height"]//4]):
            # Normalize logits
            step_logits = np.array(step_logits)
            if step_logits.max() > step_logits.min():
                normalized = (step_logits - step_logits.min()) / (step_logits.max() - step_logits.min())
            else:
                normalized = np.full_like(step_logits, 0.5)

            # Draw as horizontal bars
            y_start = step_idx * 4
            y_end = y_start + 3

            for i, value in enumerate(normalized[:width//4]):
                brightness = int(value * 255)
                frame[y_start:y_end, i*4:(i+1)*4] = [brightness, brightness, brightness, 255]

        return frame

    def record_frame(self, frame: np.ndarray, frame_type: str):
        """Record a frame for later playback"""
        self.frames.append({
            "type": frame_type,
            "data": frame.tobytes().hex(),
            "shape": list(frame.shape),
            "timestamp": datetime.utcnow().isoformat()
        })

    def save_recording(self, output_path: str):
        """Save recorded frames as BitPack"""
        cartridge = {
            "format": "pxos-llm-recording-v1",
            "metadata": {
                "frame_count": len(self.frames),
                "timestamp": datetime.utcnow().isoformat()
            },
            "frames": self.frames
        }

        cartridge_bytes = json.dumps(cartridge).encode('utf-8')
        signature = self.trust_anchor.sign(cartridge_bytes)

        # Generate SBOM
        self.sbom_generator.generate(
            [{"name": "llm_recording", "data": cartridge_bytes.decode('utf-8'), "version": "1.0.0"}],
            f"{output_path}.sbom.json",
            ["llm_visualization"]
        )

        # Save files
        with open(output_path, "wb") as f:
            f.write(cartridge_bytes)
        with open(f"{output_path}.sig", "w") as f:
            json.dump({"signature": signature.hex()}, f)

        print(f"[LLM-VIZ] Saved recording to '{output_path}'")
        return output_path

    def _token_to_color(self, token: str) -> np.ndarray:
        """Generate consistent color for token"""
        # Simple hash-based color generation
        hash_val = hash(token)
        return np.array([
            (hash_val & 0xFF0000) >> 16,
            (hash_val & 0x00FF00) >> 8,
            (hash_val & 0x0000FF),
            255
        ], dtype=np.uint8)
