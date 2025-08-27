# Demo script for Python-to-CSV transpilation
# This demonstrates direct semantic conversion vs pixel capture

# Variable assignments become visual operations
x = 100
y = 50
width = 200
height = 150

print("VisualPython Transpiler Demo")
print(f"Rectangle: {width} x {height}")

# Math operations are preserved semantically
area = width * height
perimeter = 2 * (width + height)

print(f"Area: {area}")
print(f"Perimeter: {perimeter}")

# Clear the screen with dark background
clear(0, 20, 40)

# Draw visual elements with exact semantic operations
rect(x, y, width, height, 100, 200, 255)
text(x + 10, y + 10, "SEMANTIC", 255, 255, 255)

# Commit this frame
commit()

# Loop creates frame sequence (not just pixel updates)
for i in range(3):
    clear(0, 20, 40)
    offset = i * 30
    rect(x + offset, y, 60, 40, 255 - i * 50, 100 + i * 50, 200)
    text(x + offset + 5, y + 15, f"Frame {i}", 255, 255, 255)
    commit()

print("Transpilation complete!")
print("This generates semantic CSV operations, not pixel captures")