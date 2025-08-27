from dataclasses import dataclass, field
from typing import List, Tuple, Any, Dict, Optional
import uuid

@dataclass
class FiducialMarker:
    """Represents a single fiducial marker with its coordinates and type.

    These are absolute pixel coordinates on the program sheet.
    """
    x: int
    y: int
    marker_type: str = "alignment" # e.g., 'corner', 'grid', 'calibration'

@dataclass
class ProgramTile:
    """
    Defines the schema for a single analog program tile,
    embedding its operational payload, position, fiducial markers,
    and Error Correction Code (ECC) data for precision and integrity.
    """
    # --- Core Operational Payload ---
    # The low-level instruction set for the tile (e.g., LLIR tuple).
    # Example: ("DRAW_RECT", "10", "20", "40", "20", "64", "64", "64")
    payload: Tuple[str, ...] = field(default_factory=tuple)

    # --- Tile Metadata (for rendering and sheet layout) ---
    tile_id: str = field(default_factory=lambda: str(uuid.uuid4())) # A unique identifier for this specific tile instance.
    position_x: int = 0 # X-coordinate of the tile's top-left corner on the sheet.
    position_y: int = 0 # Y-coordinate of the tile's top-left corner on the sheet.
    width: int = 0      # Width of the tile in pixels/units.
    height: int = 0     # Height of the tile in pixels/units.

    # --- Precision & Verification Data ---
    # Fiducial markers associated with this tile's region for geometric correction.
    # These are absolute coordinates on the program sheet.
    fiducial_markers: List[FiducialMarker] = field(default_factory=list)

    # Error Correction Code (ECC) data for the payload.
    # This is the actual encoded ECC string/bits, derived from the payload.
    ecc_data: str = ""
    ecc_type: str = "parity" # Type of ECC used (e.g., 'parity', 'hamming16_12').

    # A simple checksum of the original payload (before ECC encoding) for quick integrity checks.
    # This can be a hash of the payload string.
    payload_checksum: str = ""
    payload_checksum_type: str = "sha256" # e.g., 'md5', 'sha256'

    # Optional: Version of the tile schema itself, for future compatibility.
    schema_version: str = "1.0"

@dataclass
class ProgramSheet:
    """Represents the entire program sheet to be rendered."""
    tiles: List[ProgramTile] = field(default_factory=list)

    # --- Global Sheet Metadata ---
    sheet_width: int = 256
    sheet_height: int = 256

    # Global fiducials for sheet-level alignment (e.g., corners of the entire canvas).
    global_fiducials: List[FiducialMarker] = field(default_factory=list)
    schema_version: str = "1.0"