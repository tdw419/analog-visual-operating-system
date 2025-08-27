from abc import ABC, abstractmethod
from PIL import Image

class FrameSink(ABC):
    """Abstract interface for a device that can display a frame (an image)."""

    @abstractmethod
    def present(self, image: Image.Image) -> None:
        """Presents a single image frame to the output device."""
        pass

class FrameSource(ABC):
    """Abstract interface for a device that can capture a frame (an image)."""

    @abstractmethod
    def capture(self) -> Image.Image:
        """Captures a single image frame from the input device."""
        pass