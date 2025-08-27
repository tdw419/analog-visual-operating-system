# UVIR Hardware Bridge Setup Guide

This guide will help you set up the complete UVIR system with hardware control capabilities, enabling your LLM to control physical devices like LEDs through natural language commands.

## 🎯 What You'll Build

- **LLM-to-Hardware Pipeline**: "Set LED on pin 13 to value 128" → Physical LED dims to 50% brightness
- **Visual Feedback**: Real-time visualization of hardware commands and results
- **Safe Control**: Input validation and error handling to prevent hardware damage
- **Replay Capability**: Record and replay sessions for debugging and demonstration

## 🛠️ Hardware Requirements

### Basic Setup (Recommended)
- **Arduino Uno** (or compatible)
- **LED** (any color)
- **220Ω Resistor**
- **Breadboard**
- **Jumper wires**
- **USB cable** (for Arduino connection)

### Advanced Setup (Optional)
- Multiple LEDs for RGB control
- Servo motors for movement
- Sensors for feedback loops
- External power supply for high-power devices

## 🔧 Hardware Setup

### 1. Basic LED Circuit
```
Arduino Pin 13 → 220Ω Resistor → LED (Anode) → LED (Cathode) → Arduino GND
```

### 2. Multi-LED Setup (Optional)
```
Pin 3  → 220Ω → Red LED   → GND
Pin 5  → 220Ω → Green LED → GND  
Pin 6  → 220Ω → Blue LED  → GND
Pin 13 → 220Ω → White LED → GND
```

### 3. Arduino Programming
1. **Install Arduino IDE**: Download from [arduino.cc](https://www.arduino.cc/en/software)
2. **Upload Sketch**:
   - Open `arduino_pwm_control.ino` in Arduino IDE
   - Select your board: **Tools > Board > Arduino Uno**
   - Select your port: **Tools > Port > [your port]**
   - Click **Upload** (→ button)
3. **Test Connection**:
   - Open **Tools > Serial Monitor**
   - Set baud rate to **9600**
   - Type `PWM:13:255` and press Enter
   - LED should turn on, and you should see "OK"

## 💻 Software Setup

### 1. Install Dependencies
```bash
# Install Python packages
pip install -r requirements-uvir.txt

# Or install individually:
pip install fastapi uvicorn pydantic json-repair pyserial
# Optional: pip install llama-cpp-python  # for real LLM (requires GGUF model)
```

### 2. Configure Serial Port
```bash
# Linux/Mac
export SERIAL_PORT="/dev/ttyUSB0"  # or /dev/ttyACM0

# Windows
set SERIAL_PORT=COM3  # check Device Manager for correct port

# Optional: Use a real LLM
export MODEL_PATH="/path/to/llama-3.2-1b-instruct.gguf"
```

### 3. Start the System
```bash
# Terminal 1: Start UVIR server
python uvir_server.py

# Terminal 2: Serve the frontend  
python -m http.server 8080

# Open browser to http://localhost:8080/uvir_frontend.html
```

## 🚀 Testing the System

### 1. Basic Hardware Test
1. **Click "Test LED"** button in the web interface
2. **Expected result**: 
   - LED dims to 50% brightness
   - UI shows "✓ LED Test Success"
   - Log panel shows tool call and result

### 2. Natural Language Control
1. **Enter prompt**: "Set LED on pin 13 to value 200 and show confirmation"
2. **Click "Generate"**
3. **Expected result**:
   - LED brightens to ~78% brightness (200/255)
   - Canvas shows hardware command visualization
   - Confirmation message appears

### 3. Hardware Examples
Try these prompts:
```
"Turn on the LED at full brightness"
"Dim the LED to 25% brightness"  
"Set LED on pin 13 to value 128"
"Pulse the LED by setting it to 100, then 200, then 50"
```

## 🔍 Troubleshooting

### Serial Connection Issues
```bash
# Check available ports
python -c "import serial.tools.list_ports; print([p.device for p in serial.tools.list_ports.comports()])"

# Test manual connection
python -c "import serial; s=serial.Serial('/dev/ttyUSB0', 9600, timeout=1); s.write(b'PWM:13:255\\n'); print(s.readline())"
```

### Common Problems

| Problem | Solution |
|---------|----------|
| "Server Offline" | Check if `uvir_server.py` is running on port 8844 |
| "No Hardware" | Verify `SERIAL_PORT` environment variable and Arduino connection |
| LED not responding | Check wiring, resistor value, and Arduino sketch upload |
| Permission denied | Add user to dialout group: `sudo usermod -a -G dialout $USER` |

### Debug Mode
```bash
# Run server with debug output
UVIR_DEBUG=1 python uvir_server.py

# Check server logs for detailed error messages
```

## 🎨 Advanced Examples

### 1. RGB LED Control (3 LEDs)
```
"Create a rainbow effect by setting red LED to 255, green to 128, and blue to 64"
```

### 2. Breathing Effect
```
"Make the LED breathe by slowly cycling from 0 to 255 and back"
```

### 3. Data Visualization + Hardware
```
"Show quarterly sales as bars and light up LEDs: Q1=pin 3, Q2=pin 5, Q3=pin 6, Q4=pin 13"
```

## 🔧 Extending the System

### 1. Add New Hardware Tools
Edit `uvir_server.py` to add new tools:
```python
class ServoControlArgs(BaseModel):
    pin: int = Field(..., ge=0, le=13)
    angle: int = Field(..., ge=0, le=180)

TOOL_REGISTRY["servo_control"] = {
    "description": "Control servo motor angle",
    "schema": ServoControlArgs
}
```

### 2. Add Sensor Feedback
Extend Arduino sketch to read sensors and send data back:
```cpp
void handleSensorRead() {
    int sensorValue = analogRead(A0);
    Serial.print("SENSOR:");
    Serial.println(sensorValue);
}
```

### 3. Create Custom UVIR Operations
Add domain-specific operations for your hardware:
```python
def validate_hardware_ops(ops):
    # Add custom ops like LED_PULSE, SERVO_SWEEP, etc.
    pass
```

## 🎯 Next Steps

### Phase 4: Observability & Replay
- [ ] Implement session logging to NDJSON files
- [ ] Add replay endpoint for re-running sessions
- [ ] Create metrics dashboard (TTFP, commands/sec, error rates)

### Advanced Hardware Integration
- [ ] Multi-device coordination (multiple Arduinos)
- [ ] Sensor feedback loops (light sensors, temperature, etc.)
- [ ] Real-time hardware monitoring dashboard
- [ ] Safety interlocks and emergency stops

### LLM Optimization
- [ ] Grammar constraints for guaranteed valid UVIR output
- [ ] Fine-tuning for better hardware command generation
- [ ] Multi-modal input (voice commands, images)

## 📚 Resources

- **UVIR Specification**: Complete technical specification with schemas
- **Example Projects**: Algorithm visualization, data dashboards, IoT control
- **Community**: Share your hardware integrations and UVIR extensions

---

**🎉 Congratulations!** You now have a complete LLM-to-hardware control system. Your AI can perceive (through prompts), reason (via UVIR), and act (through hardware) in the physical world. This is the foundation of truly embodied AI systems.

**What will you build next?** 🚀