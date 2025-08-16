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

# Segment types
SEGMENT_TYPE_CODE = 1
SEGMENT_TYPE_SIGNATURE = 2
SEGMENT_TYPE_SBOM = 3

@dataclass
class BitPackSegmentHeader:
    """Header for a single data segment within the cartridge."""
    segment_type: int = 0
    data_length: int = 0

    HEADER_SIZE = 8

    def serialize(self) -> bytes:
        return (self.segment_type.to_bytes(4, 'little') +
                self.data_length.to_bytes(4, 'little'))

    @classmethod
    def deserialize(cls, data: bytes) -> "BitPackSegmentHeader":
        segment_type = int.from_bytes(data[0:4], 'little')
        data_length = int.from_bytes(data[4:8], 'little')
        return cls(segment_type, data_length)

class BitPackV2Codec:
    """Lossless code-to-pixels encoder/decoder for PixelOS"""

    def __init__(self, spec: "BitPackSpec" = None):
        self.spec = spec or BitPackSpec()

    def encode_to_buffer(
        self,
        code_bytes: bytes,
        lang_id: str = "pixelpy",
        is_compressed: bool = False,
        signature: Optional[bytes] = None,
        sbom_bytes: Optional[bytes] = None,
    ) -> np.ndarray:
        """Encode code bytes and metadata to a segmented RGBA pixel buffer."""
        segments = []

        # --- Code Segment ---
        code_digest = sha256(code_bytes).digest()
        segments.append({"type": SEGMENT_TYPE_CODE, "data": code_bytes})

        # --- Signature Segment ---
        if signature:
            segments.append({"type": SEGMENT_TYPE_SIGNATURE, "data": signature})

        # --- SBOM Segment ---
        if sbom_bytes:
            segments.append({"type": SEGMENT_TYPE_SBOM, "data": sbom_bytes})

        # --- Construct Payload from Segments ---
        payload_data = bytearray()
        for seg in segments:
            seg_header = BitPackSegmentHeader(
                segment_type=seg["type"], data_length=len(seg["data"])
            )
            payload_data.extend(seg_header.serialize())
            payload_data.extend(seg["data"])

        # --- Main Header ---
        header = BitPackHeaderV2(
            lang_id=lang_id,
            content_length=len(payload_data),
            flags=1 if is_compressed else 0,
            checksum=code_digest,
            segment_count=len(segments),
        )

        payload = header.serialize() + payload_data

        bits_per_tile = self.spec.tile_w * self.spec.tile_h
        bytes_per_tile = (bits_per_tile + 7) // 8
        tiles_needed = (len(payload) + bytes_per_tile - 1) // bytes_per_tile

        side = int(tiles_needed ** 0.5 + 0.999)
        cols, rows = side, (tiles_needed + side - 1) // side

        W = self.spec.margin * 2 + self.spec.finder + cols * self.spec.cell
        H = self.spec.margin * 2 + self.spec.finder + rows * self.spec.cell

        buffer = np.ones((H, W, 4), dtype=np.float32)
        self._draw_finder_patterns(buffer, W, H)
        self._encode_data_tiles(buffer, payload, cols, rows)
        return buffer

    def _draw_finder_patterns(self, buffer: np.ndarray, W: int, H: int):
        fx, fy = self.spec.margin, self.spec.margin
        finder_positions = [
            (fx, fy),
            (W - self.spec.margin - self.spec.finder, fy),
            (fx, H - self.spec.margin - self.spec.finder)
        ]
        for x, y in finder_positions:
            self._draw_finder_square(buffer, x, y, self.spec.finder)

    def _draw_finder_square(self, buffer: np.ndarray, x: int, y: int, size: int):
        buffer[y:y+size, x:x+size] = [0, 0, 0, 1]
        m = size // 6
        buffer[y+m:y+size-m, x+m:x+size-m] = [1, 1, 1, 1]
        buffer[y+2*m:y+size-2*m, x+2*m:x+size-2*m] = [0, 0, 0, 1]

    def _encode_data_tiles(self, buffer: np.ndarray, payload: bytes, cols: int, rows: int):
        origin_x = self.spec.margin + self.spec.finder
        origin_y = self.spec.margin + self.spec.finder
        bit_index = 0
        for r in range(rows):
            for c in range(cols):
                ox = origin_x + c * self.spec.cell
                oy = origin_y + r * self.spec.cell
                buffer[oy:oy+self.spec.cell, ox:ox+self.spec.cell] = [0, 0, 0, 1]
                buffer[oy+1:oy+self.spec.cell-1, ox+1:ox+self.spec.cell-1] = [1, 1, 1, 1]
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
        H, W = buffer.shape[:2]
        binary_buffer = ((buffer[:, :, 0] + buffer[:, :, 1] + buffer[:, :, 2]) / 3 > 0.5).astype(np.uint8)
        origin_x = self.spec.margin + self.spec.finder
        origin_y = self.spec.margin + self.spec.finder
        cols = (W - 2 * self.spec.margin - self.spec.finder) // self.spec.cell
        rows = (H - 2 * self.spec.margin - self.spec.finder) // self.spec.cell
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
        payload = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                if i + j < len(bits):
                    byte = (byte << 1) | bits[i + j]
            payload.append(byte)
        header = BitPackHeaderV2.deserialize(bytes(payload[:72]))
        decoded_segments = {}
        offset = 72
        for _ in range(header.segment_count):
            if offset + BitPackSegmentHeader.HEADER_SIZE > len(payload):
                raise ValueError("Buffer truncated while reading segment header.")
            seg_header_bytes = payload[offset : offset + BitPackSegmentHeader.HEADER_SIZE]
            seg_header = BitPackSegmentHeader.deserialize(seg_header_bytes)
            offset += BitPackSegmentHeader.HEADER_SIZE
            if offset + seg_header.data_length > len(payload):
                raise ValueError(f"Buffer truncated while reading segment type {seg_header.segment_type}.")
            seg_data = payload[offset : offset + seg_header.data_length]
            offset += seg_header.data_length
            decoded_segments[seg_header.segment_type] = seg_data
        code_content = decoded_segments.get(SEGMENT_TYPE_CODE)
        if code_content is None:
            raise ValueError("Cartridge does not contain a code segment.")
        if sha256(code_content).digest() != header.checksum:
            raise ValueError("Code segment checksum mismatch.")
        is_compressed = header.flags & 1
        if is_compressed:
            # This is a bug, should be code_content that is decompressed
            code_content = zstd.decompress(code_content)
        output = {
            "lang": header.lang_id,
            "content": code_content,
            "text": code_content.decode("utf-8"),
            "digest": header.checksum.hex(),
            "signature": decoded_segments.get(SEGMENT_TYPE_SIGNATURE),
            "sbom_raw": decoded_segments.get(SEGMENT_TYPE_SBOM),
        }
        if output["sbom_raw"] and is_compressed:
            output["sbom_raw"] = zstd.decompress(output["sbom_raw"])
        return output

@dataclass
class BitPackSpec:
    tile_w: int = 8
    tile_h: int = 8
    cell: int = 10
    finder: int = 60
    margin: int = 16
