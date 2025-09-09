# Assistive Robotics-as-a-Service (ARaaS) Platform

![Project Banner](assets/banner.png)  

**A mobile, AI-powered assistive robotic arm platform designed for elderly care, combining robotics, software, and AI for enhanced independence and safety.**

---

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Hardware Stack](#hardware-stack)
- [Software Stack](#software-stack)
- [3D Models](#3d-models)
- [Installation & Setup](#installation--setup)
- [Usage](#usage)
- [Future Scope](#future-scope)
- [License](#license)

---

## Overview
ARaaS is a mobile assistive robotic arm system with a **personalized AI companion** for elderly care. It supports **multi-modal control** (manual, app-based, voice commands, and scheduled tasks) and offers real-time feedback via live camera feeds and sensor data. The platform emphasizes **independence, safety, and user-friendliness**.

---

## Features

- **Manual Control:** Keyboard, mouse, or joystick for immediate operation  
- **Dashboard / App:**  
  - Live camera feed (`LiveFeed.jsx`)  
  - Controls panel (`Controls.jsx`)  
  - Task Scheduler (`TaskScheduler.jsx`)  
  - Object interaction & path tracing (`ObjectInteraction.jsx`, `PathTracing.jsx`)  
  - Emergency alerts (`EmergencyAlerts.jsx`)  
  - Caregiver monitoring panel (`CaregiverPanel.jsx`)  
  - Large action button interface (`BigButton.jsx`)  
- **Voice Control:** TTS/STT support via AI companion  
- **Custom 3D-Printed Design:** Tested through trial-and-error for optimal movement  
- **Open-Source:** All model and code files are released for public use

---

## Hardware Stack

| Component | Description |
|-----------|-------------|
| **Raspberry Pi** | Master controller with WiFi, 480p camera, ultrasonic sensors, TTS/STT support |
| **Arduino** | Slave controller to drive actuators (motors, servos, LEDs) based on RPi commands |
| **DC Motors & Wheels** | Mobile vehicle base |
| **Servo Motors** | Robotic arm movement |
| **Ultrasonic Sensors** | Obstacle detection & distance measurement |
| **Power Supply** | Battery pack for all electronics |
| **Optional Accessories** | Touch buttons, LEDs, microphones, etc. |

---

## Software Stack

| Layer / Tool | Purpose |
|--------------|---------|
| **Arduino IDE** | Servo, motor, and sensor control |
| **Python** | High-level control, AI companion logic, camera streaming |
| **React / JSX Modules** | Frontend dashboard components: `Dashboard.jsx`, `Controls.jsx`, etc. |
| **Communication Protocol** | WiFi / Serial between RPi and Arduino |
| **AI Companion** | Personalized voice interaction (TTS/STT) for elderly assistance |

---

## 3D Models

- All **robotic arm and vehicle models** are custom-designed and 3D-printed  
- Trial-and-error testing ensures **optimized movement and reliability**  
- **Available in `/3D-Models` folder**  
- Open-source: Anyone can download, modify, and build their own version

---

## Installation & Setup

### Hardware Setup
1. Assemble the mobile robotic arm on the vehicle base using 3D-printed components.  
2. Connect servos, motors, and sensors to Arduino.  
3. Connect Arduino to Raspberry Pi via USB/Serial.  
4. Connect battery supply.

### Software Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/ARaaS.git
cd ARaaS

# Install Python dependencies
pip install -r requirements.txt

# Start backend services
python main.py

# Start frontend dashboard
npm install
npm start
