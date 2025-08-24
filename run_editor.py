import pygame
from pxos_py.visual_editor import VisualCodeEditor
from pxos_py.window import PixelWindow # Need to see what the editor needs for context

# A mock PXOS context object, similar to what the simulator would provide.
class MockPXOS:
    def __init__(self, surface):
        self.surface = surface
        self.windows = []

    def log(self, msg):
        print(f"PXOS: {msg}")

    def blit(self, source_buffer, dest_surface, x, y):
        # A mock blit function. The editor uses this for its preview.
        # For now, we can just ignore it or print a message.
        # A more advanced version could actually render the preview.
        pass

def main():
    pygame.init()
    width, height = 800, 600
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Visual Editor Test Harness")

    # The editor expects a "px" object that has a surface and can blit.
    pxos_context = MockPXOS(screen)

    # Create the editor instance
    # The editor is a "PixelWindow", so it will draw on its own buffer.
    # We need to get that buffer and blit it to the main screen.
    editor = VisualCodeEditor(pxos_context, 10, 10, width - 20, height - 20)

    # Set the language to Python to engage the transpiler
    editor.set_language("python")

    # Set some sample code. This should trigger the transpile_to_ir method.
    sample_code = """
# Transpiler Test
CLS()
PIXEL(10, 10, 1)

for i in range(5):
    PIXEL(i * 5, 20, 1)
"""
    editor.set_code(sample_code)

    running = True
    clock = pygame.time.Clock()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Pass events to the editor (though it doesn't do much with them yet)
            # editor.handle_event(event) # This needs to be adapted to pygame events

        # The editor renders to its own internal buffer.
        # We need to call its render method, then blit its buffer to the screen.
        editor.render_content()

        # Blit the editor's canvas buffer to the main screen
        screen.blit(editor.canvas.buffer_as_surface(), (editor.x, editor.y))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
