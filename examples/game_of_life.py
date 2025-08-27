import numpy as np

def update(buffer):
    # Get the current state of the game
    state = buffer[..., 0] > 0.5

    # Count neighbors
    neighbors = np.zeros_like(state, dtype=int)
    neighbors[1:, 1:] += state[:-1, :-1]
    neighbors[1:, :-1] += state[:-1, 1:]
    neighbors[:-1, 1:] += state[1:, :-1]
    neighbors[:-1, :-1] += state[1:, 1:]
    neighbors[1:, :] += state[:-1, :]
    neighbors[:-1, :] += state[1:, :]
    neighbors[:, 1:] += state[:, :-1]
    neighbors[:, :-1] += state[:, 1:]

    # Apply the rules of the game
    birth = (neighbors == 3) & ~state
    survive = ((neighbors == 2) | (neighbors == 3)) & state

    # Update the buffer
    buffer[..., 0] = (birth | survive).astype(np.float32)
    buffer[..., 1] = (birth | survive).astype(np.float32)
    buffer[..., 2] = (birth | survive).astype(np.float32)
