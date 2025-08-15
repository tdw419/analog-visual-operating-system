import numpy as np

def sobel_filter(buffer):
    grayscale = np.dot(buffer[...,:3], [0.2989, 0.5870, 0.1140])
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])

    from scipy import ndimage
    edge_x = ndimage.convolve(grayscale, sobel_x)
    edge_y = ndimage.convolve(grayscale, sobel_y)

    edges = np.sqrt(edge_x**2 + edge_y**2)
    edges = np.clip(edges, 0, 1)

    return np.stack([edges, edges, edges, buffer[...,3]], axis=-1)

def update(buffer):
    # This is a placeholder for a real program
    # In a real program, you would load an image and apply the filter

    # Create a test image
    test_image = np.zeros_like(buffer)
    test_image[100:200, 100:200] = [1,1,1,1]

    filtered = sobel_filter(test_image)

    # Copy to the main buffer
    np.copyto(buffer, filtered)
