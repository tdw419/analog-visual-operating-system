from PIL import Image
from pxos_device_interfaces import FrameSink, FrameSource
from typing import Optional

class FrameSinkDigital(FrameSink):
    """A digital FrameSink that holds the 'rendered' image in memory."""
    def __init__(self):
        self.framebuffer: Optional[Image.Image] = None

    def present(self, image: Image.Image) -> None:
        """Stores the image in the in-memory framebuffer."""
        self.framebuffer = image.copy()

class FrameSourceDigital(FrameSource):
    """A digital FrameSource that 'captures' from an in-memory FrameSink."""
    def __init__(self, sink: FrameSinkDigital):
        self._sink = sink

    def capture(self) -> Image.Image:
        """Returns a copy of the image from the sink's framebuffer."""
        if self._sink.framebuffer is None:
            raise ConnectionError("Cannot capture frame: FrameSink has nothing to present.")
        return self._sink.framebuffer.copy()