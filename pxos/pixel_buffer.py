"""
PXOS PixelBuffer: The universal substrate for all computation
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class Region:
    """Rectangular region in pixel space"""
    x: int
    y: int
    width: int
    height: int

    def contains(self, x: int, y: int) -> bool:
        return (self.x <= x < self.x + self.width and
                self.y <= y < self.y + self.height)

class PixelBuffer:
    """Universal pixel buffer for all PXOS operations"""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.data = np.zeros((height, width, 4), dtype=np.uint8)
        self.regions: Dict[str, Region] = {}
        self.dirty_regions: List[Region] = []

    def clear(self, color=(0, 0, 0, 255)):
        """Clear entire buffer"""
        self.data[:] = color
        self.dirty_regions.append(Region(0, 0, self.width, self.height))

    def update_region(self, pixels: np.ndarray, x: int, y: int):
        """Update a rectangular region"""
        h, w = pixels.shape[:2]
        if x + w > self.width or y + h > self.height:
            raise ValueError("Region out of bounds")

        self.data[y:y+h, x:x+w] = pixels
        self.dirty_regions.append(Region(x, y, w, h))

    def get_region(self, x: int, y: int, width: int, height: int) -> np.ndarray:
        """Get a rectangular region"""
        return self.data[y:y+height, x:x+width].copy()

    def register_region(self, name: str, region: Region):
        """Register a named region"""
        self.regions[name] = region

    def get_dirty_regions(self) -> List[Region]:
        """Get all dirty regions and clear the list"""
        dirty = self.dirty_regions.copy()
        self.dirty_regions.clear()
        return dirty

    def save(self, path: str):
        """Save buffer to file"""
        from PIL import Image
        img = Image.fromarray(self.data)
        img.save(path)

    def load(self, path: str):
        """Load buffer from file"""
        from PIL import Image
        img = Image.open(path)
        self.data = np.array(img.convert('RGBA'))
        self.height, self.width = self.data.shape[:2]
