#!/usr/bin/env python3
"""
Bus Assistance System — Bus Vehicle Pi
========================================
Hardware:
  - Buzzer  →  D2 (BCM GPIO2, physical pin 3)
  - LCD 16×2 →  I2C-1 (SDA=p3, SCL=p5), default address 0x27

Behaviour:
  - Connects to the mosquitto broker at BROKER_HOST
  - Subscribes to  bus-assistance/<BUS_LINE>/request
  - On incoming request:
      1. Ring buzzer for 3 seconds
      2. Show on LCD: bus line + stop name, for 30 seconds
  - After 30 seconds, clear LCD and arm for next request
  - Also subscribes to  bus-assistance/<BUS_LINE>/accepted  to
    give driver visual confirmation that the request was acknowledged.
"""

import json
import sys
import threading
import time
from datetime import datetime

import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO

# ── Local config ──────────────────────────────────────────────────────────────
from config import (
    BROKER_HOST,
    BROKER_PORT,
    BUS_LINE,
    BUZZER_PIN,
    DISPLAY_DURATION_SEC,
    LCD_COLS,
    LCD_I2C_ADDRESS,
    LCD_ROWS,
    STOP_NAME,
    accepted_topic,
    request_topic,
)

# ══════════════════════════════════════════════════════
# GPIO — Buzzer
# ══════════════════════════════════════════════════════


def buzz_on(duration=3.0):
    """Activate buzzer for `duration` seconds (blocking)."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    try:
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(duration)
    finally:
        GPIO.output(BUZZER_PIN, GPIO.LOW)


def buzz_async(duration=3.0):
    t = threading.Thread(target=buzz_on, args=(duration,), daemon=True)
    t.start()


# ══════════════════════════════════════════════════════
# LCD 16×2 via I2C (PCF8574 / hd44780)
# ══════════════════════════════════════════════════════
# Uses the smbus2 library (pip install smbus2).
# If you prefer the `lcd-asyncio` library, swap this class accordingly.

try:
    from smbus2 import SMBus

    LCD_AVAILABLE = True
except ImportError:
    LCD_AVAILABLE = False
    print("[WARN] smbus2 not installed — LCD disabled.  Run: pip install smbus2")

# HD44780 command constants
LCD_CLEAR = 0x01
LCD_HOME = 0x02
LCD_ENTRYMODE = 0x04
LCD_DISPLAYON = 0x08
LCD_FUNCSET = 0x20
LCD_CONTRAST = 0x28  # 4-bit mode, 2 lines, 5×8 chars

LCD_RS = 0b00000001  # Register Select (0=cmd, 1=data)
LCD_RW = 0b00000010  # Read/Write (0=write)
LCD_EN = 0b00000100  # Enable
LCD_BACKLIGHT = 0b00001000  # Backlight on

MASK_RS_EN = LCD_RS | LCD_EN
MASK_DATA = LCD_EN  # data mode = EN + RS
MASK_CMD = 0  # command mode = EN only
MASK_BACKLIGHT = LCD_BACKLIGHT | LCD_EN

# Timing
LCD_PULSE_US = 50  # EN pulse width


class HD44780:
    """Simple 4-bit I2C driver for PCF8574-based 16×2 LCD."""

    def __init__(self, busnum=1, addr=LCD_I2C_ADDRESS, cols=16, rows=2):
        self.busnum = busnum
        self.addr = addr
        self.cols = cols
        self.rows = rows
        self.bus = None

    def _write_nibble(self, nibble, rs=True):
        """Write one 4-bit nibble with EN strobe."""
        byte = nibble << 4 | LCD_BACKLIGHT | (LCD_RS if rs else 0) | LCD_EN
        self.bus.write_byte(self.addr, byte)
        time.sleep_us(LCD_PULSE_US)
        self.bus.write_byte(self.addr, byte & ~LCD_EN)
        time.sleep_us(LCD_PULSE_US)

    def _write_byte(self, value, rs=True):
        self._write_nibble(value >> 4, rs=rs)
        self._write_nibble(value & 0x0F, rs=rs)

    def init(self):
        self.bus = SMBus(self.busnum)
        time.sleep_ms(50)

        # 8-bit sequence for 4-bit mode init (see HD44780 datasheet)
        for _ in range(3):
            self._write_nibble(0b0011, rs=False)
            time.sleep_ms(5)

        # Switch to 4-bit mode
        self._write_nibble(0b0010, rs=False)
        time.sleep_us(100)

        # Function set: 4-bit, 2 lines, 5×8 font
        self._write_byte(0x28, rs=False)  # N=1 (2 lines), F=0 (5×8)
        time.sleep_us(50)

        self._write_byte(0x0C, rs=False)  # Display ON, cursor OFF
        time.sleep_us(50)

        self._write_byte(0x06, rs=False)  # Entry mode: increment, no shift
        time.sleep_us(50)

        self.clear()

    def clear(self):
        self._write_byte(LCD_CLEAR, rs=False)
        time.sleep_ms(2)

    def set_cursor(self, col, row):
        row_offsets = (0x00, 0x40, 0x14, 0x54)
        if row < len(row_offsets):
            addr = row_offsets[row] + col
        else:
            addr = col
        self._write_byte(0x80 | addr, rs=False)
        time.sleep_us(50)

    def print(self, text):
        for ch in text:
            if ch == "\n":
                # Move to second line manually
                self.set_cursor(0, 1)
            else:
                self._write_byte(ord(ch), rs=True)
                time.sleep_us(50)

    def close(self):
        if self.bus:
            self.bus.close()


# ══════════════════════════════════════════════════════
# State
# ══════════════════════════════════════════════════════

lcd = None
display_timer = None  # threading.Timer for auto-clear


def clear_display():
    global lcd
    if lcd:
        lcd.clear()
        print(f"[{now()}] LCD cleared")


# ══════════════════════════════════════════════════════
# MQTT callbacks
# ══════════════════════════════════════════════════════


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{now()}] MQTT connected — subscribed to line {BUS_LINE}")
        client.subscribe(request_topic(BUS_LINE))
        client.subscribe(accepted_topic(BUS_LINE))
    else:
        print(f"[{now()}] MQTT connect failed, rc={rc}")


def on_disconnect(client, userdata, rc):
    print(f"[{now()}] MQTT disconnected (rc={rc})")


def on_message(client, userdata, msg):
    topic = msg.topic.decode() if isinstance(msg.topic, bytes) else msg.topic
    payload = msg.payload.decode() if isinstance(msg.payload, bytes) else msg.payload
    print(f"[{now()}] MQTT ← {topic}  payload={payload!r}")

    if topic == request_topic(BUS_LINE):
        handle_request(payload)
    elif topic == accepted_topic(BUS_LINE):
        handle_accepted(payload)


# ── Request arrived — ring buzzer + show LCD ────────────────────────────────


def handle_request(payload):
    global display_timer

    print(f"[{now()}] *** REQUEST for line {BUS_LINE} ***")
    print(f"        Stop: {STOP_NAME}")

    # Cancel any pending auto-clear
    if display_timer and display_timer.is_alive():
        display_timer.cancel()

    # 1. Buzzer (async so LCD starts immediately)
    buzz_async(duration=3.0)

    # 2. LCD
    if lcd:
        lcd.clear()
        time.sleep_ms(10)

        line_str = f"Linea {BUS_LINE}"
        lcd.set_cursor(0, 0)
        lcd.print(line_str)

        # Centre stop name on row 2 (truncate if > 16 chars)
        stop = STOP_NAME[:LCD_COLS]
        lcd.set_cursor(0, 1)
        lcd.print(stop)
        print(f"[{now()}] LCD: '{line_str}' | '{stop}'")
    else:
        print("[WARN] LCD not available")

    # 3. Auto-clear after DISPLAY_DURATION_SEC
    display_timer = threading.Timer(DISPLAY_DURATION_SEC, clear_display)
    display_timer.daemon = True
    display_timer.start()


# ── Accepted confirmation ────────────────────────────────────────────────────


def handle_accepted(payload):
    """Flash LCD twice to confirm acceptance received."""
    print(f"[{now()}] Accepted confirmed for line {BUS_LINE}")
    if lcd:
        for _ in range(2):
            lcd._write_byte(LCD_DISPLAYON ^ 0x04, rs=False)  # toggle display off/on
            time.sleep_ms(300)


# ══════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════


def now():
    return datetime.now().strftime("%H:%M:%S")


def main():
    global lcd

    print("=" * 50)
    print(f"Bus Pi  —  Line {BUS_LINE}  |  Stop: {STOP_NAME}")
    print(f"Broker : {BROKER_HOST}:{BROKER_PORT}")
    print(f"Buzzer : BCM GPIO{BUZZER_PIN}")
    print(f"LCD    : I2C 0x{LCD_I2C_ADDRESS:02X}  ({LCD_COLS}x{LCD_ROWS})")
    print(f"Display: {DISPLAY_DURATION_SEC}s auto-clear")
    print("=" * 50)

    # ── LCD init ──────────────────────────────────────────────────────────────
    if LCD_AVAILABLE:
        try:
            lcd = HD44780(busnum=1, addr=LCD_I2C_ADDRESS, cols=LCD_COLS, rows=LCD_ROWS)
            lcd.init()
            lcd.print(f"Linea {BUS_LINE}  ok")
            lcd.set_cursor(0, 1)
            lcd.print("Attesa richieste...")
            print(f"[{now()}] LCD initialised")
        except Exception as e:
            print(f"[WARN] LCD init failed: {e}")
            lcd = None
    else:
        print("[WARN] LCD disabled (smbus2 missing)")
        lcd = None

    # ── MQTT ──────────────────────────────────────────────────────────────────
    client = mqtt.Client(
        protocol=mqtt.MQTTv311,
        userdata={"line": BUS_LINE},
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        client.loop_start()
    except Exception as e:
        print(f"[ERROR] MQTT connect failed: {e}")
        sys.exit(1)

    # ── Idle ──────────────────────────────────────────────────────────────────
    print(f"[{now()}] Bus Pi running — press Ctrl+C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n[{now()}] Shutting down...")
        client.loop_stop()
        client.disconnect()
        if lcd:
            lcd.clear()
            lcd.close()
        GPIO.cleanup()


if __name__ == "__main__":
    main()
