"""
Performance benchmarks for the enhanced kernel system.
"""
import time
import numpy as np
import pytest
from pxos_py.kernels import MoveKernel, ThreshKernel, BoxBlurKernel, ColorTransformKernel

class TestKernelPerformance:
    """Performance test suite for PXOS kernels."""

    @pytest.fixture
    def test_buffer(self):
        """Create test buffer for benchmarks."""
        return np.random.rand(512, 512, 4).astype(np.float32)

    @pytest.fixture
    def test_mask(self):
        """Create test mask for benchmarks."""
        mask = np.random.rand(512, 512) > 0.5
        return mask

    @pytest.fixture
    def test_dir_field(self):
        """Create test direction field for benchmarks."""
        return np.random.randint(0, 8, (512, 512), dtype=np.int32)

    def benchmark_move_kernel(self, test_buffer, test_mask, test_dir_field, benchmark):
        """Benchmark MoveKernel performance."""
        kernel = MoveKernel()

        def move_operation():
            return kernel.apply(test_buffer, test_mask, test_dir_field)

        result = benchmark(move_operation)
        assert result.shape == test_buffer.shape

    def benchmark_thresh_kernel(self, test_buffer, benchmark):
        """Benchmark ThreshKernel performance."""
        kernel = ThreshKernel()

        def thresh_operation():
            return kernel.apply(test_buffer, channel=1, gt=True, value=0.5)

        result = benchmark(thresh_operation)
        assert result.dtype == bool

    def benchmark_blur_kernel(self, test_buffer, benchmark):
        """Benchmark BoxBlurKernel performance."""
        kernel = BoxBlurKernel()

        def blur_operation():
            return kernel.apply(test_buffer, iters=3)

        result = benchmark(blur_operation)
        assert result.shape == test_buffer.shape

    def benchmark_color_transform(self, test_buffer, benchmark):
        """Benchmark ColorTransformKernel performance."""
        kernel = ColorTransformKernel()

        def transform_operation():
            return kernel.apply(test_buffer, from_space="rgb", to_space="hsl")

        result = benchmark(transform_operation)
        assert result.shape == test_buffer.shape

    def test_tile_size_impact(self, test_buffer, test_mask, test_dir_field):
        """Test impact of tile size on MoveKernel performance."""
        kernel = MoveKernel()
        tile_sizes = [32, 64, 128, 256]

        results = {}
        for tile_size in tile_sizes:
            start_time = time.time()

            for _ in range(10):  # Multiple iterations for stable measurement
                kernel.apply(test_buffer, test_mask, test_dir_field, tile_size=tile_size)

            elapsed = time.time() - start_time
            results[tile_size] = elapsed / 10

        print("Tile size performance:")
        for tile_size, elapsed in results.items():
            print(f"  {tile_size}: {elapsed*1000:.2f}ms")

        # Verify that larger tiles are generally faster
        assert results[128] < results[32] * 0.8  # Should be at least 20% faster

def run_performance_tests():
    """Run all performance benchmarks."""
    test_instance = TestKernelPerformance()

    # Create test data
    test_buffer = np.random.rand(512, 512, 4).astype(np.float32)
    test_mask = np.random.rand(512, 512) > 0.5
    test_dir_field = np.random.randint(0, 8, (512, 512), dtype=np.int32)

    # Run benchmarks
    print("Running kernel performance benchmarks...")

    # MoveKernel benchmark
    start = time.time()
    for _ in range(100):
        MoveKernel().apply(test_buffer, test_mask, test_dir_field)
    move_time = (time.time() - start) / 100
    print(f"MoveKernel: {move_time*1000:.2f}ms per iteration")

    # ThreshKernel benchmark
    start = time.time()
    for _ in range(100):
        ThreshKernel().apply(test_buffer, channel=1, gt=True, value=0.5)
    thresh_time = (time.time() - start) / 100
    print(f"ThreshKernel: {thresh_time*1000:.2f}ms per iteration")

    # BoxBlurKernel benchmark
    start = time.time()
    for _ in range(10):
        BoxBlurKernel().apply(test_buffer, iters=3)
    blur_time = (time.time() - start) / 10
    print(f"BoxBlurKernel (3 iterations): {blur_time*1000:.2f}ms per iteration")

    # ColorTransform benchmark
    start = time.time()
    for _ in range(50):
        ColorTransformKernel().apply(test_buffer, from_space="rgb", to_space="hsl")
    color_time = (time.time() - start) / 50
    print(f"ColorTransformKernel: {color_time*1000:.2f}ms per iteration")

    # Test tile size impact
    test_instance.test_tile_size_impact(test_buffer, test_mask, test_dir_field)

if __name__ == "__main__":
    run_performance_tests()
