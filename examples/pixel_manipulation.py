import numpy as np

def update(buffer):
    H, W, _ = buffer.shape

    # Create a ripple effect
    x, y = np.meshgrid(np.arange(W), np.arange(H))

    center_x = W / 2
    center_y = H / 2

    dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)

    # Create a ripple pattern
    ripple = np.sin(dist / 10) * 0.1

    # Apply the ripple to the buffer
    buffer[..., 0] += ripple
    buffer[..., 1] += ripple
    buffer[..., 2] += ripple

    # Clip the values to be between 0 and 1
    np.clip(buffer, 0, 1, out=buffer)
