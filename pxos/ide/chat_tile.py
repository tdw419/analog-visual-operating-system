"""
PXOS Chat Tile: AI-driven interaction interface
"""
import numpy as np
import json
from typing import Dict, Any
from ..pixel_buffer import PixelBuffer, Region
from ..ai_bridge import AIBridge
from ..kernel_plan import sys_plan_apply

class ChatTile:
    """Interactive chat tile for AI-driven PXOS operations"""

    def __init__(self, pixel_buffer: PixelBuffer, context: Dict[str, Any]):
        self.buffer = pixel_buffer
        self.context = context
        self.ai_bridge = AIBridge(backend="mock")
        self.input_text = ""
        self.output_plan = None
        self.width = 400
        self.height = 300
        self.x = 10
        self.y = 10

        # Register region in pixel buffer
        self.buffer.register_region("chat_tile",
                                   Region(self.x, self.y, self.width, self.height))

    def render(self):
        """Render the chat tile"""
        # Create chat tile background
        tile_data = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        tile_data[:] = [40, 40, 60, 255]  # Dark blue background

        # Render input text
        self._render_text(tile_data, self.input_text, 10, 10, (255, 255, 255, 255))

        # Render output plan if exists
        if self.output_plan:
            plan_text = json.dumps(self.output_plan, indent=2)
            self._render_text(tile_data, plan_text, 10, 50, (200, 255, 200, 255))

        # Update pixel buffer
        self.buffer.update_region(tile_data, self.x, self.y)

    def _render_text(self, tile_data: np.ndarray, text: str, x: int, y: int, color):
        """Simple text rendering (placeholder for proper font rendering)"""
        for i, char in enumerate(text[:50]):  # Limit characters
            if x + i * 8 < tile_data.shape[1] and y < tile_data.shape[0]:
                # Simple 8x8 character representation
                tile_data[y:y+8, x+i*8:x+i*8+8] = color

    def handle_input(self, text: str):
        """Handle text input and generate AI plan"""
        if text == "\n":  # Enter key
            # Generate plan from AI
            self.output_plan = self.ai_bridge.generate_plan(
                self.input_text,
                {"screen": {"w": self.buffer.width, "h": self.buffer.height}}
            )

            # Execute plan
            if self.output_plan:
                result = sys_plan_apply(self.context, self.output_plan, dry_run=False)
                print(f"[CHAT] Plan executed: {result}")

            # Clear input
            self.input_text = ""
        elif text == "\b":  # Backspace
            self.input_text = self.input_text[:-1]
        else:  # Regular character
            self.input_text += text

        # Re-render
        self.render()
