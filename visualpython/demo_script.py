# Demo script for VisualPython Unified testing
# This script demonstrates direct Python-to-pixels execution

# Variable assignments become visual elements
x = 100
y = 50
width = 200
height = 150

print("VisualPython Unified Demo")
print(f"Rectangle at ({x}, {y}) with size {width}x{height}")

# Math operations
area = width * height
perimeter = 2 * (width + height)

print(f"Area: {area}")
print(f"Perimeter: {perimeter}")

# Color calculations for visualization
red = 255
green = 128 
blue = 64

print(f"Color: RGB({red}, {green}, {blue})")

# Loop creates visual patterns
print("Creating pattern:")
for i in range(3):
    offset = i * 30
    size = 20 + i * 10
    print(f"  Element {i}: offset={offset}, size={size}")