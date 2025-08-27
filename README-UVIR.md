# UVIR 1.0 - Universal Visual Intermediate Representation

A revolutionary framework for streaming visual operations from Large Language Models in real-time, bypassing the sequential token bottleneck through parallel visual primitives.

## 🌟 What is UVIR?

UVIR transforms how LLMs communicate by moving from autoregressive text tokens to **structured visual primitives** that can be rendered in parallel. This enables:

- **Real-time visualization** of AI reasoning
- **Hardware control** through structured operations (NEW!)
- **Transparent AI** with entropy/confidence visualization
- **Interactive dashboards** generated from natural language
- **Physical world interaction** via serial PWM control

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements-uvir.txt
```

### 2. Run in Mock Mode (No LLM Required)

```bash
# Terminal 1: Start the server
python uvir_server.py

# Terminal 2: Open the frontend
python -m http.server 8080
# Open http://localhost:8080/uvir_frontend.html
```

### 3. Hardware Control (NEW!)

```bash
# Set up Arduino with LED on pin 13
# Upload arduino_pwm_control.ino sketch
export SERIAL_PORT="/dev/ttyUSB0"  # or COM3 on Windows
python uvir_server.py
```

Now try: **"Set LED on pin 13 to value 128"** → Physical LED dims to 50% brightness!

## 🎯 Core Features

### Visual Primitives
- **TICK**: Temporal markers for progress visualization
- **TEXT**: Rendered text with positioning and styling
- **BAR**: Progress bars with labels and values
- **RECT**: Rectangles and containers
- **LINK**: Connections with optional arrows

### Real-time Streaming
- Server-Sent Events (SSE) for live updates
- Token-by-token visualization of LLM thinking
- Parallel operation rendering while generating

### Safety & Validation
- JSON schema validation for all operations
- Input sanitization and bounds checking
- **Hardware safety** with pin/value validation and clamping
- Graceful error handling and recovery

## 📊 Example Use Cases

### Algorithm Visualization
```
Prompt: "Visualize bubble sort with array [5,3,8,1,4]"
Result: Live bars showing sorting steps with comparisons
```

### Data Dashboard
```
Prompt: "Create a sales dashboard with Q1-Q4 performance bars"
Result: Interactive bar chart with labels and values
```

### Hardware Visualization
```
Prompt: "Set LED on pin 13 to value 200 and show confirmation"
Result: Physical LED brightens + visual confirmation on canvas
```

## 🏗️ Architecture

```
LLM → UVIR Operations → SSE Stream → Canvas Renderer → Visual Output
                     → Tool Calls → Hardware/API Integration
```

### Backend (FastAPI)
- LLM integration via llama-cpp-python
- Streaming endpoint with validation
- Tool registry for hardware control
- Error handling and recovery

### Frontend (HTML5/Canvas)
- Real-time operation rendering
- Performance metrics and logging
- Interactive controls and examples
- Export capabilities

## 🔧 API Endpoints

- `GET /health` - Server health check
- `POST /stream` - Stream UVIR events from LLM
- `POST /runs/{id}/abort` - Abort running generation
- `POST /tools/execute` - Execute tool calls

## 🎨 UVIR Operation Examples

### Text Rendering
```json
{
  "op": "TEXT",
  "x": 100,
  "y": 50,
  "text": "Hello UVIR",
  "color": "#00FF00",
  "size": 16
}
```

### Progress Bar
```json
{
  "op": "BAR",
  "x": 50,
  "y": 100,
  "len": 200,
  "label": "Progress",
  "value": 0.75,
  "color": "#00AA00"
}
```

### Connected Flow
```json
[
  {"op": "RECT", "x": 100, "y": 100, "w": 120, "h": 60, "color": "#00FFFF"},
  {"op": "TEXT", "x": 110, "y": 120, "text": "Start"},
  {"op": "LINK", "x1": 160, "y1": 160, "x2": 160, "y2": 200, "arrow": true}
]
```

## 🎯 Hardware Integration (NEW!)

UVIR now includes direct hardware control capabilities:

### Arduino Setup
1. **Upload sketch**: `arduino_pwm_control.ino` to your Arduino
2. **Connect LED**: Pin 13 → 220Ω resistor → LED → GND  
3. **Set serial port**: `export SERIAL_PORT="/dev/ttyUSB0"`
4. **Test**: Click "Test LED" button or use natural language

### Natural Language Hardware Control
```
"Set LED on pin 13 to value 255"     → LED turns on full brightness
"Dim the LED to 25% brightness"       → LED dims to 64/255
"Turn off all LEDs"                   → All LEDs turn off
```

### Hardware Safety Features
- **Pin validation**: Only PWM-capable pins (3,5,6,9,10,11,13)
- **Value clamping**: PWM values constrained to 0-255 range
- **Error handling**: Graceful degradation if hardware unavailable
- **Simulation mode**: Works without physical Arduino for development

See [`HARDWARE_SETUP.md`](HARDWARE_SETUP.md) for complete setup guide.

## 📈 Performance Metrics

The system tracks key performance indicators:
- **TTFP** (Time to First Payload): Latency to first visual update
- **Tokens/Second**: LLM generation speed
- **Operations/Second**: Visual rendering throughput
- **Error Rate**: JSON repair and validation statistics

## 🛠️ Development Roadmap

### Phase 1: ✅ Walking Skeleton
- [x] Basic token streaming
- [x] Core visual primitives
- [x] Canvas renderer
- [x] Mock mode for testing

### Phase 2: 🚧 Contract Hardening
- [ ] JSON schema enforcement
- [ ] Error recovery mechanisms
- [ ] Performance optimization
- [ ] Batch operation processing

### Phase 3: ✅ Tool Integration
- [x] Hardware control (serial PWM)
- [x] Safe tool execution with validation
- [x] Tool registry architecture
- [x] Arduino integration example

### Phase 4: 📊 Observability
- [ ] Session replay system
- [ ] Metrics dashboard
- [ ] Performance profiling
- [ ] Debug visualizations

## 🤝 Contributing

This is the future of human-AI interaction! Contributions welcome:

1. **Core UVIR**: New visual primitives and operations
2. **Renderers**: Platform-specific rendering backends
3. **Tools**: Hardware and API integration modules
4. **Applications**: Domain-specific UVIR implementations

## 📄 License

MIT License - Feel free to use UVIR in your projects!

## 🙏 Acknowledgments

Inspired by the need to break free from sequential token generation and enable true real-time AI visualization. Special thanks to the PXOS project for pioneering visual computing paradigms.

---

**UVIR 1.0** - Transforming AI output from linear text to parallel visual operations, one pixel at a time. 🚀