"""
Integration tests for the enhanced kernel system with simulator.
"""
import pytest
import numpy as np
import tempfile
from pathlib import Path
from pxos_py.kernels import MoveKernel, ThreshKernel, kernel_registry
from pxos_core.screen_native_sim import setup_simulation_context, load_program

class TestKernelIntegration:
    """Integration tests for kernel system with simulator."""

    def test_simulator_with_kernels(self):
        """Test that simulator properly integrates with kernel system."""
        # Create temporary program
        program_content = '''
import numpy as np
from pxos_py.kernels import kernel_registry

def setup(ctx):
    surf = ctx["surface"]
    W, H = surf.get_size()
    ctx["fb"] = ctx["fb_class"].empty(H, W)
    ctx["fb"].buf[H//2, W//2] = np.array([0, 1, 0, 1], dtype=np.float32)

def update(ctx, dt_ms):
    fb = ctx["fb"]
    H, W = fb.buf.shape[:2]

    # Use kernel registry
    move_kernel = kernel_registry.get_kernel("move")
    thresh_kernel = kernel_registry.get_kernel("thresh")

    # Create mask for green pixels
    head_mask = thresh_kernel.apply(fb.buf, channel=1, gt=True, value=0.5)

    # Create direction field (move right)
    dir_field = np.zeros((H, W), dtype=np.int32)
    dir_field[:, :] = 0  # Move right

    # Apply movement
    fb.buf = move_kernel.apply(fb.buf, mask=head_mask, dir_field=dir_field, step=1)

    fb.blit_to(ctx["surface"])
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(program_content)
            temp_program = f.name

        try:
            # Setup simulation
            args = type('Args', (), {
                'program': temp_program,
                'steps': 10,
                'headless': True,
                'fps': 60,
                'color_space': 'rgb',
                'profile': False
            })()

            ctx = setup_simulation_context(args)

            # Load program
            update_func = load_program(ctx, temp_program)
            assert update_func is not None

            # Run a few updates
            for i in range(5):
                update_func(ctx, 16)  # 16ms per frame (~60 FPS)

            # Verify that the pixel moved
            initial_pos = (256, 256)
            final_pos = None

            # Find the green pixel
            green_pixels = np.where(ctx["fb"].buf[:, :, 1] > 0.5)
            if len(green_pixels[0]) > 0:
                final_pos = (green_pixels[1][0], green_pixels[0][0])

            assert final_pos is not None
            assert final_pos[0] > initial_pos[0]  # Should have moved right

        finally:
            Path(temp_program).unlink()

    def test_kernel_registry(self):
        """Test kernel registry functionality."""
        # Test getting kernels
        move_kernel = kernel_registry.get_kernel("move")
        assert isinstance(move_kernel, MoveKernel)

        thresh_kernel = kernel_registry.get_kernel("thresh")
        assert isinstance(thresh_kernel, ThreshKernel)

        # Test listing kernels
        kernels = kernel_registry.list_kernels()
        assert "move" in kernels
        assert "thresh" in kernels

        # Test unknown kernel
        with pytest.raises(Exception):
            kernel_registry.get_kernel("unknown")

    def test_error_handling(self):
        """Test error handling in kernel operations."""
        # Create invalid buffer
        invalid_buf = np.random.rand(100, 100, 3).astype(np.float32)  # Wrong channels

        kernel = MoveKernel()

        # Should raise error for invalid buffer
        with pytest.raises(Exception):
            kernel.apply(invalid_buf,
                         np.ones((100, 100), dtype=bool),
                         np.zeros((100, 100), dtype=np.int32))

def run_integration_tests():
    """Run all integration tests."""
    print("Running kernel integration tests...")

    test_instance = TestKernelIntegration()

    try:
        test_instance.test_simulator_with_kernels()
        print("✅ Simulator integration test passed")
    except Exception as e:
        print(f"❌ Simulator integration test failed: {e}")

    try:
        test_instance.test_kernel_registry()
        print("✅ Kernel registry test passed")
    except Exception as e:
        print(f"❌ Kernel registry test failed: {e}")

    try:
        test_instance.test_error_handling()
        print("✅ Error handling test passed")
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")

if __name__ == "__main__":
    run_integration_tests()
