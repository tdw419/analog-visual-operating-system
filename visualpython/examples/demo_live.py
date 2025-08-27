# VisualPython Live Demo
# Edit this file and save to see instant changes!

# Variables become visual elements immediately
x = 100
y = 150
size = 30

print("🔥 VisualPython Direct Execution!")
print(f"Position: ({x}, {y})")
print(f"Size: {size}")

# Math operations render instantly  
width = size * 2
height = size + 10
area = width * height

print(f"Dimensions: {width} x {height}")
print(f"Area: {area}")

# Loops create visual patterns
print("\nGenerating pattern:")
for i in range(3):
    offset = i * 40
    scale = size + i * 5
    print(f"  Element {i}: offset={offset}, scale={scale}")

# Conditional logic
if area > 500:
    status = "LARGE"
    priority = 1
else:
    status = "NORMAL"
    priority = 2

print(f"\nStatus: {status}")
print(f"Priority: {priority}")

# Color parameters for hardware
red = 255
green = 128
blue = 64

print(f"Color: RGB({red}, {green}, {blue})")

print("\n🎯 Try changing any numbers above and save this file!")
print("Watch the visual bars and colors update instantly!")
print("No compilation, no restarts - just immediate feedback!")