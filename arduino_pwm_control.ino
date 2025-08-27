/*
 * UVIR Hardware Bridge - Arduino PWM Controller
 * 
 * This sketch enables the UVIR system to control LEDs and other PWM devices
 * via serial communication. It listens for commands in the format:
 * PWM:pin:value
 * 
 * Example: PWM:13:128 sets pin 13 to 50% brightness (128/255)
 * 
 * Hardware Setup:
 * - Connect an LED with 220Ω resistor to pin 13
 * - Connect Arduino to computer via USB
 * - Set Serial Port in environment variable (e.g., /dev/ttyUSB0 or COM3)
 */

void setup() {
  Serial.begin(9600);
  
  // Initialize LED pin
  pinMode(13, OUTPUT);
  
  // Optional: Initialize other PWM pins
  pinMode(3, OUTPUT);
  pinMode(5, OUTPUT);
  pinMode(6, OUTPUT);
  pinMode(9, OUTPUT);
  pinMode(10, OUTPUT);
  pinMode(11, OUTPUT);
  
  // Startup sequence - flash LED to show ready
  for (int i = 0; i < 3; i++) {
    digitalWrite(13, HIGH);
    delay(200);
    digitalWrite(13, LOW);
    delay(200);
  }
  
  Serial.println("UVIR Hardware Bridge Ready");
}

void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim(); // Remove whitespace
    
    if (command.startsWith("PWM:")) {
      handlePWMCommand(command);
    } else if (command.startsWith("PING")) {
      Serial.println("PONG");
    } else if (command.startsWith("STATUS")) {
      Serial.println("READY");
    } else {
      Serial.println("ERROR: Unknown command");
    }
  }
}

void handlePWMCommand(String command) {
  // Parse PWM:pin:value format
  int firstColon = command.indexOf(':');
  int secondColon = command.lastIndexOf(':');
  
  if (firstColon == -1 || secondColon == -1 || firstColon == secondColon) {
    Serial.println("ERROR: Invalid PWM format. Use PWM:pin:value");
    return;
  }
  
  String pinStr = command.substring(firstColon + 1, secondColon);
  String valueStr = command.substring(secondColon + 1);
  
  int pin = pinStr.toInt();
  int value = valueStr.toInt();
  
  // Validate pin (only allow PWM-capable pins)
  if (!isPWMPin(pin)) {
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
  
  // Send confirmation
  Serial.println("OK");
  
  // Optional: Debug output
  // Serial.print("DEBUG: Set pin ");
  // Serial.print(pin);
  // Serial.print(" to ");
  // Serial.println(value);
}

bool isPWMPin(int pin) {
  // Arduino Uno PWM pins: 3, 5, 6, 9, 10, 11
  // Pin 13 is also allowed for basic LED control
  return (pin == 3 || pin == 5 || pin == 6 || pin == 9 || 
          pin == 10 || pin == 11 || pin == 13);
}

// Optional: Add more command handlers
void handleStatusCommand() {
  Serial.println("UVIR Bridge Status:");
  Serial.println("- PWM pins: 3,5,6,9,10,11,13");
  Serial.println("- Commands: PWM:pin:value, PING, STATUS");
  Serial.println("- Ready for AI control");
}