# Bus Assistance System — Project Summary

> Last updated: 2026-05-19 (evening session)
> Stop Pi IP: `10.248.139.121`

---

## 1. System Overview

```
┌──────────────────────────────────────┐        MQTT         ┌──────────────────────┐
│           BUS STOP PI                 │  bus-assistance/15  │   MQTT BROKER        │
│   (Pi 3B+ + 7" Touch Screen)           │ ──────────────────► │   mosquitto          │
│   User taps a bus line →              │      (publish)      │   10.248.139.121:1883│
│   MQTT message sent to broker        │                     └──────────┬───────────┘
└──────────────────────────────────────┘                             │
                                                                   │  (subscribe to
                                                                   │   only its own line)
                                                                   ▼
                                                         ┌──────────────────────┐
                                                         │     BUS PI           │
                                                         │  (Pi 3B+ + LCD +     │
                                                         │   Buzzer)            │
                                                         │  Lines: 15, 68, etc. │
                                                         └──────────────────────┘
```

---

## 2. File Structure

```
/home/s4mpie/bus-assistance/
├── config.py              ← Broker IP, bus lines, timing
├── copy_xauth_bin         ← SUID C binary — copies X auth cookie (root-owned, suid)
├── copy_xauth.sh          ← Wrapper script that runs the binary
├── run_ui.sh              ← Launches app.py with correct env vars + auth copy
├── bus_stop/
│   ├── app.py             ← Touch screen UI (Tkinter fullscreen, 2-column grid, popup flow)
│   └── __init__.py
└── bus_vehicle/
    ├── app.py             ← NOT YET WRITTEN
    └── __init__.py

/home/s4mpie/.config/systemd/user/
├── bus-stop.service       ← User systemd service (auto-starts on boot/login)
└── bus-stop.desktop       ← Autostart desktop entry
```

---

## 3. What's Working

| Component | Status | Notes |
|-----------|--------|-------|
| MQTT Broker (mosquitto) | ✅ Running | `systemctl status mosquitto`, listening on `0.0.0.0:1883` |
| Bus Stop UI (`bus_stop/app.py`) | ✅ Written & running | Tkinter fullscreen, 2-column bus grid, popup flow |
| Popup window (request sent) | ✅ Working | Blue fullscreen overlay, animated circle, progress bar, cancel button |
| Driver accepted transition | ✅ Written | Green state with checkmark, auto-closes after 4s |
| Auto-reset on timeout | ✅ Working | 60-second timeout resets to idle |
| MQTT publish | ✅ Working | Publishes to `bus-assistance/{LINE}/request` |
| MQTT subscribe (accepted) | ✅ Written | Subscribes to `bus-assistance/{LINE}/accepted` |
| Haptic feedback | ✅ Written | Runs in background thread (GPIO12) |
| Bus-stop systemd service | ✅ Enabled | `systemctl --user enable bus-stop` |
| X11 display | ✅ Working | LightDM + Xorg running, auth cookie setup via SUID binary |
| MQTT client | ✅ Connected | Paho MQTT client connects to broker |
| Haptic motor wiring | ⚠️ Pending | Connect vibration motor to GPIO12 |
| Bus Pi code | ❌ Not written | `bus_vehicle/app.py` still needed |
| Bus Pi setup | ❌ Not done | Configure bus Pi later |

---

## 4. UI Design

- **Screen:** 7" 800×480, fullscreen, no decorations
- **Grid:** 2 columns, 4 bus lines (adjustable in `config.py`)
- **Colors:** Dark navy background (`#0B1F3A`), blue buttons (`#112244`)
- **Button font:** 42pt bold, cyan (`#4FC3F7`)
- **Popup states:**
  - **Requesting:** Blue pulsing circle, "Requesting assistance...", progress bar
  - **Accepted:** Green pulsing circle, "✅ Driver Accepted!", auto-close after 4s
  - **Timeout:** Auto-reset to idle with brief button highlight
  - **Cancelled:** Red button flash, immediate reset

---

## 5. Configuration

**Edit `/home/s4mpie/bus-assistance/config.py`:**

```python
BROKER_HOST = "10.248.139.121"   # This Pi's IP
BROKER_PORT = 1883

# Bus lines shown on the touch screen (2-column grid)
BUS_LINES = ["15", "68", "42", "33"]

REQUEST_TIMEOUT_SEC = 60  # Auto-reset if no driver response

HAPTIC_PIN = 12   # Vibration motor GPIO (set to None to disable)
```

**MQTT Topics:**
- Publish: `bus-assistance/{LINE}/request` — when user taps a line
- Subscribe: `bus-assistance/{LINE}/accepted` — when driver accepts (bus Pi publishes this)

---

## 6. How to Run

### Automatic (on boot / login)
```bash
systemctl --user enable --now bus-stop
```

### Manual
```bash
bash /home/s4mpie/bus-assistance/run_ui.sh
```

### Key commands
```bash
# Restart the UI
systemctl --user restart bus-stop

# View logs
cat /tmp/bus-stop.log

# Test MQTT locally
mosquitto_pub -t "bus-assistance/15/request" -m "TEST"

# Subscribe to all messages
mosquitto_sub -t "bus-assistance/#" -v

# Find Pi IP
hostname -I
```

---

## 7. X11 Authentication Setup (Important)

The Pi uses **LightDM** to manage the X display. The X auth cookie is owned by root at
`/var/run/lightdm/root/:0`. A **SUID C binary** (`copy_xauth_bin`) copies this to
`/home/s4mpie/.Xauthority` and sets the correct permissions so the UI can access X.

This SUID binary is the ONLY reliable way to get X auth in the systemd user session context.
Do NOT use sudo-based approaches — they fail in the systemd environment.

If the UI fails to show on screen:
```bash
/home/s4mpie/bus-assistance/copy_xauth_bin && echo "auth copied"
ls -la /home/s4mpie/.Xauthority  # should be owned by s4mpie
DISPLAY=:0 XAUTHORITY=/home/s4mpie/.Xauthority python3 -c "import tkinter; print('OK')"
```

---

## 8. Known Issues (Resolved)

### Issue: X11 "Authorization required" in systemd user session
**Root cause:** LightDM's X auth file (`/var/run/lightdm/root/:0`) is root-only.
The systemd `--user` session can't read it. `xauth` hangs when run in that context.
`sudo` works but triggers `su` password prompt in the systemd cgroup.

**Solution:** Created SUID C binary (`copy_xauth_bin`) that runs as root (euid=0),
reads the LightDM auth file, writes it to `/home/s4mpie/.Xauthority` with correct
permissions. The binary drops privileges immediately after.

### Issue: `.Xauthority` root-owned lock files
**Root cause:** Some earlier attempts left root-owned `.Xauthority-l` lock files.
`xauth` reads fail with "Permission denied" because the lock is held.

**Fix:** Remove lock files: `sudo rm -f /home/s4mpie/.Xauthority-*`

---

## 9. Remaining Work

### High Priority
1. **[BUS PI] Write `bus_vehicle/app.py`** — MQTT subscribe + LCD + buzzer
2. **[BUS PI] Wire LCD (16x2 HD44780)** — GPIO pins defined in config
3. **[BUS PI] Wire buzzer** — GPIO18 on bus Pi
4. **[BUS PI] Configure `config.py`** — `BROKER_HOST="10.248.139.121"`, `BUS_LINE="15"`

### Medium Priority
5. **[STOP PI] Customize bus lines** — Edit `BUS_LINES` in `config.py`
6. **[STOP PI] Wire haptic motor** — Connect to GPIO12

### Lower Priority
7. **[STOP PI] Static IP** — Fix the IP so bus Pi always knows where to connect

---

## 10. Bus Pi Configuration (Reminder)

When you set up the bus Pi later, copy these files:
- `/home/s4mpie/bus-assistance/config.py` (edit `BUS_LINE` to match the bus number)
- `/home/s4mpie/bus-assistance/bus_vehicle/app.py` (write this)

On the bus Pi, edit `config.py`:
```python
BROKER_HOST = "10.248.139.121"   # Stop Pi's IP
BUS_LINE = "15"                  # This bus's line number
```
