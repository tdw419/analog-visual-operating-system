"""
Enhanced kernel system for PXOS with vectorized operations and performance optimization.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from abc import ABC, abstractmethod
import logging
from pxos_py.errors import KernelExecutionError, BufferShapeError

logger = logging.getLogger(__name__)

class AbstractKernel(ABC):
    """Base class for all PXOS kernels."""

    @abstractmethod
    def apply(self, buf: np.ndarray, **kwargs) -> np.ndarray:
        """Apply the kernel operation to the buffer.

        Args:
            buf: Input buffer (H, W, C) float32
            **kwargs: Kernel-specific parameters

        Returns:
            Processed buffer (H, W, C) float32
        """
        pass

    def validate_input(self, buf: np.ndarray, **kwargs) -> None:
        """Validate input parameters."""
        if buf.ndim != 3 or buf.shape[2] != 4:
            raise BufferShapeError(f"Expected (H, W, 4) buffer, got {buf.shape}")
        if buf.dtype != np.float32:
            raise BufferShapeError(f"Expected float32 buffer, got {buf.dtype}")

class MoveKernel(AbstractKernel):
    """Moves pixels based on mask and direction field with vectorized operations."""

    def apply(self, buf: np.ndarray, mask: np.ndarray, dir_field: np.ndarray,
              step: int = 1, decay: Optional[float] = None,
              tile_size: int = 64, color_space: str = "rgb") -> np.ndarray:
        """Move pixels where mask is True by step pixels in directions from dir_field.

        Args:
            buf: Input buffer (H, W, 4) float32
            mask: Boolean mask (H, W) indicating pixels to move
            dir_field: Direction field (H, W) int32 (0=E, 1=SE, 2=S, ..., 7=NE)
            step: Number of pixels to move
            decay: Optional decay factor for moved pixels
            tile_size: Size of processing tiles for optimization
            color_space: Color space for processing

        Returns:
            Processed buffer with moved pixels
        """
        self.validate_input(buf, mask=mask, dir_field=dir_field)

        H, W = buf.shape[:2]
        result = buf.copy()

        # Direction vectors (E, SE, S, SW, W, NW, N, NE)
        directions = np.array([
            [1, 0], [1, 1], [0, 1], [-1, 1],
            [-1, 0], [-1, -1], [0, -1], [1, -1]
        ], dtype=np.int32)

        # Process in tiles for better cache locality
        for y_start in range(0, H, tile_size):
            for x_start in range(0, W, tile_size):
                y_end = min(y_start + tile_size, H)
                x_end = min(x_start + tile_size, W)

                # Extract tile
                tile_mask = mask[y_start:y_end, x_start:x_end]
                if not np.any(tile_mask):
                    continue

                tile_dir = dir_field[y_start:y_end, x_start:x_end]
                tile_buf = buf[y_start:y_end, x_start:x_end]

                # Calculate new positions
                dirs = directions[tile_dir]
                y_coords, x_coords = np.mgrid[y_start:y_end, x_start:x_end]

                new_y = np.clip(y_coords + dirs[:, :, 1] * step, 0, H - 1)
                new_x = np.clip(x_coords + dirs[:, :, 0] * step, 0, W - 1)

                # Apply movement only where mask is True
                valid_mask = tile_mask & ((new_y != y_coords) | (new_x != x_coords))
                if np.any(valid_mask):
                    result[new_y[valid_mask], new_x[valid_mask]] = tile_buf[valid_mask]
                    result[y_start:y_end, x_start:x_end][valid_mask] = [0, 0, 0, 0]

        # Apply decay if specified
        if decay is not None and decay > 0:
            result *= (1.0 - decay)

        logger.debug(f"MoveKernel applied: step={step}, decay={decay}, tiles={(H//tile_size)*(W//tile_size)}")
        return result

class ThreshKernel(AbstractKernel):
    """Creates boolean mask based on threshold conditions."""

    def apply(self, buf: np.ndarray, channel: int = 0, gt: bool = True,
              value: float = 0.5, color_space: str = "rgb") -> np.ndarray:
        """Create boolean mask based on channel threshold.

        Args:
            buf: Input buffer (H, W, 4) float32
            channel: Channel to threshold (0=R/H, 1=G/S, 2=B/L, 3=A)
            gt: If True, threshold greater than value; else less than or equal
            value: Threshold value
            color_space: Color space for processing

        Returns:
            Boolean mask (H, W)
        """
        self.validate_input(buf)

        if channel >= buf.shape[2]:
            raise KernelExecutionError(f"Invalid channel index: {channel}")

        channel_data = buf[:, :, channel]

        if gt:
            mask = channel_data > value
        else:
            mask = channel_data <= value

        logger.debug(f"ThreshKernel applied: channel={channel}, gt={gt}, value={value}")
        return mask

class BoxBlurKernel(AbstractKernel):
    """Applies box blur filter with optimized iterations."""

    def apply(self, buf: np.ndarray, iters: int = 1,
              color_space: str = "rgb") -> np.ndarray:
        """Apply box blur filter for specified iterations.

        Args:
            buf: Input buffer (H, W, 4) float32
            iters: Number of blur iterations
            color_space: Color space for processing

        Returns:
            Blurred buffer
        """
        self.validate_input(buf)

        result = buf.copy()

        for _ in range(iters):
            # Simple box blur using convolution
            kernel = np.ones((3, 3)) / 9
            for c in range(4):
                result[:, :, c] = self._convolve2d(result[:, :, c], kernel)

        logger.debug(f"BoxBlurKernel applied: iters={iters}")
        return result

    def _convolve2d(self, image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
        """Simple 2D convolution implementation."""
        kh, kw = kernel.shape
        ih, iw = image.shape
        output = np.zeros_like(image)

        # Pad the image
        padded = np.pad(image, ((kh//2, kh//2), (kw//2, kw//2)), mode='edge')

        for i in range(ih):
            for j in range(iw):
                output[i, j] = np.sum(padded[i:i+kh, j:j+kw] * kernel)

        return output

class ColorTransformKernel(AbstractKernel):
    """Transforms between color spaces (RGB <-> HSL)."""

    def apply(self, buf: np.ndarray, from_space: str = "rgb",
              to_space: str = "hsl") -> np.ndarray:
        """Transform color space of buffer.

        Args:
            buf: Input buffer (H, W, 4) float32
            from_space: Source color space
            to_space: Target color space

        Returns:
            Transformed buffer
        """
        self.validate_input(buf)

        if from_space == to_space:
            return buf.copy()

        result = buf.copy()

        if from_space == "rgb" and to_space == "hsl":
            result[:, :, :3] = self._rgb_to_hsl(buf[:, :, :3])
        elif from_space == "hsl" and to_space == "rgb":
            result[:, :, :3] = self._hsl_to_rgb(buf[:, :, :3])
        else:
            raise KernelExecutionError(f"Unsupported color space transform: {from_space} -> {to_space}")

        logger.debug(f"ColorTransformKernel applied: {from_space} -> {to_space}")
        return result

    def _rgb_to_hsl(self, rgb: np.ndarray) -> np.ndarray:
        """Convert RGB to HSL."""
        # Normalize to [0, 1]
        rgb = np.clip(rgb, 0, 1)

        max_val = np.max(rgb, axis=2)
        min_val = np.min(rgb, axis=2)
        delta = max_val - min_val

        # Hue calculation
        h = np.zeros_like(max_val)
        mask = delta != 0
        h[mask] = np.where(
            rgb[mask, 0] == max_val[mask],
            ((rgb[mask, 1] - rgb[mask, 2]) / delta[mask]) % 6,
            np.where(
                rgb[mask, 1] == max_val[mask],
                (rgb[mask, 2] - rgb[mask, 0]) / delta[mask] + 2,
                (rgb[mask, 0] - rgb[mask, 1]) / delta[mask] + 4
            )
        )
        h = h / 6.0

        # Lightness
        l = (max_val + min_val) / 2

        # Saturation
        s = np.zeros_like(l)
        mask = delta != 0
        s[mask] = delta[mask] / (1 - np.abs(2 * l[mask] - 1))

        return np.stack([h, s, l], axis=2)

    def _hsl_to_rgb(self, hsl: np.ndarray) -> np.ndarray:
        """Convert HSL to RGB."""
        h, s, l = hsl[:, :, 0], hsl[:, :, 1], hsl[:, :, 2]

        c = (1 - np.abs(2 * l - 1)) * s
        x = c * (1 - np.abs((h * 6) % 2 - 1))
        m = l - c / 2

        rgb = np.zeros_like(hsl)

        # Segment the hue into 6 parts
        mask = (h < 1/6)
        rgb[mask] = np.stack([c[mask], x[mask], np.zeros_like(c[mask])], axis=2)

        mask = (h >= 1/6) & (h < 2/6)
        rgb[mask] = np.stack([x[mask], c[mask], np.zeros_like(c[mask])], axis=2)

        mask = (h >= 2/6) & (h < 3/6)
        rgb[mask] = np.stack([np.zeros_like(c[mask]), c[mask], x[mask]], axis=2)

        mask = (h >= 3/6) & (h < 4/6)
        rgb[mask] = np.stack([np.zeros_like(c[mask]), x[mask], c[mask]], axis=2)

        mask = (h >= 4/6) & (h < 5/6)
        rgb[mask] = np.stack([x[mask], np.zeros_like(c[mask]), c[mask]], axis=2)

        mask = (h >= 5/6)
        rgb[mask] = np.stack([c[mask], np.zeros_like(c[mask]), x[mask]], axis=2)

        return np.clip(rgb + m[:, :, np.newaxis], 0, 1)

class KernelRegistry:
    """Registry for managing available kernels."""

    def __init__(self):
        self._kernels: Dict[str, AbstractKernel] = {
            "move": MoveKernel(),
            "thresh": ThreshKernel(),
            "blur": BoxBlurKernel(),
            "color_transform": ColorTransformKernel()
        }

    def get_kernel(self, name: str) -> AbstractKernel:
        """Get kernel by name."""
        if name not in self._kernels:
            raise KernelExecutionError(f"Unknown kernel: {name}")
        return self._kernels[name]

    def register_kernel(self, name: str, kernel: AbstractKernel) -> None:
        """Register a new kernel."""
        self._kernels[name] = kernel

    def list_kernels(self) -> List[str]:
        """List available kernel names."""
        return list(self._kernels.keys())

# Global kernel registry
kernel_registry = KernelRegistry()
