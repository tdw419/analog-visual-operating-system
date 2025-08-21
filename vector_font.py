"""
A simple, device-independent vector font representation.

Each character is a dictionary entry where the key is the character and the
value is a list of strokes. Each stroke is a list of (x, y) tuples in a
normalized [0, 1] coordinate space, where (0, 0) is the bottom-left corner.
"""

SIMPLE_FONT = {
    'A': [
        [(0.2, 0.1), (0.5, 0.9)],      # Left leg
        [(0.8, 0.1), (0.5, 0.9)],      # Right leg
        [(0.35, 0.5), (0.65, 0.5)],    # Crossbar
    ],
    'B': [
        [(0.2, 0.1), (0.2, 0.9)],      # Stem
        [(0.2, 0.9), (0.7, 0.9), (0.9, 0.7), (0.7, 0.5), (0.2, 0.5)],  # Top loop
        [(0.2, 0.5), (0.8, 0.5), (1.0, 0.3), (0.8, 0.1), (0.2, 0.1)],  # Bottom loop
    ],
    'C': [
        [(0.9, 0.7), (0.7, 0.9), (0.3, 0.9), (0.1, 0.7), (0.1, 0.3), (0.3, 0.1), (0.7, 0.1), (0.9, 0.3)],
    ],
    'X': [
        [(0.2, 0.1), (0.8, 0.9)],      # Stroke 1
        [(0.2, 0.9), (0.8, 0.1)],      # Stroke 2
    ],
}
