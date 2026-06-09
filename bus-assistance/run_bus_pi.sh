#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Bus Assistance — Bus Pi launcher
# Run this on the Bus Pi (the one with LCD + buzzer).
# ─────────────────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Config sanity check ───────────────────────────────────────────────────────
if ! grep -q 'BUS_LINE\s*=' config.py; then
    echo "[ERROR] config.py not found or BUS_LINE not set."
    echo "  → Edit bus_vehicle/config.py and set BUS_LINE, STOP_NAME, etc."
    exit 1
fi

# ── Dependencies ───────────────────────────────────────────────────────────────
echo "[INFO] Checking dependencies..."

pip_install() {
    python3 -m pip show "$1" >/dev/null 2>&1 || python3 -m pip install "$1" --quiet
}

pip_install paho-mqtt
pip_install smbus2

# ── I2C check ──────────────────────────────────────────────────────────────────
if ! command -v i2cdetect >/dev/null 2>&1; then
    echo "[WARN] i2c-tools not found — skipping I2C check."
else
    echo "[INFO] I2C devices on bus 1:"
    i2cdetect -y 1 2>/dev/null || echo "  (i2c not accessible — are you root?)"
fi

# ── Launch ─────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════"
echo "  Starting Bus Pi — Line $(python3 -c "import config; print(config.BUS_LINE)")"
echo "  Broker : $(python3 -c "import config; print(config.BROKER_HOST)")"
echo "  LCD    : I2C 0x$(python3 -c "import config; print(hex(config.LCD_I2C_ADDRESS))")"
echo "  Buzzer : BCM GPIO$(python3 -c "import config; print(config.BUZZER_PIN)")"
echo "═══════════════════════════════════════════════"
echo ""

exec python3 bus_vehicle/app.py
