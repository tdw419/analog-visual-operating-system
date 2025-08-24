import tkinter as tk

class TkRenderer:
    """Tkinter-based renderer for VisualPython."""
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.root = tk.Tk()
        self.root.title("VisualPython - Timeline OS")
        self.root.geometry(f"{width}x{height}")
        self.canvas = tk.Canvas(self.root, bg='#001100', width=width, height=height)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.stepper_frame = tk.Frame(self.root, bg='#222')
        self.stepper_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.step_callbacks = []

    def add_step_callback(self, back_callback, forward_callback, play_callback):
        """Add stepper control callbacks."""
        tk.Button(self.stepper_frame, text="Step Back", command=back_callback).pack(side=tk.LEFT)
        tk.Button(self.stepper_frame, text="Step Forward", command=forward_callback).pack(side=tk.LEFT)
        tk.Button(self.stepper_frame, text="Play", command=play_callback).pack(side=tk.LEFT)

    def render_bitmap_text(self, text, x, y, scale=1, color='lime'):
        """Render text using 5x7 bitmap font."""
        self.canvas.create_rectangle(x, y, x + len(text) * 6 * scale, y + 7 * scale, fill='#001100', outline='')
        current_x = x
        font5x7 = {  # Same font as in core.py, ideally shared
            'A': [0x0E, 0x11, 0x1F, 0x11, 0x11], 'B': [0x1E, 0x11, 0x1E, 0x11, 0x1E],
            'C': [0x0E, 0x11, 0x10, 0x11, 0x0E], 'D': [0x1E, 0x11, 0x11, 0x11, 0x1E],
            'E': [0x1F, 0x10, 0x1E, 0x10, 0x1F], 'F': [0x1F, 0x10, 0x1E, 0x10, 0x10],
            'G': [0x0E, 0x11, 0x13, 0x11, 0x0E], 'H': [0x11, 0x11, 0x1F, 0x11, 0x11],
            'I': [0x0E, 0x04, 0x04, 0x04, 0x0E], 'L': [0x10, 0x10, 0x10, 0x10, 0x1F],
            'M': [0x11, 0x1B, 0x15, 0x11, 0x11], 'N': [0x11, 0x19, 0x15, 0x13, 0x11],
            'O': [0x0E, 0x11, 0x11, 0x11, 0x0E], 'P': [0x1E, 0x11, 0x1E, 0x10, 0x10],
            'R': [0x1E, 0x11, 0x1E, 0x14, 0x13], 'S': [0x0F, 0x10, 0x0E, 0x01, 0x1E],
            'T': [0x1F, 0x04, 0x04, 0x04, 0x04], 'U': [0x11, 0x11, 0x11, 0x11, 0x0E],
            'V': [0x11, 0x11, 0x11, 0x0A, 0x04], 'W': [0x11, 0x11, 0x15, 0x1B, 0x11],
            'X': [0x11, 0x0A, 0x04, 0x0A, 0x11], 'Y': [0x11, 0x0A, 0x04, 0x04, 0x04],
            'Z': [0x1F, 0x02, 0x04, 0x08, 0x1F],
            '0': [0x0E, 0x11, 0x11, 0x11, 0x0E], '1': [0x04, 0x0C, 0x04, 0x04, 0x0E],
            '2': [0x0E, 0x11, 0x02, 0x08, 0x1F], '3': [0x1F, 0x02, 0x06, 0x01, 0x1E],
            '4': [0x02, 0x06, 0x0A, 0x1F, 0x02], '5': [0x1F, 0x10, 0x1E, 0x01, 0x1E],
            '6': [0x06, 0x08, 0x1E, 0x11, 0x0E], '7': [0x1F, 0x01, 0x02, 0x04, 0x08],
            '8': [0x0E, 0x11, 0x0E, 0x11, 0x0E], '9': [0x0E, 0x11, 0x0F, 0x02, 0x0C],
            ' ': [0x00, 0x00, 0x00, 0x00, 0x00], ':': [0x00, 0x04, 0x00, 0x04, 0x00],
            '(': [0x02, 0x04, 0x04, 0x04, 0x02], ')': [0x08, 0x04, 0x04, 0x04, 0x08],
            '!': [0x04, 0x04, 0x04, 0x00, 0x04], ',': [0x00, 0x00, 0x00, 0x04, 0x08],
            '.': [0x00, 0x00, 0x00, 0x00, 0x04], '_': [0x00, 0x00, 0x00, 0x00, 0x1F]
        }
        current_x = x
        for char in text.upper():
            glyph = font5x7.get(char, font5x7[' '])
            for col in range(5):
                col_bits = glyph[col]
                for row in range(7):
                    if col_bits & (1 << (6 - row)):
                        self.canvas.create_rectangle(
                            current_x + col * scale,
                            y + row * scale,
                            current_x + col * scale + scale,
                            y + row * scale + scale,
                            fill=color, outline=''
                        )
            current_x += 6 * scale

    def render_rect(self, x, y, width, height, color):
        """Render a rectangle."""
        self.canvas.create_rectangle(x, y, x + width, y + height, fill=color, outline='')

    def clear(self):
        """Clear the canvas."""
        self.canvas.delete('all')

    def update(self):
        """Update the display."""
        self.root.deiconify()
        self.root.update()

    def cleanup(self):
        """Clean up resources."""
        self.root.destroy()
