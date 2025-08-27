# PXOS Operations Schema (pxos-ops/1.0)

## Overview
The `pxos-ops/1.0` schema defines the High-Level Intermediate Representation (HLIR) for the PXOS 6-Pane Workbench, a hybrid computing platform for bidirectional digital-analog translation. All operations are validated against this schema to ensure semantic integrity.

## Schema Structure
The schema is based on JSON Schema Draft 2020-12 and defines a structured format for representing hybrid computing operations that can be translated between Python code, analog DSL, and hardware instructions.

## Core Operations

### RECT - Rectangle Drawing
Draws a rectangle at specified coordinates with RGB color values.

**Schema:**
```json
{
  "op": "RECT",
  "x": integer (0-∞),
  "y": integer (0-∞), 
  "w": integer (0-∞),
  "h": integer (0-∞),
  "r": integer (0-255),
  "g": integer (0-255),
  "b": integer (0-255)
}
```

**Python Example:**
```python
VA.RECT(20, 20, 40, 20, 64)  # Gray rectangle
VA.RECT(10, 10, 30, 30, 255, r=255, g=0, b=0)  # Red rectangle
```

**DSL Example:**
```
RECT(x=20,y=20,w=40,h=20,g=64)
RECT(x=10,y=10,w=30,h=30,r=255,g=0,b=0)
```

### COMMIT - State Commit
Commits the current state to hardware or display buffer.

**Schema:**
```json
{"op": "COMMIT"}
```

**Example:**
```python
VA.COMMIT()  # DSL: COMMIT()
```

### SLEEP - Execution Delay
Pauses execution for specified milliseconds.

**Schema:**
```json
{
  "op": "SLEEP",
  "ms": integer (0-∞)
}
```

**Example:**
```python
VA.SLEEP(100)  # DSL: SLEEP(ms=100)
```

### DAC_WRITE - Digital-to-Analog Output
Writes a value to a DAC (Digital-to-Analog Converter) channel.

**Schema:**
```json
{
  "op": "DAC_WRITE",
  "ch": integer (0-31),
  "val": integer (0-65535)
}
```

**Example:**
```python
VA.DAC_WRITE(1, 32768)  # DSL: DAC_WRITE(ch=1,val=32768)
```

### SYNC_ROW - Row Synchronization
Synchronizes processing at a specific row index.

**Schema:**
```json
{
  "op": "SYNC_ROW", 
  "i": integer (0-∞)
}
```

**Example:**
```python
VA.SYNC_ROW(5)  # DSL: SYNC_ROW(i=5)
```

## Extended Operations (Phase 2)

### INTEGRATE - Analog Integration
Performs integration with time constant tau from source to destination channel.

**Schema:**
```json
{
  "op": "INTEGRATE",
  "tau": number (>0),
  "src": integer,
  "dst": integer  
}
```

**Example:**
```python
VA.INTEGRATE(0.1, 0, 1)  # DSL: INTEGRATE(tau=0.1,src=0,dst=1)
```

### FILTER - Signal Filtering
Applies a filter (low-pass, high-pass, band-pass) with cutoff frequency.

**Schema:**
```json
{
  "op": "FILTER",
  "type": string,  # "lp", "hp", "bp", "notch"
  "fc": integer (0-∞),
  "src": integer,
  "dst": integer
}
```

**Example:**
```python
VA.FILTER("lp", 1000, 0, 1)  # DSL: FILTER(type="lp",fc=1000,src=0,dst=1)
```

### MULTIPLY - Signal Multiplication
Multiplies a source signal by a gain factor.

**Schema:**
```json
{
  "op": "MULTIPLY", 
  "gain": number,
  "src": integer,
  "dst": integer
}
```

**Example:**
```python
VA.MULTIPLY(2.5, 1, 2)  # DSL: MULTIPLY(gain=2.5,src=1,dst=2)
```

### SUM - Signal Summation
Sums multiple input signals to an output channel.

**Schema:**
```json
{
  "op": "SUM",
  "inputs": [integer, ...],  # Array of integers, min 1 item
  "output": integer
}
```

**Example:**
```python
VA.SUM([0, 1, 2], 3)  # DSL: SUM(inputs=[0,1,2],output=3)
```

## Complete Example

### Python Code:
```python
import viewer_adapter as VA

# Draw a rectangle
VA.RECT(50, 50, 100, 75, 128)

# Set up analog processing
VA.INTEGRATE(0.5, 0, 1)
VA.FILTER("lp", 500, 1, 2) 
VA.MULTIPLY(1.5, 2, 3)

# Output to DAC
VA.DAC_WRITE(0, 32768)

# Commit changes
VA.COMMIT()
```

### Equivalent HLIR:
```json
{
  "schemaVersion": "pxos-ops/1.0",
  "meta": {"profile": "default", "cols": 16},
  "program": [
    {"op": "RECT", "x": 50, "y": 50, "w": 100, "h": 75, "r": 128, "g": 128, "b": 128},
    {"op": "INTEGRATE", "tau": 0.5, "src": 0, "dst": 1},
    {"op": "FILTER", "type": "lp", "fc": 500, "src": 1, "dst": 2},
    {"op": "MULTIPLY", "gain": 1.5, "src": 2, "dst": 3},
    {"op": "DAC_WRITE", "ch": 0, "val": 32768},
    {"op": "COMMIT"}
  ]
}
```

### Equivalent DSL:
```
RECT(x=50,y=50,w=100,h=75,g=128)
INTEGRATE(tau=0.5,src=0,dst=1)
FILTER(type="lp",fc=500,src=1,dst=2)
MULTIPLY(gain=1.5,src=2,dst=3)
DAC_WRITE(ch=0,val=32768)
COMMIT()
```

## Schema Validation

The schema enforces:
- **Type safety**: All values must match expected types (integer, number, string, array)
- **Range validation**: Values like RGB components (0-255) and DAC channels (0-31) have defined limits
- **Required fields**: All operations must include their required parameters
- **Additional properties**: Set to `false` to prevent schema drift

## Implementation

```python
import jsonschema
from pxos_ops_schema import SCHEMA

def validate_hlir(hlir: dict) -> None:
    try:
        jsonschema.validate(hlir, SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValidationError(f"Schema validation failed: {e.message}")
```

## Version History

- **1.0**: Initial release with core operations (RECT, COMMIT, SLEEP, DAC_WRITE, SYNC_ROW)
- **1.1** (planned): Extended operations (INTEGRATE, FILTER, MULTIPLY, SUM)
- **2.0** (planned): Profile-specific constraints and advanced ECC operations

## Community Adoption

This schema is designed for:
- **Hardware interfacing**: Direct translation to analog computing hardware
- **Educational tools**: Visual programming for hybrid computing concepts  
- **Research platforms**: Rapid prototyping of analog-digital systems
- **Industrial automation**: Bridge between digital control and analog processes

The bidirectional nature ensures that programs can be authored in any representation (Python, DSL, or JSON) while maintaining semantic equivalence across all formats.