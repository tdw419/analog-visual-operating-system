class PixelWindow:
    def __init__(self, px, x, y, width, height, title):
        self.px = px
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.title = title
        self.needs_redraw = True
