import numpy as np

class Surface:
    def __init__(self, buf):
        self.buf = buf

    @classmethod
    def empty(cls, H, W, color_space="rgb"):
        buf = np.zeros((H, W, 4), dtype=np.float32)
        return cls(buf)

    def blit_to(self, surface):
        pass

class Bus:
    pass
