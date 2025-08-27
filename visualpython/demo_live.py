# VisualPython Live Demo
# This script demonstrates live coding with the unified simulator
# Try editing values below and saving to see instant updates!

import math
import time

# Animation parameters - edit these and save to see changes!
circle_x = 400
circle_y = 300
circle_radius = 50
color_red = 100
color_green = 200
color_blue = 255

# Background color
bg_red = 0
bg_green = 20
bg_blue = 40

print("🎨 VisualPython Live Demo")
print(f"Circle at ({circle_x}, {circle_y}) with radius {circle_radius}")
print(f"Color: RGB({color_red}, {color_green}, {color_blue})")

# Create animated elements
for i in range(8):
    angle = i * (math.pi * 2 / 8)
    offset_x = int(math.cos(angle) * circle_radius)
    offset_y = int(math.sin(angle) * circle_radius)
    
    dot_x = circle_x + offset_x
    dot_y = circle_y + offset_y
    
    # Vary color based on position
    dot_red = min(255, color_red + i * 20)
    dot_green = min(255, color_green + i * 10)
    dot_blue = min(255, color_blue - i * 15)
    
    print(f"  Dot {i}: ({dot_x}, {dot_y}) RGB({dot_red}, {dot_green}, {dot_blue})")

# Pattern generation
pattern_size = 60
pattern_count = 5

print(f"\nGenerating {pattern_count} pattern elements:")
for i in range(pattern_count):
    pattern_x = 100 + i * 80
    pattern_y = 100
    pattern_width = pattern_size - i * 8
    pattern_height = pattern_size - i * 8
    
    # Rainbow colors
    hue_red = int(255 * (i / pattern_count))
    hue_green = int(255 * ((i + 1) % pattern_count / pattern_count))
    hue_blue = int(255 * ((i + 2) % pattern_count / pattern_count))
    
    print(f"  Pattern {i}: ({pattern_x}, {pattern_y}) {pattern_width}x{pattern_height}")
    print(f"             Color: RGB({hue_red}, {hue_green}, {hue_blue})")

# Text display
message = "LIVE CODING ROCKS!"
text_x = 200
text_y = 500
text_red = 255
text_green = 255
text_blue = 0

print(f"\nText: '{message}' at ({text_x}, {text_y})")
print(f"Text Color: RGB({text_red}, {text_green}, {text_blue})")

# Instructions for live editing
print("\n" + "="*50)
print("🔄 LIVE EDITING INSTRUCTIONS:")
print("1. Run with: python visualpython_unified.py run demo_live.py --live --backend sim")
print("2. Edit any values above (colors, positions, sizes)")
print("3. Save the file")
print("4. Watch the output update automatically!")
print("="*50)