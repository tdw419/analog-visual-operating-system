#!/usr/bin/env python3
"""
Live Demo Test Script for VisualPython Unified

This script demonstrates the --live functionality by creating
simple visual elements that can be easily modified to test
the auto-reload feature.

Edit the variables below and save to see changes instantly!
"""

# Variables that affect visual output - edit these!
x_position = 100
y_position = 50
rect_width = 200
rect_height = 100

# Colors (0-255 RGB values)
bg_red = 0
bg_green = 20
bg_blue = 40

rect_red = 100
rect_green = 200
rect_blue = 255

text_red = 255
text_green = 255
text_blue = 0

# Animation parameters
frame_count = 3
offset_increment = 30

print("🎨 VisualPython Live Demo Test")
print(f"Rectangle: ({x_position}, {y_position}) {rect_width}x{rect_height}")
print(f"Background: RGB({bg_red}, {bg_green}, {bg_blue})")
print(f"Rectangle Color: RGB({rect_red}, {rect_green}, {rect_blue})")
print(f"Text Color: RGB({text_red}, {text_green}, {text_blue})")
print(f"Animation: {frame_count} frames, offset={offset_increment}")

# Create visual elements
for i in range(frame_count):
    frame_x = x_position + (i * offset_increment)
    frame_y = y_position + (i * 10)
    
    # Calculate frame-specific colors
    frame_red = min(255, rect_red + i * 20)
    frame_green = max(0, rect_green - i * 30)
    frame_blue = rect_blue
    
    print(f"  Frame {i}: pos=({frame_x}, {frame_y}) color=RGB({frame_red}, {frame_green}, {frame_blue})")

# Instructions for testing --live
print("\n" + "="*60)
print("🔄 LIVE TESTING INSTRUCTIONS:")
print("1. Run with: python visualpython_unified.py run test_live_demo.py --backend sim --live")
print("2. Edit values above (colors, positions, frame_count)")
print("3. Save this file")
print("4. Watch output update automatically!")
print("5. Check ./vp_sim_frames/ for new PNG files")
print("="*60)

# Test with mirror flag too
print("\n💾 WITH CSV RECORDING:")
print("Run: python visualpython_unified.py run test_live_demo.py --backend sim --live --mirror live_session.csv")
print("This will record all changes to live_session.csv for later replay!")