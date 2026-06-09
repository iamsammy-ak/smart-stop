# 🚌 Smart Stop — Bus Assistance System

An IoT-based accessibility system that helps **hearing-impaired passengers** independently identify which bus is approaching at a public transit stop. The system uses **two Raspberry Pis** that talk to each other over **MQTT**: a *Stop Pi* with a touchscreen at the bus stop, and a *Bus Pi* on the bus itself that displays the stop name and announces on the speaker when a passenger requests assistance.

> **Primary user:** deaf or hard-of-hearing passengers who cannot rely on audio announcements from the bus driver.

---

## ✨ Features

- **Touchscreen request interface** at the stop (one tap per bus line)
- **Live bus line buttons** with color-coded badges (Lines 15, 68, 42, 33)
- **Cancel button** to abort an in-flight request
- **Live weather widget** on the Stop Pi (Open-Meteo, no API key)
- **Animated "waiting" screen** on the Stop Pi while the request is in flight
- **LCD 16×2 + buzzer** feedback on the bus (visual + audible alert for the driver)
- **MQTT-based messaging** — the Stop Pi runs the broker, the Bus Pi subscribes
- **Auto-reset timer** (30 s) returns both sides to idle if no driver confirmation arrives
- **mDNS discovery** — no hard-coded IPs needed (`smartstop-pi.local`)

---

## 🏗️ System Architecture

```
┌─────────────────────────────────┐         MQTT           ┌─────────────────────────────────┐
│           STOP PI               │   bus-assistance/<L>   │            BUS PI               │
│   (runs Mosquitto broker)       │ ─────────────────────► │   (subscribes per bus line)     │
│                                 │   publish: request     │                                 │
│  • 7" Touchscreen  800×480      │   publish: cancel      │  • LCD 16×2  (I2C 0x27)         │
│  • Bus-line buttons  15/68/42/33│   subscribe: accepted  │  • Buzzer      (BCM GPIO2)      │
│  • Cancel button                │                        │  • Optional RGB backlight       │
│  • Weather widget               │                        │  • I2C: SDA=p3, SCL=p5          │
│  • Optional haptic motor (GPIO12)                       │                                 │
└─────────────────────────────────┘                        └─────────────────────────────────┘
        │                                                              │
        ▼                                                              ▼
  Passenger touches                                                 Driver sees
  their bus line                                                    stop name +
                                                                    hears buzzer
```

| Component              | IP (example)            | Role                                 |
|------------------------|-------------------------|--------------------------------------|
| **Stop Pi** (broker)   | `10.39.44.121`          | Touch UI, weather, publishes requests |
| **Bus Pi** (subscriber)| `10.39.44.151`          | LCD + buzzer on the bus              |

> The Stop Pi is also reachable via mDNS as `smartstop-pi.local`.

---

## 📁 Repository Layout

```
smart-stop/
├── README.md                       # ← you are here
├── bus-assistance/                 # ← main project source
│   ├── config.py                   # Stop Pi settings (broker, lines, colors)
│   ├── bus_stop/                   # Stop Pi package
│   │   ├── app.py                  # Tkinter GUI: buttons, weather, waiting
│   │   ├── polito_logo.png
│   │   └── app.py.bak              # (legacy backup — safe to ignore)
│   ├── bus_vehicle/                # Bus Pi package
│   │   ├── app.py                  # MQTT client + LCD + buzzer
│   │   └── config.py               # Bus Pi settings (line, stop, pins)
│   ├── run_bus_pi.sh               # Convenience launcher
│   ├── launcher.sh
│   ├── BUS_PI_SETUP_PROMPT.md      # Step-by-step Bus Pi provisioning
│   ├── PROJECT_SUMMARY.md          # High-level project summary
│   ├── debug.sh
│   ├── copy_xauth.sh / xauth_copy.py / generate_xauth.py
│   └── test_tkinter.sh
├── requirements.txt                # paho-mqtt, smbus2, RPi.GPIO
├── smart-stop.code-workspace       # VS Code workspace (optional)
├── SMART_BUS_SYSTEM_REPORT.md      # Full technical report (v1.0)
├── app.py                          # Stop Pi GUI (single-file variant)
├── bus_display.py                  # Bus Pi display (single-file variant, RGB LCD)
├── bus_display_mqtt.py             # Bus Pi MQTT bridge variant
├── lcd_simple.py / lcd_test.py / test_lcd*.py   # LCD sanity tests
├── publish2.py / publish_dbus.py / publish_mqtt_service.py  # MQTT test publishers
├── debug_mqtt.py / test_audio.py / test_both_lines.py        # Diagnostics
├── set_i2c_speed.sh / fix_volume_and_speed.py                # Hardware tuning
├── run_sudo.py / start-bus-stop.sh / autostart_bus.sh        # Boot helpers
├── bus-display.service / mqtt-service.xml / mqtt-svc.xml     # systemd / upstart units
└── config.py                       # Stop Pi config (top-level mirror of bus-assistance/config.py)
```

The canonical project is `bus-assistance/`. The flat files at the repo root are an earlier single-file iteration kept for reference.

---

## 🔧 Hardware

### Stop Pi

| Part                          | Notes                                              |
|-------------------------------|----------------------------------------------------|
| Raspberry Pi 3 B+ / Pi 4      | Any Pi with DSI / touchscreen support              |
| Official 7" Touchscreen        | 800×480, 5-point capacitive, DSI ribbon            |
| Optional: vibration motor     | BCM GPIO12, pin 32                                 |
| Power: 5 V / 3 A              | USB-C or micro-USB depending on model             |

### Bus Pi

| Part                                | Notes                                         |
|-------------------------------------|-----------------------------------------------|
| Raspberry Pi 3 B+                   | Headless                                       |
| LCD 16×2 + I2C backpack (PCF8574)   | Address `0x27` (or `0x3F`), 4-bit mode         |
| Buzzer (active or passive)          | BCM GPIO2, physical pin 3 (D2 on Grove hat)   |
| Optional: USB speaker               | `plughw:1,0`, used by the single-file variant |
| Power: 12–24 V → 5 V USB adapter    | From bus electrical system                    |

#### LCD wiring (Bus Pi)

| LCD pin | Pi physical pin | Pi BCM       |
|---------|-----------------|--------------|
| GND     | 6               | —            |
| VCC     | 2 or 4          | —            |
| SDA     | 3               | GPIO2 (I2C1) |
| SCL     | 5               | GPIO3 (I2C1) |

#### Buzzer wiring (Bus Pi)

- **D2 on Grove/Seed hat** → **BCM GPIO2** → **physical pin 3**

---

## ⚙️ Software Architecture

### Stop Pi — `bus-assistance/bus_stop/app.py`

- **Tkinter** fullscreen UI on 800×480
- **2-column grid** of bus line buttons (color-coded per `LINE_COLORS`)
- **Cancel** button to abort a request
- **Weather widget** (Open-Meteo, polled every 10 min, no API key)
- **"Waiting" page** with a pulsing circle while the bus Pi responds
- **Haptic pulse** on the optional vibration motor (`HAPTIC_PIN`)
- **MQTT publisher** (paho-mqtt) → `bus-assistance/<line>/request`
- **MQTT subscriber** → `bus-assistance/<line>/accepted` (visual confirmation)

### Bus Pi — `bus-assistance/bus_vehicle/app.py`

- **MQTT subscriber** for its own bus line: `bus-assistance/15/request`
- On request:
  1. Cancel any pending LCD clear
  2. **Ring buzzer** for 3 s (async, non-blocking)
  3. **Update LCD** to `Linea <N>` / `<STOP_NAME>`
  4. **Schedule auto-clear** after `DISPLAY_DURATION_SEC` (default 30 s)
- On `accepted` topic: **flash LCD** twice to confirm
- **HD44780 driver** in 4-bit mode via `smbus2`

### Communication — MQTT topics

| Topic                                  | Direction       | Payload                                   |
|----------------------------------------|-----------------|-------------------------------------------|
| `bus-assistance/<line>/request`        | Stop → Bus      | `"STOP 462 -- Piazza Castello -- LINE 15"`|
| `bus-assistance/<line>/cancelled`      | Stop → Bus      | `"CANCELLED"`                             |
| `bus-assistance/<line>/accepted`       | Bus → Stop      | (driver confirmation, future use)         |

`<line>` is one of `15`, `68`, `42`, `33` by default — editable in `bus-assistance/config.py`.

### Display states

| State             | LCD (Bus Pi)            | RGB backlight     |
|-------------------|-------------------------|-------------------|
| Idle              | Stop name + ready       | (single-file RGB variant: yellow) |
| Request received  | `Linea <N>` / stop name | (red in RGB variant)             |
| Accepted confirm  | LCD flash ×2            | —                                 |

---

## 🚀 Installation

### 1. System packages (both Pis)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip mosquitto mosquitto-clients i2c-tools alsa-utils
```

### 2. Python packages

```bash
pip3 install -r requirements.txt
# paho-mqtt, smbus2, RPi.GPIO
```

### 3. Stop Pi (broker + touchscreen)

```bash
# Copy project
cp -r bus-assistance /home/s4mpie/

# Start the broker
sudo systemctl enable mosquitto
sudo systemctl start  mosquitto

# Launch the GUI
cd /home/s4mpie/bus-assistance
bash run_bus_pi.sh       # or: python3 bus_stop/app.py
```

For autostart, drop the unit in `~/.config/systemd/user/` or add to LXDE autostart.

### 4. Bus Pi (LCD + buzzer)

```bash
# Enable I2C
sudo raspi-config        # Interface Options → I2C → Enable
# or:
sudo raspi-config do_i2c 0 yes
sudo reboot

# Find the LCD address
i2cdetect -y 1
#   0x27 = PCF8574 (most common)
#   0x3F = PCF8574A
# Update bus-assistance/bus_vehicle/config.py → LCD_I2C_ADDRESS

# Run
cd /home/s4mpie/bus-assistance
python3 bus_vehicle/app.py
```

For step-by-step Bus Pi provisioning (SCP, apt, raspi-config, systemd), see [`bus-assistance/BUS_PI_SETUP_PROMPT.md`](bus-assistance/BUS_PI_SETUP_PROMPT.md).

---

## 🔁 End-to-End Flow

```
Passenger          Stop Pi                     MQTT                  Bus Pi                Driver
   │                 │                          │                       │                    │
   │  tap "Line 15"  │                          │                       │                    │
   ├────────────────►│                          │                       │                    │
   │                 │ publish request          │                       │                    │
   │                 ├─────────────────────────►│ bus-assistance/15/request                  │
   │                 │                          ├──────────────────────►│                    │
   │                 │                          │                       │  ring buzzer 3 s   │
   │                 │                          │                       │  LCD: Linea 15 /   │
   │                 │                          │                       │       <STOP_NAME>  │
   │                 │                          │                       ├───────────────────►│
   │  see "waiting"  │                          │                       │                    │
   │◄────────────────│                          │                       │                    │
   │                 │                          │                       │                    │
   │                 │                          │   bus-assistance/15/accepted (optional)     │
   │                 │◄─────────────────────────┤◄──────────────────────┤                    │
   │  see "accepted" │                          │                       │                    │
   │◄────────────────│                          │                       │                    │
   │                 │                          │                       │                    │
   │  (or 30s pass)  │                          │                       │  auto-clear LCD    │
   │                 │                          │                       ├───────────────────►│
   │  back to home   │                          │                       │                    │
   │◄────────────────│                          │                       │                    │
```

---

## 🧪 Testing & Debugging

```bash
# Simulate a request from any machine on the network
mosquitto_pub -h 10.39.44.121 -p 1883 \
  -t "bus-assistance/15/request" \
  -m "STOP 462 -- Piazza Castello -- LINE 15"

# Watch everything fly by
mosquitto_sub -h 10.39.44.121 -p 1883 -t "bus-assistance/#" -v

# Audio test (Bus Pi, single-file variant)
aplay -D plughw:1,0 audio/it_line_15.wav

# LCD test
i2cdetect -y 1
python3 test_lcd.py
```

Common issues and fixes live in the [Troubleshooting](#-troubleshooting) section below.

---

## 🛠️ Troubleshooting

| Symptom                              | Likely cause                      | Fix                                                           |
|--------------------------------------|-----------------------------------|---------------------------------------------------------------|
| Bus Pi LCD shows garbage chars       | I2C timing too fast               | Lower I²C clock (`set_i2c_speed.sh`) or increase delays        |
| Audio not playing                    | Wrong ALSA device                 | Run `aplay -l`, update `AUDIO` in config                       |
| MQTT not connecting                  | Broker not running / firewall     | `systemctl status mosquitto`, `sudo ufw status`, ping broker  |
| Bus Pi doesn't start on boot         | Bad crontab / path                | Use full paths; check `crontab -l`                             |
| LCD blank                            | Wrong I²C address                 | `i2cdetect -y 1` → update `LCD_I2C_ADDRESS`                   |
| Buzzer silent                        | Wrong GPIO                        | BCM GPIO2 / physical pin 3 — verify with `gpio readall`       |
| Touchscreen rotated                  | LCD rotation setting              | Add `display_rotate=0` to `/boot/config.txt`                   |

---

## 🧰 Bill of Materials

### Stop Pi (≈ €165)

| Item                       | Qty |  € |
|----------------------------|----:|----:|
| Raspberry Pi 4 (4 GB)      | 1   | 55 |
| 7" Touchscreen Display     | 1   | 75 |
| microSD 32 GB              | 1   | 10 |
| Power supply (3 A)         | 1   | 10 |
| Case                       | 1   | 15 |

### Bus Pi (≈ €73)

| Item                                | Qty |  € |
|-------------------------------------|----:|----:|
| Raspberry Pi 3 B+                   | 1   | 35 |
| LCD 16×2 + I²C backpack             | 1   |  8 |
| USB speaker                         | 1   | 10 |
| USB power cable                     | 1   |  5 |
| USB power adapter (12 V → 5 V)      | 1   | 15 |

### Optional

| Item                       |  € |
|----------------------------|----:|
| GPS module (NEO-6M)        | 12 |
| Bluetooth beacon           |  8 |
| 10 W solar panel           | 25 |
| LiPo battery 5 000 mAh     | 15 |
| Waterproof enclosure       | 20 |

---

## 🛣️ Roadmap (from the project report)

1. **Automatic bus-arrival detection** — GPS, BLE beacons, WiFi probe, or RFID
2. **More languages** — Italian, English today; add ES / FR / DE / ZH / AR
3. **GTFS / GTFS-RT integration** — real-time arrivals, route info, delay alerts
4. **Richer passenger information** on the LCD (countdown, next stop, status)
5. **Two-way communication** — emergency / "thank you" / "waiting" buttons
6. **Solar power** for the Bus Pi (10 W panel + 5 Ah LiPo)
7. **Companion mobile app** (React Native / Flutter, BLE)
8. **Privacy-respecting analytics** — request counts, peak hours, popular lines
9. **Voice control** — speech-to-text for accessibility
10. **Multi-stop support** — one Bus Pi serving several stops on a route

---

## 🔐 Security notes

- The Mosquitto broker currently accepts **anonymous** connections on port 1883 (LAN only). If you expose it beyond a trusted network, add ACLs in `/etc/mosquitto/mosquitto.conf` and a password file.
- No personal data is collected. All payloads are short status strings.
- The Stop Pi resolves the broker via mDNS (`smartstop-pi.local`) so DHCP IP changes don't break things.

---

## 📚 Further reading

- [`bus-assistance/BUS_PI_SETUP_PROMPT.md`](bus-assistance/BUS_PI_SETUP_PROMPT.md) — full Bus Pi provisioning
- [`bus-assistance/PROJECT_SUMMARY.md`](bus-assistance/PROJECT_SUMMARY.md) — high-level summary
- [`SMART_BUS_SYSTEM_REPORT.md`](SMART_BUS_SYSTEM_REPORT.md) — the original v1.0 technical report
- `bus-assistance/config.py` / `bus-assistance/bus_vehicle/config.py` — tweak everything from here

---

## 📝 License

Internal project — Politecnico di Torino accessibility research.

---

**Document version:** 1.0 · **Status:** Production-ready prototype · **Last updated:** 2026-05-28
