# VisualPython

A revolutionary Python library for executing code as immediate visual operations, bypassing traditional compilation.

## Installation
```bash
pip install visualpython
# Optional dependencies for enhanced features
pip install visualpython[watchdog,pygame,web]
```

## Quick Start
```bash
# Run a script directly
visualpython run examples/demo_live.py
# Monitor a script for live updates
visualpython live examples/demo_live.py --interval 0.2
```

## Features
- **Direct Visual Execution**: Parse Python code via AST and render as visuals (text, bars, tick marks).
- **Live File Monitoring**: Detect file changes in ~100ms and update visuals instantly.
- **Bitmap Font**: Pixel-perfect 5x7 font for text rendering.
- **Timeline OS Integration**: Code execution maps to keyframes, starting with font foundation at keyframe 5.0.
- **Hardware-Ready**: Export signals as CSV for Arduino/LED control.
- **Multiple Backends**: Tkinter (default), with plans for Pygame and web.

## Example
Create `demo_live.py`:
```python
x = 100
y = 150
size = 30
print("Direct Python Execution!")
print(f"Position: ({x}, {y})")
for i in range(3):
    offset = i * 40
    print(f"Element {i} at offset {offset}")
```

Run:
```bash
visualpython live demo_live.py
```

Edit `demo_live.py` (e.g., change `x = 200`) and watch the canvas update instantly!

## Roadmap
- Support for `if/else`, functions, and more Python constructs.
- Pygame and web backends.
- Hardware integration (serial communication).
- PyPI release.

## License
MIT License
