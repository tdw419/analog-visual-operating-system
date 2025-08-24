import numpy as np
from pxos_py.window import PixelWindow
from pxos_py.font import PixelFont
from pxos_py.color import rgba
from transpiler import PythonToCsvTranspiler
import io
import csv

class VisualToolbox:
    def __init__(self):
        self.tools = ["code", "block"]
        self.selected_tool = "code"

    def render(self, buffer):
        # Render the toolbox UI
        pass

    def contains(self, x, y):
        # Check if a point is within the toolbox
        return False

    def get_tool_at(self, pos):
        # Get the tool at a given position
        return "code"

class CodeCanvas:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.buffer = np.zeros((height, width, 4), dtype=np.float32)
        self.font = PixelFont()

    def render(self, buffer, code, language):
        if language == "pxasm":
            self.highlight_pxasm(buffer, code)
        else:
            # Default text rendering
            self.font.render_string(buffer, 10, 10, code, rgba(1,1,1,1))

    def highlight_pxasm(self, buffer, code):
        lines = code.split('\n')
        y_offset = 10
        for line in lines:
            parts = line.split()
            if not parts:
                continue

            x_offset = 10
            for part in parts:
                color = self.get_pxasm_color(part)
                self.font.render_string(buffer, x_offset, y_offset, part, color)
                x_offset += len(part) * 6 + 6 # 6 is font width

            y_offset += 10

    def get_pxasm_color(self, part):
        if part.upper() in ["MOVE", "COPY", "CLEAR", "BLEND", "ADD", "SUB", "MUL", "DIV", "BLUR", "EDGE", "CONVOL", "CREATE_FIELD", "APPLY_FIELD", "MOVE_MASK", "JMP", "JZ", "JNZ", "CALL", "RET", "SYNC", "HALT", "DEBUG", "LOAD", "STORE", "PEEK", "POKE"]:
            return rgba(1, 0.5, 0.5, 1) # Keywords
        elif part.endswith(':'):
            return rgba(0.5, 1, 0.5, 1) # Labels
        elif part.startswith('#'):
            return rgba(0.5, 0.5, 1, 1) # Comments
        else:
            return rgba(1, 1, 1, 1) # Default

    def handle_click(self, event):
        # Handle clicks on the code canvas
        pass

    def buffer_as_surface(self):
        """Converts the internal numpy buffer to a pygame Surface."""
        import pygame
        # Convert float (0-1) to uint8 (0-255)
        # We need to clip to handle potential floating point inaccuracies
        int_buffer = np.clip(self.buffer * 255, 0, 255).astype(np.uint8)

        # The buffer is (height, width, channels), but make_surface expects (width, height, channels)
        # So we need to transpose the first two axes.
        # We only need the RGB channels for make_surface.
        rgb_buffer = int_buffer[:, :, :3]

        # Pygame's surfarray has dimensions swapped (width, height) vs numpy (height, width)
        return pygame.surfarray.make_surface(rgb_buffer.transpose(1, 0, 2))

class VisualCodeEditor(PixelWindow):
    def __init__(self, px, x, y, width, height):
        super().__init__(px, x, y, width, height, "Visual Editor")
        self.canvas = CodeCanvas(width-20, height-40)
        self.toolbox = VisualToolbox()
        self.mode = "code"  # or "visual"
        self.language = "python"
        self.code = ""

    def handle_event(self, event):
        if event.type == "MOUSE_CLICK":
            if self.toolbox.contains(event.pos):
                tool = self.toolbox.get_tool_at(event.pos)
                self.select_tool(tool)
            else:
                self.canvas.handle_click(event)

    def select_tool(self, tool):
        if tool == "code":
            self.mode = "code"
        elif tool == "block":
            self.mode = "visual"

    def set_language(self, language):
        self.language = language
        self.needs_redraw = True

    def set_code(self, code):
        self.code = code
        self.needs_redraw = True
        self.transpile_to_ir()

    def transpile_to_ir(self):
        if self.language == "python":
            transpiler = PythonToCsvTranspiler()
            try:
                csv_ops = transpiler.transpile(self.code)

                # Format to CSV string for display/logging
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(['frame', 'op', 'param1', 'param2', 'param3'])
                writer.writerows(csv_ops)
                csv_string = output.getvalue()

                # For now, just print it for verification
                print("--- Transpiled IR (CSV) ---")
                print(csv_string)
                print("---------------------------")
                return csv_ops
            except Exception as e:
                print(f"Error during transpilation: {e}")
                return None
        return None

    def render_content(self):
        # The buffer to draw on belongs to the canvas.
        self.canvas.render(self.canvas.buffer, self.code, self.language)
        self.toolbox.render(self.canvas.buffer)
        # The preview logic seems buggy and incomplete, disabling for now.
        # preview = self.get_pixel_preview()
        # if preview:
        #     self.px.blit(preview, self.canvas.buffer, self.width - 220, 20)

    def get_pixel_preview(self):
        if self.language == "pxasm":
            from pxos_py.pxasm_compiler import pxasm_to_pixelbuffer
            return pxasm_to_pixelbuffer(self.code)
        else:
            # For other languages, we can't generate a preview
            return None

    def update_preview(self):
        self.preview_buffer = self.get_pixel_preview()
        self.needs_redraw = True
