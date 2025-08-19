"""
A simple, hardcoded 5x7 pixel font renderer.
This is a basic implementation for demonstrating the concept of
mathematical/procedural rendering in the PXOS ecosystem.
"""
import numpy as np

# A simple 5x7 pixel font. 1 represents a lit pixel.
# The data is stored as a dictionary mapping characters to a list of 7 integers,
# where each integer represents a row of 5 pixels.
FONT_DATA = {
    'A': [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    'B': [0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110],
    'C': [0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110],
    'D': [0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110],
    'E': [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111],
    'F': [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000],
    'G': [0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01110],
    'H': [0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    'I': [0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    'J': [0b00011, 0b00001, 0b00001, 0b00001, 0b00001, 0b10001, 0b01110],
    'K': [0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001],
    'L': [0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
    'M': [0b10001, 0b11011, 0b10101, 0b10001, 0b10001, 0b10001, 0b10001],
    'N': [0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001],
    'O': [0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    'P': [0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
    'Q': [0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01111],
    'R': [0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001],
    'S': [0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110],
    'T': [0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
    'U': [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    'V': [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
    'W': [0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001],
    'X': [0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001],
    'Y': [0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100],
    'Z': [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111],
    ' ': [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
    '0': [0b01110, 0b10011, 0b10101, 0b10101, 0b10101, 0b11001, 0b01110],
    '1': [0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    '2': [0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111],
    '3': [0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110],
    '4': [0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010],
    '5': [0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110],
    '6': [0b01110, 0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110],
    '7': [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000],
    '8': [0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110],
    '9': [0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00001, 0b01110],
    '.': [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b01100, 0b01100],
    ',': [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b01100, 0b00100],
    ':': [0b00000, 0b00000, 0b01100, 0b00000, 0b01100, 0b00000, 0b00000],
    '\'': [0b00100, 0b00100, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
    '"': [0b01010, 0b01010, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
    '!': [0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100],
    '?': [0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b00000, 0b00100],
    '(': [0b00100, 0b01000, 0b01000, 0b01000, 0b01000, 0b01000, 0b00100],
    ')': [0b01000, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01000],
    '[': [0b01110, 0b01000, 0b01000, 0b01000, 0b01000, 0b01000, 0b01110],
    ']': [0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    '{': [0b00110, 0b01000, 0b01000, 0b11100, 0b01000, 0b01000, 0b00110],
    '}': [0b01100, 0b00010, 0b00010, 0b00111, 0b00010, 0b00010, 0b01100],
    '-': [0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000],
}

FONT_WIDTH = 5
FONT_HEIGHT = 7
CHAR_SPACING = 1 # Pixels between characters

class PixelFont:
    """
    A simple bitmap font renderer.
    """
    def render_string(self, buffer, x, y, text, color):
        """
        Renders a string onto the given buffer.

        Args:
            buffer (np.ndarray): The target buffer (H, W, 4) to draw on.
            x (int): The starting X coordinate.
            y (int): The starting Y coordinate.
            text (str): The string to render.
            color (list or tuple): The [R, G, B, A] color to use for the text.
        """
        cursor_x = x
        buffer_height, buffer_width, _ = buffer.shape

        for char in text.upper(): # Our font only has uppercase letters
            glyph = FONT_DATA.get(char)
            if not glyph:
                glyph = FONT_DATA.get('?') # Fallback for unknown characters

            for row_idx, row_data in enumerate(glyph):
                for col_idx in range(FONT_WIDTH):
                    # Check if the pixel in the glyph is set
                    if (row_data >> (FONT_WIDTH - 1 - col_idx)) & 1:
                        # Calculate the pixel's position on the buffer
                        px = cursor_x + col_idx
                        py = y + row_idx

                        # Check bounds to avoid drawing outside the buffer
                        if 0 <= px < buffer_width and 0 <= py < buffer_height:
                            buffer[py, px] = color

            # Move cursor for the next character
            cursor_x += FONT_WIDTH + CHAR_SPACING
