/*
 * UVIR Hardware Bridge - Arduino PWM Controller
 * Compatible with UVIR 1.0 Server serial_pwm tool
 * 
 * This sketch receives PWM commands via serial and controls LEDs/devices.
 * Command format: PWM:pin:value
 * Example: PWM:13:128 sets pin 13 to 50% brightness (128/255)
 * 
 * Hardware Setup:
 * - LED + 220Ω resistor on pin 13 (built-in LED works too)
 * - Connect Arduino to computer via USB
 * - Note the serial port (e.g., /dev/ttyUSB0 or COM3)
 * 
 * Compatible with: Arduino Uno, Nano, Mega, ESP32, ESP8266
 */

// Pin configuration
const int LED_PIN = 13;            // Main LED pin (built-in LED)
const int PWM_PINS[] = {3, 5, 6, 9, 10, 11, 13}; // Valid PWM pins
const int NUM_PWM_PINS = 7;
const int BAUD_RATE = 9600;

void setup() {
  // Initialize serial communication
  Serial.begin(BAUD_RATE);
  
  // Initialize PWM pins as outputs
  for (int i = 0; i < NUM_PWM_PINS; i++) {
    pinMode(PWM_PINS[i], OUTPUT);
    analogWrite(PWM_PINS[i], 0); // Start with all LEDs off
  }
  
  // Startup sequence - flash built-in LED to show ready
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(200);
    digitalWrite(LED_PIN, LOW);
    delay(200);
  }
  
  // Send ready signal
  Serial.println("UVIR Hardware Bridge Ready");
  Serial.flush();
}

void loop() {
  // Check for incoming serial commands
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim(); // Remove any whitespace
    
    // Process the command
    if (command.startsWith("PWM:")) {
      handlePWMCommand(command);
    } else if (command.startsWith("PING")) {
      Serial.println("PONG");
    } else if (command.startsWith("STATUS")) {
      sendStatus();
    } else if (command.startsWith("RESET")) {
      resetAllPins();
    } else if (command.length() > 0) {
      Serial.println("ERROR: Unknown command");
    }
    
    Serial.flush(); // Ensure response is sent immediately
  }
}

void handlePWMCommand(String command) {
  // Parse PWM:pin:value format
  int firstColon = command.indexOf(':');
  int secondColon = command.lastIndexOf(':');
  
  if (firstColon == -1 || secondColon == -1 || firstColon == secondColon) {
    Serial.println("ERROR: Invalid format. Use PWM:pin:value");
    return;
  }
  
  // Extract pin and value
  String pinStr = command.substring(firstColon + 1, secondColon);
  String valueStr = command.substring(secondColon + 1);
  
  int pin = pinStr.toInt();
  int value = valueStr.toInt();
  
  // Validate pin
  if (!isValidPWMPin(pin)) {
    Serial.println("ERROR: Invalid pin. Use pins 3,5,6,9,10,11,13");
    return;
  }
  
  // Validate value (0-255 for PWM)
  if (value < 0 || value > 255) {
    Serial.println("ERROR: Invalid value. Use 0-255");
    return;
  }
  
  // Execute PWM command
  analogWrite(pin, value);
  
  // Send success response
  Serial.println("OK");
  
  // Optional debug output (uncomment for debugging)
  // Serial.print("DEBUG: Pin ");
  // Serial.print(pin);
  // Serial.print(" set to ");
  // Serial.println(value);
}

bool isValidPWMPin(int pin) {
  // Check if pin is in the list of valid PWM pins
  for (int i = 0; i < NUM_PWM_PINS; i++) {
    if (PWM_PINS[i] == pin) {
      return true;
    }
  }
  return false;
}

void sendStatus() {
  Serial.println("UVIR Bridge Status:");
  Serial.print("- Valid PWM pins: ");
  for (int i = 0; i < NUM_PWM_PINS; i++) {
    Serial.print(PWM_PINS[i]);
    if (i < NUM_PWM_PINS - 1) Serial.print(",");
  }
  Serial.println();
  Serial.println("- Commands: PWM:pin:value, PING, STATUS, RESET");
  Serial.println("- Ready for UVIR control");
}

void resetAllPins() {
  // Turn off all PWM pins
  for (int i = 0; i < NUM_PWM_PINS; i++) {
    analogWrite(PWM_PINS[i], 0);
  }
  Serial.println("OK: All pins reset to 0");
}

// Optional: Advanced features for future expansion

void handleRGBCommand(String command) {
  // Future: Handle RGB:red:green:blue commands
  // For controlling RGB LEDs on pins 3,5,6 for example
}

void handleServoCommand(String command) {
  // Future: Handle SERVO:pin:angle commands
  // For controlling servo motors
}

void readSensors() {
  // Future: Read analog sensors and send data back to UVIR
  // Format: SENSOR:pin:value
}

/*
 * Example usage from UVIR server:
 * 
 * 1. Connect LED to pin 13 with 220Ω resistor
 * 2. Upload this sketch to Arduino
 * 3. Note the serial port (e.g., COM3 on Windows, /dev/ttyUSB0 on Linux)
 * 4. Set environment variable: export SERIAL_PORT="/dev/ttyUSB0"
 * 5. Start UVIR server: python uvir_server.py
 * 6. Open frontend and try: "Set LED on pin 13 to value 128"
 * 
 * Expected behavior:
 * - LED dims to 50% brightness (128/255)
 * - Serial monitor shows: OK
 * - UVIR frontend shows success message
 * 
 * Troubleshooting:
 * - Check serial port permissions: sudo usermod -a -G dialout $USER
 * - Verify Arduino is connected and sketch uploaded
 * - Test manually: Send "PWM:13:255" in Serial Monitor
 * - Check UVIR server logs for serial communication errors
 */