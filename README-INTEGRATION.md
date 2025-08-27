# Analog Code Workbench - Paste-and-Go Integration

A complete development environment for bridging digital programming and analog execution. This system provides a seamless "paste-and-go" workflow for converting any Python program into analog-executable format.

## Quick Start (2-minute smoke test)

1. **Run the workbench:**
   ```bash
   python simple_analog_workbench.py
   ```

2. **Click "Run with my Viewer"** → Pane 3 fills with CSV operations

3. **Watch the magic:** 
   - Pane 2 (tiles) + Pane 4 (results) update automatically
   - Edit a line in Pane 3 → both panes re-render in real-time

4. **Edit and experiment:**
   - Modify CSV operations directly
   - See immediate visual feedback
   - Export for hardware execution

## System Architecture

### Four-Pane Workbench
- **Pane 1:** Source code (editable, with source mirroring)
- **Pane 2:** Analog pixel tiles (visual program representation)
- **Pane 3:** CSV/IR operations (editable, the "truth layer")
- **Pane 4:** Live execution results (visual feedback)

### Core Components

#### 1. Viewer Adapter (`viewer_adapter_simple.py`)
Universal capture point for any Python drawing operations:
```python
import viewer_adapter_simple as VA

VA.reset()
VA.RECT(20, 20, 40, 20, 64)    # Capture rectangle
VA.SLEEP(30)                    # Capture timing
VA.DAC_WRITE(1, 180)           # Capture hardware ops
VA.COMMIT()                    # Frame boundary

csv_output = VA.get_captured_csv()
```

#### 2. Smoke-Test Viewer (`your_viewer_main.py`)
Example integration showing how to adapt any viewer:
```python
def main():
    VA.reset()
    # Your drawing operations here
    VA.RECT(x, y, w, h, gray)
    VA.COMMIT()
```

#### 3. Environment Configuration
No code changes needed - use environment variables:
```bash
# Windows
set ACW_VIEWER_MODULE=my_custom_viewer
set ACW_VIEWER_FUNC=render

# Linux/Mac
export ACW_VIEWER_MODULE=my_custom_viewer
export ACW_VIEWER_FUNC=render

python simple_analog_workbench.py
```

#### 4. Monkey Patching (`monkey_patch.py`)
Integrate with existing code without modification:
```python
import monkey_patch
monkey_patch.patch_visualpython()
# Now your existing viewer automatically captures operations
```

#### 5. Hardware Integration (`hardware_hooks.py`)
Connect CSV operations to real analog hardware:
```python
from hardware_hooks import AnalogHardware

hardware = AnalogHardware(use_real_hardware=True)
hardware.execute_csv_program(csv_content)
```

#### 6. ECC Tile Encoding (`ecc_tile_encoder.py`)
Drop-in upgrade from parity to Hamming error correction:
```python
# Replace:
from your_module import pack_bits
# With:
from ecc_tile_encoder import pack_bits
# Now your tiles have single-error correction!
```

## Integration Patterns

### Pattern 1: Direct Integration
Replace your drawing calls with adapter calls:
```python
# Before:
draw_rectangle(x, y, w, h, color)

# After:
import viewer_adapter_simple as VA
VA.RECT(x, y, w, h, grayscale_value)
```

### Pattern 2: Monkey Patching
No code changes required:
```python
import monkey_patch
monkey_patch.auto_patch()
# Run your existing code - operations automatically captured
```

### Pattern 3: Environment Configuration
Switch between viewers without editing code:
```bash
# Test with built-in viewer
python simple_analog_workbench.py

# Switch to your custom viewer
set ACW_VIEWER_MODULE=my_physics_sim
set ACW_VIEWER_FUNC=run_simulation
python simple_analog_workbench.py
```

## CSV Operation Format

The system uses a simple, human-readable CSV format:

```csv
# Basic drawing
RECT,20,20,40,20,64,64,64
SLEEP,30
COMMIT

# Hardware control
DAC_WRITE,1,180
ADC_READ,0
SYNC_ROW,1

# Advanced operations
FILTER,lowpass,1000,input_ch,output_ch
INTEGRATE,0.1,signal_ch,result_ch
```

## Hardware Integration

### Mock Hardware (for testing)
```python
from hardware_hooks import csv_player_with_hardware

csv_program = """
DAC_WRITE,0,100
SLEEP,50
ADC_READ,0
"""

csv_player_with_hardware(csv_program, use_real_hardware=False)
```

### Real Hardware Integration
1. Replace `MockDAC`/`MockADC` with real hardware interfaces
2. Set `use_real_hardware=True`
3. Add hardware initialization code
4. Connect to your analog devices

## Error Correction

Upgrade your tiles from simple parity to Hamming ECC:

```python
# Simple parity (current)
bits = pack_bits_simple_parity(opcode, operand)

# Hamming ECC (upgrade)
bits = pack_bits_hamming(opcode, operand)
# Single-error correction, double-error detection
```

## File Structure

```
analog-visual-operating-system/
├── simple_analog_workbench.py      # Main 4-pane workbench
├── viewer_adapter_simple.py        # Universal viewer adapter
├── your_viewer_main.py             # Smoke-test viewer example
├── monkey_patch.py                 # Optional monkey patching
├── hardware_hooks.py               # Hardware integration
├── ecc_tile_encoder.py             # ECC tile encoding
├── demo_complete_integration.py    # Complete demo
└── README-INTEGRATION.md           # This file
```

## Examples

### Example 1: Scientific Simulation
```python
# physics_sim.py
import numpy as np
import viewer_adapter_simple as VA

def run_physics_sim():
    VA.reset()
    
    # Simulate bouncing ball
    for t in range(100):
        x = 50 + t * 2
        y = 50 + abs(np.sin(t * 0.1) * 30)
        
        VA.RECT(int(x), int(y), 10, 10, 200)
        VA.COMMIT()
        VA.SLEEP(50)

# Run through workbench:
# set ACW_VIEWER_MODULE=physics_sim
# set ACW_VIEWER_FUNC=run_physics_sim
```

### Example 2: Hardware Control
```python
# pid_controller.py
import viewer_adapter_simple as VA

def pid_controller():
    VA.reset()
    
    # Read sensor
    VA.ADC_READ(0)
    
    # PID calculation (simplified)
    VA.DAC_WRITE(1, 128)  # Proportional term
    VA.DAC_WRITE(2, 64)   # Integral term
    VA.DAC_WRITE(3, 32)   # Derivative term
    
    # Output control signal
    VA.DAC_WRITE(0, 150)
    VA.COMMIT()
```

### Example 3: Visual Art
```python
# generative_art.py
import viewer_adapter_simple as VA
import random

def create_art():
    VA.reset()
    
    # Create random pattern
    for i in range(20):
        x = random.randint(0, 200)
        y = random.randint(0, 200)
        size = random.randint(5, 30)
        gray = random.randint(50, 255)
        
        VA.RECT(x, y, size, size, gray)
    
    VA.COMMIT()
```

## Advanced Features

### Source Mirroring
The workbench automatically mirrors your viewer's source code into Pane 1 for audit and version tracking.

### Bidirectional Editing
- Edit source in Pane 1 → updates CSV in Pane 3
- Edit CSV in Pane 3 → updates tiles and results
- Real-time feedback in all panes

### Tile Visualization
See your program as executable pixels - each tile encodes an operation with error correction.

### Hardware Simulation
Test your analog programs before deploying to real hardware.

## Next Steps

1. **Start with the smoke test** - run the workbench and click "Run with my Viewer"
2. **Adapt your viewer** - replace drawing calls with adapter calls
3. **Test with hardware** - use the hardware hooks for real analog devices
4. **Upgrade to ECC** - use Hamming encoding for robust field deployment
5. **Scale up** - create libraries of analog operations for your domain

## Support

This system provides a complete bridge between digital programming and analog execution. The "paste-and-go" design means you can start with any existing Python program and immediately see it running in the analog environment.

For more complex integrations or custom hardware, the modular design allows you to extend any component while maintaining compatibility with the rest of the system.

Your analog computer is ready to run! 🚀