"""
Example demonstrating hardware control with VisualPython.

This shows how Python variables can directly control Arduino hardware
through signal export and live monitoring.
"""

import time
import math

print("🔧 VisualPython Hardware Control Demo")
print("=" * 45)

# LED Control - These values control actual hardware!
led_brightness = 128    # 0-255, controls LED brightness
led_pin = 13           # Arduino pin number

print(f"💡 LED Pin {led_pin}: brightness = {led_brightness}")

# Servo Control  
servo_angle = 90       # 0-180 degrees
servo_pin = 9         # Arduino pin number

print(f"🔄 Servo Pin {servo_pin}: angle = {servo_angle}°")

# Motor Control
motor_speed = 150     # 0-255, motor speed
motor_pin = 10        # Arduino pin number

print(f"⚡ Motor Pin {motor_pin}: speed = {motor_speed}")

# RGB LED Strip Control
rgb_red = 255
rgb_green = 128
rgb_blue = 64
rgb_pin = 6

print(f"🌈 RGB Pin {rgb_pin}: R={rgb_red}, G={rgb_green}, B={rgb_blue}")

# Animated values - try changing the math!
current_time = time.time() % 10  # 10-second cycle

# Breathing LED effect
breathing_value = int(128 + 127 * math.sin(current_time * 2))
print(f"💨 Breathing LED: {breathing_value}")

# Sweeping servo
sweep_angle = int(90 + 45 * math.sin(current_time))
print(f"↔️  Sweeping Servo: {sweep_angle}°")

# Color cycling
cycle_red = int(128 + 127 * math.sin(current_time))
cycle_green = int(128 + 127 * math.sin(current_time + 2))
cycle_blue = int(128 + 127 * math.sin(current_time + 4))

print(f"🎨 Color Cycle: R={cycle_red}, G={cycle_green}, B={cycle_blue}")

# Temperature sensor simulation
base_temp = 22.5  # Base temperature in Celsius
temp_variation = 5.0 * math.sin(current_time * 0.5)
current_temp = base_temp + temp_variation

print(f"🌡️  Temperature: {current_temp:.1f}°C")

# Fan control based on temperature
if current_temp > 25:
    fan_speed = int((current_temp - 25) * 50)
    fan_status = "ON"
else:
    fan_speed = 0
    fan_status = "OFF"

print(f"🌀 Fan: {fan_status} (speed: {fan_speed})")

# Alarm system
alarm_threshold = 30
if current_temp > alarm_threshold:
    alarm_active = True
    alarm_frequency = 1000  # Hz
else:
    alarm_active = False
    alarm_frequency = 0

print(f"🚨 Alarm: {'ACTIVE' if alarm_active else 'OFF'} ({alarm_frequency}Hz)")

print("\n🔥 Try changing any values above!")
print("   1. Run: visualpython live hardware_control.py")
print("   2. Edit values and save this file")
print("   3. Watch visual bars change instantly")
print("   4. Export signals: visualpython signals hardware_control.py --arduino control.ino")
print("   5. Upload control.ino to Arduino to see physical results!")

print("\n📡 Hardware Integration Steps:")
print("   • Connect RGB LED to pins 9, 10, 11")
print("   • Connect servo to pin 6")
print("   • Connect buzzer to pin 7")
print("   • Run signal export to generate Arduino code")
print("   • Upload and watch your Python variables control hardware!")