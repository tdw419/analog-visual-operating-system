# VisualPython Unified - Complete Usage Guide

## 🎯 Overview

VisualPython Unified transforms visual programming from a GUI-dependent activity into a **universal, testable, and automatable** process. The system provides:

- **Headless Execution**: Run visual programs without displays (perfect for CI/CD)
- **CSV Timeline Format**: Record, edit, and replay visual sequences  
- **Live Coding**: Auto-reload scripts on file changes
- **Round-Trip Workflow**: Perfect record → playback fidelity
- **Multi-Backend Support**: Same code runs on desktop, server, or embedded systems

## 🚀 Quick Start

### Basic Commands

```bash
# Run a script with GUI (interactive)
python visualpython_unified.py run demo.py --backend tkinter

# Run headlessly (saves frames as PNG/PPM)
python visualpython_unified.py run demo.py --backend sim --out-dir ./frames

# Record operations to CSV while running
python visualpython_unified.py run demo.py --backend sim --mirror recording.csv

# Play back a CSV file
python visualpython_unified.py csv play timeline.csv --backend sim --out-dir ./replay

# Live coding (auto-reload on file save)
python visualpython_unified.py run demo.py --live --backend sim
```

### Backend Options

| Backend | Description | Use Case |
|---------|-------------|----------|
| `tkinter` | GUI window | Interactive development |
| `sim` | Headless simulator | CI/CD, testing, automation |
| `simulator` | Alias for `sim` | Same as above |
| `console` | Text output | Debugging, minimal environments |

## 📁 File Formats

### Script Format (.py)
```python
# Example VisualPython script
# Variables become visual elements automatically

x = 100
y = 50  
width = 200
height = 150

print("VisualPython Demo")
print(f"Rectangle at ({x}, {y})")

# Math operations are visualized
area = width * height
print(f"Area: {area}")

# Loops create visual patterns
for i in range(3):
    offset = i * 30
    print(f"Element {i}: offset={offset}")
```

### CSV Timeline Format
```csv
frame,op,x,y,w,h,r,g,b,text,id
0,CLEAR,,,,,,0,17,0,,
0,RECT,100,50,60,40,40,120,240,,
0,TEXT,106,56,,,,144,238,144,HELLO,
0,COMMIT,,,,,,,,
1,PIXEL,150,70,,,255,0,0,,
1,COMMIT,,,,,,,,
```

**CSV Operations:**
- `CLEAR` - Clear screen with RGB color
- `RECT` - Draw rectangle (x,y,w,h,r,g,b)
- `TEXT` - Draw text (x,y,text,r,g,b)
- `PIXEL` - Set single pixel (x,y,r,g,b)
- `BUTTON` - Interactive button (x,y,w,h,r,g,b,text,id)
- `COMMIT` - Save frame

## 🔄 Workflows

### 1. Interactive Development
```bash
# Start with live reloading
python visualpython_unified.py run myapp.py --live --backend tkinter --mirror session.csv

# Edit myapp.py in your editor
# Save → See changes instantly
# session.csv captures everything for later replay
```

### 2. Automated Testing
```bash
# Generate test frames
python visualpython_unified.py run test_visual.py --backend sim --out-dir ./test_output

# Compare against baseline
diff -r ./test_output ./baseline_frames

# Or use in CI pipeline
python visualpython_unified.py csv play regression_test.csv --backend sim --out-dir ./ci_frames
```

### 3. Data Visualization Pipeline
```bash
# Create timeline from data
python generate_timeline.py data.json > visualization.csv

# Preview the visualization
python visualpython_unified.py csv play visualization.csv --backend sim --frame-delay 0.1

# Generate final frames
python visualpython_unified.py csv play visualization.csv --backend sim --out-dir ./final_frames
```

### 4. Interactive Prototyping
```bash
# Design with buttons
python visualpython_unified.py csv play ui_mockup.csv --backend sim --live

# Edit ui_mockup.csv in real-time
# Test different layouts instantly
```

## 🧪 Testing & Validation

### Run Integration Tests
```bash
python test_unified_integration.py
```

### Validate Round-Trip Fidelity
```bash
# Record a sequence
python visualpython_unified.py run demo.py --backend sim --mirror original.csv --out-dir ./original

# Play it back  
python visualpython_unified.py csv play original.csv --backend sim --out-dir ./replay

# Compare (should be identical)
diff -r ./original ./replay
```

## ⚡ Advanced Features

### Live File Watching
Automatically reload scripts or CSV files when they change:

```bash
# Watch Python script
python visualpython_unified.py run app.py --live --backend sim

# Watch CSV timeline
python visualpython_unified.py csv play timeline.csv --live --backend sim
```

### CSV Recording Options
```bash
# Record any run mode
python visualpython_unified.py run script.py --mirror output.csv
python visualpython_unified.py live script.py --mirror session.csv

# Dedicated recording mode
python visualpython_unified.py csv record script.py --csv-out precise.csv --mode raw
```

### Frame-by-Frame Control
```bash
# Slow playback for debugging
python visualpython_unified.py csv play animation.csv --frame-delay 1.0

# Quick playback for testing
python visualpython_unified.py csv play animation.csv --frame-delay 0.0
```

## 🎨 Creative Applications

### Animation Sequences
Create frame-based animations in CSV:
```csv
frame,op,x,y,w,h,r,g,b,text
0,CLEAR,,,,,,0,0,0,
0,RECT,100,100,50,50,255,0,0,
1,CLEAR,,,,,,0,0,0,
1,RECT,110,100,50,50,255,128,0,
2,CLEAR,,,,,,0,0,0,
2,RECT,120,100,50,50,255,255,0,
```

### Interactive Mockups
Design UI elements with buttons:
```csv
frame,op,x,y,w,h,r,g,b,text,id
0,BUTTON,100,100,80,40,50,100,200,Start,btn_start
0,BUTTON,200,100,80,40,200,50,50,Stop,btn_stop
```

### Data-Driven Visuals
Generate CSV from data sources:
```python
import pandas as pd
import csv

# Load data
df = pd.read_csv('sensor_data.csv')

# Generate visual timeline
with open('sensor_viz.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['frame', 'op', 'x', 'y', 'w', 'h', 'r', 'g', 'b', 'text'])
    
    for i, row in df.iterrows():
        writer.writerow([i, 'RECT', 50, 50, row['value'], 20, 255, 0, 0, ''])
        writer.writerow([i, 'COMMIT', '', '', '', '', '', '', '', ''])
```

## 🔧 Configuration

### Output Directory Structure
```
project/
├── scripts/          # Python scripts
│   └── demo.py
├── timelines/        # CSV files
│   └── animation.csv
├── frames/           # Generated images
│   ├── vp_sim_0000.png
│   ├── vp_sim_0001.png
│   └── ...
└── recordings/       # Captured sessions
    └── session.csv
```

### Performance Tuning
```bash
# High-resolution frames
python visualpython_unified.py run script.py --width 1920 --height 1080 --backend sim

# Memory-efficient mode (smaller frames)
python visualpython_unified.py run script.py --width 400 --height 300 --backend sim

# Fast CSV playback (no delays)
python visualpython_unified.py csv play data.csv --frame-delay 0 --backend sim
```

## 🚀 Production Deployment

### CI/CD Integration
```yaml
# .github/workflows/visual-tests.yml
name: Visual Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.8'
    - name: Run visual tests
      run: |
        python visualpython_unified.py csv play tests/regression.csv --backend sim --out-dir ./test-output
        # Add frame comparison logic here
```

### Docker Container
```dockerfile
FROM python:3.8-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "visualpython_unified.py", "csv", "play", "production.csv", "--backend", "sim"]
```

## 🎯 Next Steps

### Planned Enhancements
1. **Button System**: Full interactive element support
2. **Binary Format**: Optimized storage for dense animations  
3. **Web Export**: Browser-based preview capability
4. **Analog Output**: Hardware signal generation
5. **Visual Diff**: Compare timelines and detect changes

### Contributing
The VisualPython Unified system is designed for extensibility:

- **New Backends**: Implement the `DrawAPI` interface
- **New Operations**: Extend the CSV schema
- **New Workflows**: Build on the CLI framework

## 📚 Examples Repository

Check the following files for complete examples:
- `demo_live.py` - Live coding demonstration
- `demo_buttons.csv` - Interactive elements
- `test_unified_integration.py` - Comprehensive test suite

---

**VisualPython Unified** - Bridging creative coding, automated testing, and production deployment through a unified visual programming environment.