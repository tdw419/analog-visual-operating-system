# PXOS 6-Pane Workbench: Round-Trip Digital-Analog Translator

## Overview

The PXOS 6-Pane Workbench is a revolutionary hybrid computing interface that transforms traditional one-way compilation into **bidirectional, round-trip translation** between digital source code and analog representations. This system embodies the "pixels as program" philosophy by making analog representations first-class, editable artifacts.

## Key Features

### 🔄 **Bidirectional Translation**
- **Round-trip engineering**: Edit in any pane, watch others update automatically
- **Semantic preservation**: Maintains program intent across transformations
- **Real-time synchronization**: 200ms debounced updates prevent lag

### 🛡️ **Bulletproof Data Flow**
- **Single source of truth**: One pane is "current truth" per edit cycle
- **Build ID tracking**: Prevents echo loops and circular updates
- **Validation layers**: Schema validation at every transformation step
- **Conflict resolution**: Last-writer-wins with optional pane pinning

### 📐 **PXOS Schema Compliance**
- **Formal specification**: Implements `pxos-ops/1.0` JSON Schema
- **Extensible operations**: RECT, SLEEP, DAC_WRITE, FILTER, INTEGRATE
- **Hardware abstraction**: Ready for real DAC/ADC integration
- **ECC support**: Hamming(16,12) and parity error correction

## Architecture

### The 6-Pane Layout

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Pane 1    │  │   Pane 2    │  │   Pane 3    │
│ Python      │  │ Analog      │  │ Analog      │
│ Source      │  │ Text Mirror │  │ Editor      │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
       ┌────────────────┼────────────────┐
       │                │                │
┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐
│   Pane 4    │  │   Pane 5    │  │   Pane 6    │
│ Tile Sheet  │  │ HLIR CSV    │  │ Live Replay │
└─────────────┘  └─────────────┘  └─────────────┘
```

#### Pane Functions

| Pane | Type | Function | Editable |
|------|------|----------|----------|
| **P1** | Text | Python source code | ✅ |
| **P2** | Text | Human-readable analog DSL | ✅ |
| **P3** | Text | Syntax-aware analog editor | ✅ |
| **P4** | Visual | Tile sheet with ECC encoding | ❌ |
| **P5** | Text | Schema-validated HLIR CSV/JSON | ✅ |
| **P6** | Visual | Live execution replay | ❌ |

### Data Flow Architecture

```
Truth Selection → Validation → Transformation → Propagation
     ↑                                            ↓
Build ID ←──────────── Event Bus ──────────→ Update Panes
```

#### Transform Chain Examples

**Origin P1 (Python):**
1. Parse Python AST → Extract ViewerAdapter calls
2. Convert to HLIR CSV → Validate schema
3. Generate analog DSL → Update P2/P3
4. Lower to LLIR → Encode tiles → Update P4/P6

**Origin P3 (Analog Editor):**
1. Parse analog DSL → Validate syntax
2. Convert to HLIR → Validate schema
3. Reverse-engineer Python → Update P1
4. Update mirror P2 → Lower/encode → Update P4/P6

## Installation & Setup

### Prerequisites
- Python 3.8+
- tkinter (usually included)
- Pillow: `pip install pillow`

### Quick Start

1. **Clone/download** the PXOS workbench files:
   - `pxos_workbench_6pane.py`
   - `pxos_bus.py`
   - `pxos_validator.py`

2. **Run the demo:**
   ```bash
   python demo_6pane_workbench.py
   ```

3. **Or run workbench directly:**
   ```bash
   python pxos_workbench_6pane.py
   ```

### Environment Configuration

Set environment variables to customize viewer integration:
```bash
export ACW_VIEWER_MODULE="your_viewer_main"
export ACW_VIEWER_FUNC="main"
```

## Usage Guide

### Basic Workflow

1. **Start the workbench**
2. **Click "Run Viewer"** to load a program via ViewerAdapter
3. **Edit any pane** to see live updates across all views
4. **Use pin buttons** (📌) to lock panes from auto-updates
5. **Watch P4 and P6** for visual feedback

### Example Programs

#### Simple Rectangle Program
```python
# P1 (Python)
import viewer_adapter_simple as VA
VA.RECT(20, 20, 40, 20, 128)
VA.SLEEP(30)
VA.COMMIT()
```

```
# P2/P3 (Analog DSL)
draw_rectangle(20, 20, 40, 20)
  ├─ color: rgb(128, 128, 128)
wait(30ms)
commit_frame()
```

```csv
# P5 (HLIR CSV)
RECT,20,20,40,20,128,128,128
SLEEP,30
COMMIT
```

#### Advanced Analog Operations
```
# P3 (Analog Editor)
analog_integrator(τ=0.1ms)
  ├─ input: channel_0
  └─ output: channel_1
analog_filter(lowpass, 1000Hz)
  ├─ input: channel_1
  └─ output: channel_2
analog_output(channel_2, 2.5V)
```

### Pane-Specific Features

#### P1 (Python Source)
- **Syntax highlighting** for Python keywords
- **ViewerAdapter integration** for program capture
- **AST parsing** for semantic analysis

#### P2 (Analog Mirror)
- **Normalized representation** of analog operations
- **Auto-generated** from P1 or P5 edits
- **Directly editable** with syntax validation

#### P3 (Analog Editor)
- **Syntax highlighting** for analog DSL
- **Real-time validation** with error highlighting
- **Advanced operations** support (FILTER, INTEGRATE)

#### P4 (Tile Sheet)
- **Visual tile encoding** with Hamming ECC
- **Grid layout** with fiducial markers
- **ECC statistics** display (OK/corrected/bad tiles)

#### P5 (HLIR CSV/JSON)
- **Schema validation** against pxos-ops/1.0
- **Direct CSV editing** for precise control
- **JSON Schema** error reporting

#### P6 (Live Replay)
- **Real-time visualization** of program execution
- **Waveform display** for analog operations
- **Hardware simulation** feedback

## Technical Details

### Validation Layers

| Layer | Scope | Validation Type |
|-------|-------|----------------|
| **Python AST** | P1 | Syntax validation |
| **Analog DSL** | P2/P3 | Grammar parsing |
| **JSON Schema** | P5 | pxos-ops/1.0 compliance |
| **ECC** | P4 | Tile integrity |
| **Semantic** | All | Range/type checking |

### Event Bus Architecture

```python
class PXOSBus:
    def on_edit(self, pane_type, content, metadata=None):
        # 1. Debounce (200ms)
        # 2. Assign build_id
        # 3. Set truth_origin
        # 4. Validate content
        # 5. Transform to canonical HLIR
        # 6. Propagate to other panes
        # 7. Update visuals (P4/P6)
```

### Error Handling

- **Validation failures** halt propagation, preserve last good state
- **Syntax errors** highlighted in originating pane
- **Schema violations** reported with specific field errors
- **Transform failures** logged with detailed error messages

### Performance Features

- **Incremental updates** with content hashing
- **Debounced events** prevent UI lag
- **Caching layers** for expensive operations
- **Asynchronous transforms** keep UI responsive

## Advanced Features

### Hardware Integration

The workbench supports hardware abstraction for:
- **DAC outputs** (0-5V, 8 channels)
- **ADC inputs** with simulation
- **PWM control** for servo/motor applications
- **Serial interfaces** for Arduino/microcontroller

### Extensibility

#### Custom Operations
Add new operations to the schema:
```json
{
  "op": "CUSTOM_OP",
  "param1": {"type": "integer"},
  "param2": {"type": "string"}
}
```

#### Device Profiles
```json
{
  "profile": "high_precision",
  "dac_range": [-10.0, 10.0],
  "tile_encoding": "hamming",
  "max_channels": 16
}
```

### Camera Integration

Future support for optical program loading:
- **Fiducial detection** for tile alignment
- **Error correction** for damaged tiles
- **Real-time decode** from camera input

## Troubleshooting

### Common Issues

1. **"Import error: No module named 'pxos_bus'"**
   - Ensure all files are in the same directory
   - Check Python path includes current directory

2. **"Validation failed: Schema error"**
   - Check CSV format matches pxos-ops/1.0 spec
   - Verify all required fields are present

3. **"Pane updates not working"**
   - Check if pane is pinned (📌 button)
   - Verify edit events are triggering (check status bar)

4. **"Viewer integration failed"**
   - Ensure viewer_adapter_simple.py exists
   - Check environment variables ACW_VIEWER_MODULE/FUNC

### Debug Mode

Enable debug output:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Development

### Contributing

1. **Fork** the repository
2. **Create** feature branch: `git checkout -b feature-name`
3. **Add tests** for new functionality
4. **Submit** pull request with detailed description

### Testing

Run the test suite:
```bash
python -m pytest test_pxos_workbench.py
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints where possible
- Document all public methods
- Include docstrings for classes

## License

This project is part of the PXOS ecosystem and follows the same licensing terms.

## Acknowledgments

- **Hybrid Computing Research** for architectural inspiration
- **Round-Trip Engineering** principles from software engineering
- **Event-Driven Architecture** patterns from modern web development
- **Error Correction Codes** from digital communications theory

---

**PXOS 6-Pane Workbench** - Where pixels become programs, and programs become pixels. 🎨⚡