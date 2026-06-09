# ─────────────────────────────────────────────────────────────────────────────
# Bus Assistance System — Bus Pi Configuration
# Runs on the Pi with LCD + Buzzer (Grover Seed/Grover kit wiring)
# ─────────────────────────────────────────────────────────────────────────────

BROKER_HOST = "10.39.44.121"  # Stop Pi's IP (runs mosquitto broker)
BROKER_PORT = 1883

# ── This bus's identity ───────────────────────────────────────────────────────
BUS_LINE = "15"  # The bus line number this driver handles
STOP_NAME = "Fermata Lingotto"  # Short name shown on LCD (≤ 16 chars ideal)

# ── Hardware: Buzzer ──────────────────────────────────────────────────────────
# D2 on Grover/Seed kit pinout  →  BCM GPIO2  (physical pin 3)
BUZZER_PIN = 2

# ── Hardware: LCD 16×2 via I2C ────────────────────────────────────────────────
# Connected to I2C-1 (pins 3=SDA, 5=SCL on all Pi)
# Common addresses: 0x27 (PCF8574) or 0x3F (PCF8574A)
# Run:  i2cdetect -y 1   to verify
LCD_I2C_ADDRESS = 0x27
LCD_COLS = 16
LCD_ROWS = 2

# ── Timing ────────────────────────────────────────────────────────────────────
DISPLAY_DURATION_SEC = 30  # Auto-clear LCD after this long
