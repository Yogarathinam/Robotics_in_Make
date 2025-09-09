#include <Servo.h>

// --- Servos ---
Servo panServo;
Servo tiltServo;
Servo gripServo;

// --- L298N motor pins ---
#define IN1 8
#define IN2 9
#define IN3 10
#define IN4 11

// --- Ultrasonic pins ---
#define TRIG_PIN A1
#define ECHO_PIN A2

// --- Servo pins ---
#define PAN_PIN 3
#define TILT_PIN 5
#define GRIP_PIN 6   // gripper servo

// --- Variables ---
String inputString = "";
bool stringComplete = false;

void setup() {
  Serial.begin(9600);

  // Attach servos
  panServo.attach(PAN_PIN);
  tiltServo.attach(TILT_PIN);
  gripServo.attach(GRIP_PIN);

  // Init servo positions
  panServo.write(90);
  tiltServo.write(90);
  gripServo.write(90);

  // Motor pins
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  stopMotors();

  // Ultrasonic
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
}

void loop() {
  if (stringComplete) {
    processCommand(inputString);
    inputString = "";
    stringComplete = false;
  }

  // Send distance every 300ms
  static unsigned long lastSend = 0;
  if (millis() - lastSend > 300) {
    long distance = getDistance();
    Serial.println(distance);
    lastSend = millis();
  }
}

void processCommand(String cmd) {
  cmd.trim();

  // Motor commands
  if (cmd == "F") forward();
  else if (cmd == "B") backward();
  else if (cmd == "L") left();
  else if (cmd == "R") right();
  else if (cmd == "S") stopMotors();

  // Servo commands
  else if (cmd.startsWith("P")) {   // Pan
    int val = cmd.substring(1).toInt();
    panServo.write(constrain(val, 0, 180));
  }
  else if (cmd.startsWith("T")) {   // Tilt
    int val = cmd.substring(1).toInt();
    tiltServo.write(constrain(val, 0, 180));
  }
  else if (cmd.startsWith("G")) {   // Gripper
    int val = cmd.substring(1).toInt();
    gripServo.write(constrain(val, 0, 180));
  }
}

void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      stringComplete = true;
    } else {
      inputString += inChar;
    }
  }
}

// --- Motor functions ---
void forward() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}

void backward() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

void left() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}

void right() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

void stopMotors() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}

// --- Ultrasonic function ---
long getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 20000); // 20ms timeout
  long distance = duration * 0.034 / 2;
  return distance == 0 ? -1 : distance; // -1 if no echo
}
