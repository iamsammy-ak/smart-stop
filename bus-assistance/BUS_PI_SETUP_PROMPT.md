# Bus Pi Agent — Setup & Run Prompt
# ==================================
# Run this entire prompt on the BUS PI (10.248.139.151)
# SSH into it first: ssh s4mpie@10.248.139.151

# ─────────────────────────────────────────────────────────────────────────────
# ARCHITECTURE OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

# ┌────────────────────────────┐         MQTT          ┌────────────────────────────┐
# │       STOP PI              │  bus-assistance/15    │        BUS PI              │
# │   (10.248.139.121)         │ ─────────────────────► │   (10.248.139.151)         │
# │                            │     (publish request)  │                            │
# │  • 7" Touch Screen         │                       │  • LCD 16x2 ← I2C-1        │
# │  • Mosquitto Broker        │                       │  • Buzzer  ← D2 (GPIO2)    │
# │  • Bus lines: 15,68,42,33  │                       │  • Subscribes to:           │
# │                            │                       │    bus-assistance/15/request
# └────────────────────────────┘                       └────────────────────────────┘

# ─────────────────────────────────────────────────────────────────────────────
# 1. COPY FILES FROM STOP PI TO BUS PI
# ─────────────────────────────────────────────────────────────────────────────

# Run on STOP PI first to copy files:
scp -r /home/s4mpie/bus-assistance/ s4mpie@10.248.139.151:/home/s4mpie/

# ─────────────────────────────────────────────────────────────────────────────
# 2. SSH INTO BUS PI
# ─────────────────────────────────────────────────────────────────────────────

ssh s4mpie@10.248.139.151

# ─────────────────────────────────────────────────────────────────────────────
# 3. INSTALL DEPENDENCIES
# ─────────────────────────────────────────────────────────────────────────────

sudo apt update
sudo apt install -y i2c-tools python3-pip python3-venv

# Install Python libraries
pip install paho-mqtt smbus2

# ─────────────────────────────────────────────────────────────────────────────
# 4. ENABLE I2C
# ─────────────────────────────────────────────────────────────────────────────

sudo raspi-config
# Navigate: Interface Options → I2C → Enable → Finish → Reboot

# Or do it non-interactively:
sudo raspi-config do_i2c 0 yes
sudo reboot

# ─────────────────────────────────────────────────────────────────────────────
# 5. FIND LCD I2C ADDRESS
# ─────────────────────────────────────────────────────────────────────────────

# After reboot, check I2C bus:
i2cdetect -y 1

# Common addresses:
#   0x27 = PCF8574 (most common)
#   0x3F = PCF8574A
# Note the address — you'll need it in config.py

# ─────────────────────────────────────────────────────────────────────────────
# 6. EDIT CONFIG FILE
# ─────────────────────────────────────────────────────────────────────────────

nano /home/s4mpie/bus-assistance/bus_vehicle/config.py

# ─── Paste this full config, replacing the existing one ─────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Bus Assistance System — Bus Pi Configuration
# ─────────────────────────────────────────────────────────────────────────────

BROKER_HOST = "10.248.139.121"   # Stop Pi's IP (runs mosquitto broker)
BROKER_PORT = 1883

# ── This bus's identity ────────────────────────────────────────────────────────
BUS_LINE    = "15"           # The bus line number this driver handles
STOP_NAME   = "Fermata Lingotto"   # Name shown on LCD (max 16 chars)

# ── Hardware: Buzzer ──────────────────────────────────────────────────────────
# D2 on Grover/Seed kit pinout  →  BCM GPIO2  (physical pin 3)
BUZZER_PIN  = 2

# ── Hardware: LCD 16×2 via I2C ────────────────────────────────────────────────
# Connected to I2C-1 (pins 3=SDA, 5=SCL on all Pi)
# Set to your address from step 5 (likely 0x27 or 0x3F)
LCD_I2C_ADDRESS = 0x27
LCD_COLS = 16
LCD_ROWS = 2

# ── Timing ────────────────────────────────────────────────────────────────────
DISPLAY_DURATION_SEC = 30     # Auto-clear LCD after this long

# ─────────────────────────────────────────────────────────────────────────────
# 7. VERIFY WIRING
# ─────────────────────────────────────────────────────────────────────────────

# Buzzer: Connect to D2
#   - D2 on Grover/Seed hat = BCM GPIO2 = Physical pin 3
#   - Check with: gpio readall

# LCD: Connect via I2C-1
#   - SDA → Physical pin 3 (GPIO2)
#   - SCL → Physical pin 5 (GPIO3)
#   - VCC → 5V (pin 2 or 4)
#   - GND → GND (pin 6)

# ─────────────────────────────────────────────────────────────────────────────
# 8. TEST MQTT CONNECTIVITY
# ─────────────────────────────────────────────────────────────────────────────

# Test from bus pi to broker (stop pi)
mosquitto_pub -h 10.248.139.121 -p 1883 -t "bus-assistance/15/test" -m "hello"

# Subscribe on bus pi to see if broker is reachable
mosquitto_sub -h 10.248.139.121 -p 1883 -t "bus-assistance/#" -v

# ─────────────────────────────────────────────────────────────────────────────
# 9. RUN THE BUS PI APP
# ─────────────────────────────────────────────────────────────────────────────

cd /home/s4mpie/bus-assistance
bash run_bus_pi.sh

# ─────────────────────────────────────────────────────────────────────────────
# EXPECTED OUTPUT
# ─────────────────────────────────────────────────────────────────────────────

# On successful startup you should see:
# ==================================================
#   Bus Pi  —  Line 15  |  Stop: Fermata Lingotto
#   Broker : 10.248.139.121:1883
#   Buzzer : BCM GPIO2
#   LCD    : I2C 0x27  (16x2)
#   Display: 30s auto-clear
# ==================================================
#   LCD: "Linea 15  ok"
#   LCD row 2: "Attesa richieste..."
#   MQTT connected — subscribed to line 15

# ─────────────────────────────────────────────────────────────────────────────
# 10. SIMULATE A REQUEST (from Stop Pi)
# ─────────────────────────────────────────────────────────────────────────────

# On Stop Pi terminal:
mosquitto_pub -t "bus-assistance/15/request" -m "Help request from stop"

# Bus Pi should:
#   1. Print "[HH:MM:SS] *** REQUEST for line 15 ***"
#   2. Ring buzzer for 3 seconds
#   3. LCD row 1: "Linea 15"
#   4. LCD row 2: "Fermata Lingotto"
#   5. After 30s: clear LCD

# ─────────────────────────────────────────────────────────────────────────────
# 11. AUTO-START ON BOOT (systemd user service)
# ─────────────────────────────────────────────────────────────────────────────

mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/bus-vehicle.service << 'EOF'
[Unit]
Description=Bus Vehicle Pi — LCD + Buzzer MQTT Client
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/s4mpie/bus-assistance
ExecStart=/home/s4mpie/bus-assistance/run_bus_pi.sh
Restart=on-failure
RestartSec=5
StandardOutput=append:/tmp/bus-vehicle.log
StandardError=append:/tmp/bus-vehicle.log

[Install]
WantedBy=default.target
EOF

systemctl --user enable --now bus-vehicle

# Check logs:
cat /tmp/bus-vehicle.log

# Restart if needed:
systemctl --user restart bus-vehicle

# ─────────────────────────────────────────────────────────────────────────────
# TROUBLESHOOTING
# ─────────────────────────────────────────────────────────────────────────────

# MQTT not connecting?
#   - Check broker is running on stop pi: systemctl status mosquitto
#   - Check firewall: sudo ufw status
#   - Test ping: ping 10.248.139.121

# LCD not showing?
#   - Check address: i2cdetect -y 1 (should show 27 or 3F)
#   - Update LCD_I2C_ADDRESS in config.py
#   - Check wiring: SDA, SCL, VCC, GND

# Buzzer not working?
#   - Test GPIO: python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(2, GPIO.OUT); GPIO.output(2, GPIO.HIGH)"
#   - Should light up. Ctrl+C to stop.

# LCD shows wrong characters?
#   - Your LCD may have a different character ROM
#   - Common: A00 (Japanese) vs A02 (European)
#   - The code uses standard HD44780 — try 0x3F if 0x27 fails

# ─────────────────────────────────────────────────────────────────────────────
# QUICK REFERENCE
# ─────────────────────────────────────────────────────────────────────────────

# Stop Pi IP:       10.248.139.121 (runs mosquitto broker)
# Bus Pi IP:        10.248.139.151 (this pi)
# MQTT Topic:       bus-assistance/15/request
# LCD I2C:          0x27 (verify with i2cdetect -y 1)
# Buzzer Pin:       BCM GPIO2 (D2 on grove hat)
# Display Duration: 30 seconds
