# Smart Bus Assistance System
## Complete Technical Documentation & Report

**Version:** 1.0  
**Date:** May 28, 2026  
**Author:** Smart Bus Team  

---

# Executive Summary

The Smart Bus Assistance System is an IoT-based solution designed to help hearing-impaired passengers identify and recognize arriving buses at public transit stops. The system consists of two Raspberry Pi units working in coordination: a **Stop Pi** with a touchscreen interface for requesting assistance, and a **Bus Pi** installed on the bus that displays information and announces bus lines through audio.

The system enables deaf or hard-of-hearing passengers to independently identify which bus is approaching by providing both visual (LCD display) and audio (multi-language announcements) feedback.

---

# System Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SMART BUS ASSISTANCE SYSTEM                        │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌─────────────────────────────┐         MQTT          ┌─────────────────────────────┐
     │         STOP PI              │  (bus-assistance/)   │        BUS PI              │
     │     (10.39.44.121)          │ ─────────────────────► │     (10.39.44.151)         │
     │                              │                      │                            │
     │  ┌────────────────────────┐  │                      │  ┌────────────────────────┐  │
     │  │   7" Touchscreen       │  │                      │  │   LCD 16x2 Display    │  │
     │  │   (800x480 resolution) │  │                      │  │   • Line 0: 16 chars  │  │
     │  │                        │  │                      │  │   • Line 1: 16 chars  │  │
     │  │   Bus Line Buttons:    │  │                      │  └────────────────────────┘  │
     │  │   [15] [68] [42] [33] │  │                      │                            │
     │  │                        │  │                      │  ┌────────────────────────┐  │
     │  │   [CANCEL] button     │  │                      │  │   USB Speaker          │  │
     │  │                        │  │                      │  │   • Italian audio      │  │
     │  │   Weather display     │  │                      │  │   • English audio     │  │
     │  └────────────────────────┘  │                      │  └────────────────────────┘  │
     │                              │                      │                            │
     │  ┌────────────────────────┐  │                      │  ┌────────────────────────┐  │
     │  │   Mosquitto Broker     │  │                      │  │   RGB Backlight        │  │
     │  │   Port: 1883           │  │                      │  │   • Yellow (idle)      │  │
     │  └────────────────────────┘  │                      │  │   • Red (active)       │  │
     │                              │                      │  └────────────────────────┘  │
     └─────────────────────────────┘                      └─────────────────────────────┘
                                                                            │
                                                                            ▼
                                                            ┌─────────────────────────────┐
                                                            │      Bus Vehicle            │
                                                            │   (Raspberry Pi 3 B+)       │
                                                            └─────────────────────────────┘
```

---

## Component Specifications

### Stop Pi (Control Unit)

| Specification | Details |
|--------------|---------|
| **IP Address** | 10.39.44.121 |
| **Hardware** | Raspberry Pi 3 B+ or later |
| **Display** | 7" Official Raspberry Pi Touchscreen (800x480) |
| **Software** | Python 3, Tkinter, paho-mqtt |
| **MQTT Broker** | Mosquitto |
| **Bus Lines** | 15, 68, 42, 33 |
| **Stop Name** | Piazza Castello (#462) |

### Bus Pi (Display Unit)

| Specification | Details |
|--------------|---------|
| **IP Address** | 10.39.44.151 |
| **Hardware** | Raspberry Pi 3 B+ |
| **LCD Display** | 16x2 Character LCD with I2C Backpack |
| **LCD Address** | 0x3E (Hex) |
| **RGB Controller** | 0x62 (Hex) |
| **Audio Output** | USB Speaker (plughw:1,0) |
| **Audio Format** | WAV files, 24kHz, Mono |
| **Power** | Bus 12V/24V → USB 5V adapter |

---

# Hardware Configuration

## Stop Pi Hardware

### 7" Touchscreen Display
- **Resolution:** 800 x 480 pixels
- **Interface:** DSI (Display Serial Interface)
- **Touch:** 5-point capacitive touch
- **Mounting:** Official Raspberry Pi case

### GPIO Configuration
- Display connected via DSI ribbon cable
- No additional GPIO usage required

## Bus Pi Hardware

### LCD 16x2 Display with I2C Backpack

```
┌────────────────────────────────────────────────────┐
│  LCD Pin    │  I2C Backpack  │  Function          │
├─────────────┼─────────────────┼────────────────────┤
│  VSS        │  GND            │  Ground            │
│  VDD        │  VCC            │  5V Power          │
│  SDA        │  SDA            │  I2C Data          │
│  SCL        │  SCL            │  I2C Clock         │
└────────────────────────────────────────────────────┘
```

**I2C Addresses:**
- LCD Controller: 0x3E
- RGB Backlight: 0x62

### USB Audio Speaker
- **Card Number:** 1
- **Device Number:** 0
- **ALSA Device:** plughw:1,0

### Power Requirements
- **Input:** 12V-24V DC (from bus)
- **Output:** 5V USB-C (to Pi)
- **Current:** 3A minimum

---

# Software Architecture

## Stop Pi Software

### Application Stack

```
┌─────────────────────────────────────┐
│     Tkinter GUI (app.py)            │
│  • Touch button handlers            │
│  • MQTT message publishing          │
│  • Weather display widget          │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│     paho-mqtt (Publisher)           │
│  • Connects to local broker        │
│  • Publishes request messages      │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│     Mosquitto Broker (Local)        │
│  • Port: 1883                      │
│  • Topics: bus-assistance/*        │
└─────────────────────────────────────┘
```

### MQTT Topics

| Topic | Direction | Payload Example |
|-------|-----------|-----------------|
| `bus-assistance/{line}/request` | Stop → Bus | "STOP 462 -- Piazza Castello -- LINE 15" |
| `bus-assistance/{line}/cancelled` | Stop → Bus | "CANCELLED" |
| `bus-assistance/{line}/accepted` | Bus → Stop | (Future use) |

### Weather Integration
- **API:** Open-Meteo (free, no API key)
- **Update Interval:** 10 minutes
- **Data:** Temperature, Weather conditions
- **Location:** Configurable via config.py

## Bus Pi Software

### Application Stack

```
┌─────────────────────────────────────┐
│     bus_display.py (Main App)       │
│  • MQTT subscription               │
│  • LCD display control             │
│  • Audio playback                  │
│  • Timer management                 │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│     paho-mqtt (Subscriber)         │
│  • Subscribes to request topics    │
│  • Handles message callbacks       │
└─────────────────┬───────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌───────────────┐   ┌───────────────┐
│  smbus2       │   │  subprocess   │
│  (I2C LCD)    │   │  (Audio)      │
└───────────────┘   └───────────────┘
```

### Key Functions

```python
# LCD Functions
init_lcd()        # Initialize LCD display
clear_lcd()       # Clear screen
set_pos(col, row) # Set cursor position
write_text(text)  # Write text to LCD
make_heart()      # Create heart character
set_color(r,g,b)  # Set RGB backlight

# Display Screens
show_idle()       # Show idle screen (yellow)
show_request()    # Show request screen (red)

# Audio Functions
play_audio(line)  # Play line announcement

# Timer Functions
start_timer()     # Start 30-second countdown
cancel_timer()    # Cancel active timer
```

---

# Display Screens

## Idle Screen (Default State)

```
┌────────────────────────────────┐
│ Line 0: Smart Stop Ready       │
│ Line 1: Yellow team ♥          │
└────────────────────────────────┘
         ▲
         │
    Yellow backlight
```

**RGB Values:** (255, 255, 0) - Yellow

## Request Screen (Active State)

```
┌────────────────────────────────┐
│ Line 0: Piazza Castello        │
│ Line 1: Linea 15               │
└────────────────────────────────┘
         ▲
         │
    Red backlight
```

**RGB Values:** (255, 0, 0) - Red

---

# Communication Protocol

## MQTT Message Flow

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│  Stop    │         │  MQTT    │         │   Bus    │
│   Pi     │         │  Broker  │         │    Pi    │
└────┬─────┘         └────┬─────┘         └────┬─────┘
     │                    │                    │
     │  publish()         │                    │
     │──────────────────► │                    │
     │  (request topic)   │                    │
     │                    │ subscribe()         │
     │                    │◄───────────────────│
     │                    │                    │
     │                    │  on_message()      │
     │                    │───────────────────►│
     │                    │                    │
```

## Message Sequence

1. **User touches bus line button on Stop Pi**
   ```
   Topic: bus-assistance/15/request
   Payload: "STOP 462 -- Piazza Castello -- LINE 15"
   ```

2. **Bus Pi receives message**
   - Parse line number
   - Cancel any active timer
   - Stop any playing audio
   - Update LCD to request screen
   - Start audio announcement

3. **Audio Announcement Plays**
   - Italian: "it_line_15.wav"
   - English: "en_line_15.wav" (after 0.3s delay)

4. **Timer Starts (30 seconds)**
   - Countdown displayed in console
   - After expiration, return to idle screen

5. **User presses Cancel (optional)**
   ```
   Topic: bus-assistance/15/cancelled
   Payload: "CANCELLED"
   ```
   - Immediate return to idle screen

---

# File Structure

## Stop Pi Files

```
/home/s4mpie/bus-assistance/
├── config.py                    # Configuration settings
│   ├── BROKER_HOST             # "10.39.44.121"
│   ├── BROKER_PORT             # 1883
│   ├── TOPIC_PREFIX            # "bus-assistance"
│   ├── BUS_LINES               # ["15", "68", "42", "33"]
│   ├── REQUEST_TIMEOUT_SEC     # 30
│   └── HAPTIC_PIN              # 12 (BCM GPIO)
│
├── bus_stop/
│   └── app.py                  # Main GUI application
│       ├── Tkinter window      # 800x480 fullscreen
│       ├── Bus line buttons    # Grid layout
│       ├── Cancel button       # Reset function
│       └── Weather widget      # API integration
│
└── run_bus_pi.sh               # Start script
```

## Bus Pi Files

```
/home/s4mpie2/smartbus/
├── bus_display.py               # Main application
│   ├── LCD Functions            # I2C communication
│   ├── Audio Functions          # aplay subprocess
│   ├── MQTT Client             # Subscription handler
│   └── Timer Management         # Threading timer
│
├── audio/                       # Announcement files
│   ├── it_line_15.wav          # Italian "Linea 15"
│   ├── en_line_15.wav          # English "Line 15"
│   ├── it_line_68.wav          # Italian "Linea 68"
│   ├── en_line_68.wav          # English "Line 68"
│   ├── it_line_42.wav          # Italian "Linea 42"
│   ├── en_line_42.wav          # English "Line 42"
│   ├── it_line_33.wav          # Italian "Linea 33"
│   └── en_line_33.wav          # English "Line 33"
│
└── bus_log.txt                 # Runtime log file
```

---

# Installation & Setup

## Stop Pi Setup

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip mosquitto mosquitto-clients

# Install Python packages
pip3 install paho-mqtt

# Copy application files
cp -r bus-assistance /home/s4mpie/

# Start mosquitto broker
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

# Configure autostart
# (Add to ~/.config/autostart/ or use systemd)
```

## Bus Pi Setup

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip i2c-tools alsa-utils

# Enable I2C
sudo raspi-config
# Navigate: Interface Options → I2C → Enable → Finish

# Install Python packages
pip3 install paho-mqtt smbus2

# Copy application files
cp -r smartbus /home/s4mpie2/

# Set up autostart (crontab)
crontab -e
# Add: @reboot sleep 15 && cd /home/s4mpie2/smartbus && python3 bus_display.py
```

## LCD I2C Configuration

```bash
# Check I2C devices
sudo i2cdetect -y 1

# Expected output:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:                         -- -- -- -- -- -- -- -- -- -- -- -- --
# 10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 30: -- -- -- -- 3e -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 60: -- -- -- -- 62 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 70: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
```

---

# Troubleshooting

## Common Issues

### Bus Pi LCD Shows Garbage Characters

**Cause:** I2C timing issues

**Solution:**
- Increase delays in `write_i2c()` and `write_text()`
- Current timing: 50ms between writes, 100ms between characters

### Audio Not Playing

**Check:**
1. USB speaker is connected: `aplay -l`
2. Correct card number in config: `AUDIO = "plughw:1,0"`
3. Audio files exist: `ls audio/`
4. Test audio: `aplay -D plughw:1,0 audio/it_line_15.wav`

### MQTT Connection Fails

**Check:**
1. Network connectivity: `ping 10.39.44.121`
2. Broker is running: `systemctl status mosquitto`
3. Firewall settings: `sudo ufw status`

### Bus Pi Doesn't Start on Boot

**Check:**
1. Crontab entry: `crontab -l`
2. File permissions: `chmod +x bus_display.py`
3. Python path: Use full path in crontab

---

# Future Possibilities & Enhancements

## 1. Bus Arrival Announcement System

### Concept
Automatically announce when the bus arrives at the stop, not just when requested.

```
┌────────────────────────────────────────────────────────────┐
│              ENHANCED SYSTEM ARCHITECTURE                   │
└────────────────────────────────────────────────────────────┘

   ┌──────────┐        ┌──────────┐        ┌──────────┐
   │   Bus    │        │   Stop   │        │   Bus    │
   │  GPS/IoT │───────►│    Pi    │───────►│    Pi    │
   │  Sensor  │        │  (Hub)   │        │(Display) │
   └──────────┘        └──────────┘        └──────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   Announcements  │
                    │ • "Bus 15 arriving"
                    │ • "Bus 68 arriving"
                    │ • Multi-language
                    └──────────────────┘
```

### Implementation Options

**Option A: GPS-Based Detection**
- GPS module on bus (NEO-6M or similar)
- Compare coordinates with stop location
- Publish arrival when within 50m radius
- Pros: Automatic, no manual input needed
- Cons: Requires GPS module, may have accuracy issues

**Option B: Bluetooth Beacon**
- Beacon transmitter at stop
- Detection when bus enters range (10-50m)
- Pros: Simple, reliable
- Cons: Requires beacon hardware

**Option C: WiFi Probe Request**
- Bus scans for stop's WiFi network
- Pros: No extra hardware
- Cons: Battery drain on bus, unreliable

**Option D: RFID/NFC Tags**
- Tags at each stop
- Bus reads tag when stopping
- Pros: Very accurate
- Cons: Requires reader hardware

## 2. Multi-Language Support Expansion

### Current
- Italian (it_line_XX.wav)
- English (en_line_XX.wav)

### Enhanced
- Add more languages based on passenger demographics:
  - Spanish (es_line_XX.wav)
  - French (fr_line_XX.wav)
  - German (de_line_XX.wav)
  - Mandarin Chinese (zh_line_XX.wav)
  - Arabic (ar_line_XX.wav)

### Language Selection Options
- Touchscreen language menu
- NFC tag at stop for language preference
- Mobile app setting (future)

## 3. Real-Time Bus Tracking Integration

### APIs to Integrate
- GTFS (General Transit Feed Specification)
- GTFS-RT (Real-time extension)
- OpenMobilityData

### Features
- Display actual arrival time
- Show bus route information
- Alert for delays or disruptions

## 4. Passenger Information Display

### Additional LCD Content
```
Line 0: "Bus 15" + Arrival countdown: "3 min"
Line 1: "Lingotto → Centro" + "On Time"
```

### Information Sources
- GTFS static data (routes, stops)
- GTFS-RT (real-time positions)
- Operator dispatch systems

## 5. Two-Way Communication System

### Concept
Passenger can send signals to bus driver.

### Options
- Emergency button → Alert driver
- "Thank you" button → Satisfaction feedback
- "Waiting" indicator → Passenger waiting at stop

### Implementation
```
Passenger presses button
        ↓
Stop Pi detects press
        ↓
MQTT message to Bus Pi
        ↓
Bus Pi:
  • Flashes light (visual alert)
  • Plays distinct audio tone
  • Shows icon on LCD
```

## 6. Solar Power Integration

### For Bus Pi
- Solar panel (10W minimum)
- Battery backup (LiPo 5000mAh)
- Charge controller
- Voltage regulator (12V → 5V)

### Benefits
- Independent of bus power
- Environmentally friendly
- Reduced wiring complexity

## 7. Mobile App Integration

### Features
- Request bus assistance remotely
- Track bus location
- Save language preferences
- Accessibility settings

### Technology
- React Native or Flutter
- Bluetooth Low Energy (BLE)
- WiFi Direct

## 8. Data Collection & Analytics

### Metrics to Collect
- Number of assistance requests
- Peak hours of usage
- Most requested lines
- Average wait times
- Cancelled vs completed requests

### Privacy Considerations
- No personal data collection
- Aggregate statistics only
- GDPR compliant

## 9. Voice Control (Accessibility Enhancement)

### Features
- Voice commands via microphone
- "Call Bus 15" spoken request
- Voice confirmation of actions

### Implementation
- Speech-to-text (Google Speech API or Vosk)
- Wake word detection
- Natural language processing

## 10. Multi-Stop Support

### Concept
One Bus Pi can serve multiple stops along route.

### Implementation
- Match line + stop in MQTT message
- Display specific stop name
- Contextual announcements

---

# Bill of Materials

## Stop Pi Components

| Item | Quantity | Unit Cost | Total |
|------|----------|-----------|-------|
| Raspberry Pi 4 (4GB) | 1 | €55 | €55 |
| 7" Touchscreen Display | 1 | €75 | €75 |
| MicroSD Card (32GB) | 1 | €10 | €10 |
| Power Supply (3A) | 1 | €10 | €10 |
| Case | 1 | €15 | €15 |
| **Total** | | | **€165** |

## Bus Pi Components

| Item | Quantity | Unit Cost | Total |
|------|----------|-----------|-------|
| Raspberry Pi 3 B+ | 1 | €35 | €35 |
| LCD 16x2 + I2C Backpack | 1 | €8 | €8 |
| USB Speaker | 1 | €10 | €10 |
| USB Power Cable | 1 | €5 | €5 |
| USB Power Adapter (12V→5V) | 1 | €15 | €15 |
| **Total** | | | **€73** |

## Optional Components

| Item | Quantity | Unit Cost | Total |
|------|----------|-----------|-------|
| GPS Module (NEO-6M) | 1 | €12 | €12 |
| Bluetooth Beacon | 1 | €8 | €8 |
| Solar Panel (10W) | 1 | €25 | €25 |
| LiPo Battery (5000mAh) | 1 | €15 | €15 |
| Enclosure (waterproof) | 1 | €20 | €20 |

---

# Maintenance Schedule

## Daily Checks
- Verify LCD display is functioning
- Confirm audio is audible
- Check MQTT connectivity

## Weekly Checks
- Test all bus lines
- Verify audio file integrity
- Check for software updates

## Monthly Checks
- Physical inspection of connections
- Clean LCD screen
- Test battery backup (if applicable)
- Review system logs

## Quarterly Updates
- Update Raspbian OS
- Update Python packages
- Backup configurations
- Review and update audio files

---

# Appendix A: Configuration Reference

## bus_display.py Configuration

```python
# MQTT Settings
BROKER = "10.39.44.121"
PORT = 1883
TOPIC = "bus-assistance"

# LCD Settings
LCD = 0x3E       # LCD I2C address
RGB = 0x62       # RGB controller address

# Audio Settings
AUDIO = "plughw:1,0"
AUDIO_DIR = "/home/s4mpie2/smartbus/audio"

# Stop Information
STOP = "Piazza Castello"

# Timer Settings
TIMER = 30       # Auto-reset seconds
```

## config.py (Stop Pi)

```python
# MQTT Broker
BROKER_HOST = "10.39.44.121"
BROKER_PORT = 1883

# Bus Lines
BUS_LINES = ["15", "68", "42", "33"]

# Timing
REQUEST_TIMEOUT_SEC = 30

# Hardware
HAPTIC_PIN = 12  # Optional vibration motor
```

---

# Appendix B: Audio File Specifications

| Parameter | Value |
|-----------|-------|
| Format | WAV |
| Sample Rate | 24000 Hz |
| Bit Depth | 16-bit |
| Channels | Mono |
| Duration | 1-3 seconds |

### Recommended Text-to-Speech

```bash
# Using espeak (Linux)
espeak -w it_line_15.wav "Linea quindici" -v it -s 130

# Using Google TTS (requires internet)
# Use online service to generate audio files
```

---

# Appendix C: Network Configuration

## Static IP Setup (Bus Pi)

Edit `/etc/dhcpcd.conf`:

```
interface wlan0
static ip_address=10.39.44.151/24
static routers=10.39.44.1
static domain_name_servers=8.8.8.8
```

## MQTT Broker Access Control

Edit `/etc/mosquitto/acls`:

```
user readonly
topic read bus-assistance/#

user readonly
topic write bus-assistance/+/request
```

---

# Glossary

| Term | Definition |
|------|------------|
| **I2C** | Inter-Integrated Circuit - Serial communication protocol |
| **MQTT** | Message Queuing Telemetry Transport - Lightweight messaging protocol |
| **CGRAM** | Character Generator RAM - LCD memory for custom characters |
| **DDRAM** | Display Data RAM - LCD memory for displayed characters |
| **GPIO** | General Purpose Input/Output - Programmable pins |
| **ALSA** | Advanced Linux Sound Architecture - Audio driver framework |
| **GTFS** | General Transit Feed Specification - Open data standard |

---

# Contact & Support

For technical questions or support:
- Email: support@smartbus.example.com
- Documentation: https://github.com/smartbus/documentation

---

**Document Version:** 1.0  
**Last Updated:** May 28, 2026  
**Status:** Production Ready
