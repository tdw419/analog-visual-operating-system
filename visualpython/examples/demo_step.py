# VisualPython Stepper Demo
# Demonstrates step-by-step execution control

print("👟 VisualPython Stepper Demo")
print("Press SPACE to step through execution")

# Variables to step through
x = 10
y = 20
size = 5

print(f"Starting values: x={x}, y={y}, size={size}")

# Math operations - step through each one
width = x * 2
height = y + size
area = width * height

print(f"Calculated: width={width}, height={height}")
print(f"Final area: {area}")

# Loop with stepping - each iteration is a step
print("\nLoop execution (step through each iteration):")
for i in range(4):
    offset = i * 15
    value = size + i
    result = offset + value
    print(f"  Step {i}: offset={offset}, value={value}, result={result}")

# Conditional logic
if area > 100:
    status = "LARGE"
    multiplier = 2
else:
    status = "SMALL"
    multiplier = 1

print(f"\nCondition result: {status}")
print(f"Multiplier: {multiplier}")

# Final calculation
final_result = area * multiplier
print(f"Final result: {final_result}")

print("\n🎯 Use stepper controls to walk through each operation!")
print("Perfect for understanding code execution flow")