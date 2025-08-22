void setup() {
  Serial.begin(9600);
  pinMode(13, OUTPUT); // Built-in LED
  pinMode(9, OUTPUT);  // Example PWM pin
  // Initialize other PWM pins (3,5,6,9,10,11) if needed
  Serial.println("UVIR PWM Bridge Ready");
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command.startsWith("PWM:")) {
      int firstColon = command.indexOf(':');
      int secondColon = command.indexOf(':', firstColon + 1);

      if (firstColon != -1 && secondColon != -1) {
        int pin = command.substring(firstColon + 1, secondColon).toInt();
        int value = command.substring(secondColon + 1).toInt();

        // Safety clamp
        value = constrain(value, 0, 255);
        if (pin == 3 || pin == 5 || pin == 6 || pin == 9 || pin == 10 || pin == 11 || pin == 13) {
          analogWrite(pin, value);
          Serial.println("OK");
        } else {
          Serial.println("ERROR: Invalid PWM pin");
        }
      } else {
        Serial.println("ERROR: Invalid format. Use 'PWM:pin:value'");
      }
    }
  }
}
