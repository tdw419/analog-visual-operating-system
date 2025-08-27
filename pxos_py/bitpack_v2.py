import numpy as np
from hashlib import sha256
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List
import json
import zstd

MAGIC = b"PXCODE2\0"

@dataclass
class BitPackHeaderV2:
    magic: bytes = MAGIC
    version: int = 2
    flags: int = 0  # Compression, thumbnail, etc
    lang_id: str = "pixelpy"
    content_length: int = 0
    thumbnail_offset: int = 0
    segment_count: int = 1
    checksum: bytes = b"\0"*32

    def serialize(self) -> bytes:
        lang = self.lang_id.encode('ascii')[:8].ljust(8, b'\0')
        return (self.magic +
                self.version.to_bytes(2, 'little') +
                self.flags.to_bytes(2, 'little') +
                lang +
                self.content_length.to_bytes(8, 'little') +
                self.thumbnail_offset.to_bytes(8, 'little') +
                self.segment_count.to_bytes(4, 'little') +
                self.checksum)

    @classmethod
    def deserialize(cls, data: bytes) -> "BitPackHeaderV2":
        magic = data[:8]
        if magic != MAGIC:
            raise ValueError("Invalid magic number")
        version = int.from_bytes(data[8:10], 'little')
        flags = int.from_bytes(data[10:12], 'little')
        lang_id = data[12:20].rstrip(b'\0').decode('ascii')
        content_length = int.from_bytes(data[20:28], 'little')
        thumbnail_offset = int.from_bytes(data[28:36], 'little')
        segment_count = int.from_bytes(data[36:40], 'little')
        checksum = data[40:72]
        return cls(magic, version, flags, lang_id, content_length, thumbnail_offset, segment_count, checksum)

class BitPackV2Codec:
    """Lossless code-to-pixels encoder/decoder for PixelOS"""

    def __init__(self, spec: "BitPackSpec" = None):
        self.spec = spec or BitPackSpec()

    def encode_to_buffer(self, source_text: str, lang_id: str = "pixelpy", compress: bool = False) -> np.ndarray:
        """Encode source code to RGBA pixel buffer"""
        content = source_text.encode("utf-8")
        if compress:
            content = zstd.compress(content)

        header = BitPackHeaderV2(
            lang_id=lang_id,
            content_length=len(content),
            flags=1 if compress else 0,
            checksum=sha256(content).digest()
        )

        payload = header.serialize() + content

        bits_per_tile = self.spec.tile_w * self.spec.tile_h
        bytes_per_tile = (bits_per_tile + 7) // 8
        tiles_needed = (len(payload) + bytes_per_tile - 1) // bytes_per_tile

        # Calculate grid dimensions
        side = int(tiles_needed ** 0.5 + 0.999)
        cols, rows = side, (tiles_needed + side - 1) // side

        W = self.spec.margin * 2 + self.spec.finder + cols * self.spec.cell
        H = self.spec.margin * 2 + self.spec.finder + rows * self.spec.cell

        # Create RGBA buffer
        buffer = np.ones((H, W, 4), dtype=np.float32)

        # Draw finder patterns
        self._draw_finder_patterns(buffer, W, H)

        # Encode data tiles
        self._encode_data_tiles(buffer, payload, cols, rows)

        return buffer

    def _draw_finder_patterns(self, buffer: np.ndarray, W: int, H: int):
        """Draw QR-style finder patterns at corners"""
        fx, fy = self.spec.margin, self.spec.margin
        finder_positions = [
            (fx, fy),  # Top-left
            (W - self.spec.margin - self.spec.finder, fy),  # Top-right
            (fx, H - self.spec.margin - self.spec.finder)   # Bottom-left
        ]

        for x, y in finder_positions:
            self._draw_finder_square(buffer, x, y, self.spec.finder)

    def _draw_finder_square(self, buffer: np.ndarray, x: int, y: int, size: int):
        """Draw a single finder square (black/white/black pattern)"""
        # Outer black square
        buffer[y:y+size, x:x+size] = [0, 0, 0, 1]

        # Inner white square
        m = size // 6
        buffer[y+m:y+size-m, x+m:x+size-m] = [1, 1, 1, 1]

        # Center black square
        buffer[y+2*m:y+size-2*m, x+2*m:x+size-2*m] = [0, 0, 0, 1]

    def _encode_data_tiles(self, buffer: np.ndarray, payload: bytes, cols: int, rows: int):
        """Encode payload bytes as pixel tiles"""
        origin_x = self.spec.margin + self.spec.finder
        origin_y = self.spec.margin + self.spec.finder

        bit_index = 0
        for r in range(rows):
            for c in range(cols):
                ox = origin_x + c * self.spec.cell
                oy = origin_y + r * self.spec.cell

                # Draw tile border (black)
                buffer[oy:oy+self.spec.cell, ox:ox+self.spec.cell] = [0, 0, 0, 1]
                buffer[oy+1:oy+self.spec.cell-1, ox+1:ox+self.spec.cell-1] = [1, 1, 1, 1]

                # Encode payload bits
                for y in range(self.spec.tile_h):
                    for x in range(self.spec.tile_w):
                        byte_idx = bit_index // 8
                        bit_pos = 7 - (bit_index % 8)

                        if byte_idx < len(payload):
                            bit = (payload[byte_idx] >> bit_pos) & 1
                            color = [1, 1, 1, 1] if bit else [0, 0, 0, 1]
                            buffer[oy + 1 + y, ox + 1 + x] = color

                        bit_index += 1

    def decode_from_buffer(self, buffer: np.ndarray) -> Dict[str, Any]:
        """Decode BitPack v2 buffer back to source code"""
        H, W = buffer.shape[:2]

        # Convert to binary values
        binary_buffer = ((buffer[:, :, 0] + buffer[:, :, 1] + buffer[:, :, 2]) / 3 > 0.5).astype(np.uint8)

        # Extract grid parameters
        origin_x = self.spec.margin + self.spec.finder
        origin_y = self.spec.margin + self.spec.finder
        cols = (W - 2 * self.spec.margin - self.spec.finder) // self.spec.cell
        rows = (H - 2 * self.spec.margin - self.spec.finder) // self.spec.cell

        # Read bits from tiles
        bits = []
        for r in range(rows):
            for c in range(cols):
                ox = origin_x + c * self.spec.cell
                oy = origin_y + r * self.spec.cell

                for y in range(self.spec.tile_h):
                    for x in range(self.spec.tile_w):
                        px, py = ox + 1 + x, oy + 1 + y
                        if px < W and py < H:
                            bits.append(binary_buffer[py, px])

        # Convert bits to bytes
        payload = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                if i + j < len(bits):
                    byte = (byte << 1) | bits[i + j]
            payload.append(byte)

        # Parse header
        header = BitPackHeaderV2.deserialize(bytes(payload[:72]))

        # Extract content
        content = payload[72:72 + header.content_length]

        # Verify checksum
        if sha256(content).digest() != header.checksum:
            raise ValueError("SHA-256 checksum mismatch")

        # Decompress if necessary
        if header.flags & 1:
            content = zstd.decompress(content)

        return {
            "lang": header.lang_id,
            "content": content,
            "text": content.decode("utf-8"),
            "digest": header.checksum.hex()
        }

@dataclass
class BitPackSpec:
    tile_w: int = 8
    tile_h: int = 8
    cell: int = 10
    finder: int = 60
    margin: int = 16
