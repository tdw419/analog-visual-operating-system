import numpy as np
from pxos_py.bitpack_v2 import BitPackV2Codec, BitPackSpec

codec = BitPackV2Codec(BitPackSpec())

sample_code = """
# Sample PixelOS Program
import numpy as np

# Create a colorful pattern
def update(buffer):
    for y in range(buffer.height):
        for x in range(buffer.width):
            r = x / buffer.width
            g = y / buffer.height
            b = (x + y) / (buffer.width + buffer.height)
            buffer.set_pixel(x, y, (r, g, b, 1.0))

print("Sample pattern created!")
"""

cartridge_buffer = codec.encode_to_buffer(sample_code, "pixelpy")

from PIL import Image
img_data = (cartridge_buffer * 255).astype(np.uint8)
Image.fromarray(img_data, mode="RGBA").save("examples/demo_cartridge.png")
