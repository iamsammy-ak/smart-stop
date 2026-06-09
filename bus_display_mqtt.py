#!/usr/bin/env python3
"""
Smart Bus Display System — MQTT Edition
Subscribes to ALL bus-assistance/<LINE>/request topics.
On request: LCD turns RED with stop name + number, speaker announces the line.

Hardware:
- LCD RGB 16x2 I2C: LCD=0x3E  RGB=0x62
- Speaker: USB card 1, device plughw:1,0
- Broker: 10.39.44.121:1883
"""

import os
import re
import signal
import subprocess
import sys
import threading
import time
from collections import deque

import paho.mqtt.client as mqtt
from smbus2 import SMBus

# ── Config ────────────────────────────────────────────────────────
BROKER_HOST = "10.39.44.121"
BROKER_PORT = 1883
TOPIC_PREFIX = "bus-assistance"

LCD_ADDR = 0x3E
RGB_ADDR = 0x62

AUDIO_DEVICE = "plughw:1,0"
AUDIO_DIR = "/home/s4mpie2/smartbus/audio"

STOP_NAME = "Piazza Castello"
STOP_NUMBER = "462"
TIMEOUT_SECONDS = 30


# ── State ─────────────────────────────────────────────────────────
running = True
timer_thread = None
timer_cancelled = False
timer_lock = threading.Lock()
_audio_proc = None
_audio_lock = threading.Lock()

DEDUP_WINDOW = 2
_seen = deque(maxlen=50)

bus = SMBus(1)


def make_mqtt_client():
    ver = getattr(mqtt, "CallbackAPIVersion", None)
    if ver is not None:
        return mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    return mqtt.Client(protocol=mqtt.MQTTv311)


# ══════════════════════════════════════════════════════════════════
# I2C / LCD
# ══════════════════════════════════════════════════════════════════


def i2c_write(addr, reg, data, retries=3):
    for _ in range(retries):
        try:
            bus.write_byte_data(addr, reg, data)
            return True
        except OSError:
            time.sleep(0.01)
    return False


def lcd_cmd(cmd):
    i2c_write(LCD_ADDR, 0x80, cmd)
    time.sleep(0.001)


def lcd_data(data):
    i2c_write(LCD_ADDR, 0x40, data)
    time.sleep(0.001)


def lcd_init():
    time.sleep(0.05)
    lcd_cmd(0x30)
    time.sleep(0.005)
    lcd_cmd(0x30)
    time.sleep(0.005)
    lcd_cmd(0x30)
    time.sleep(0.005)
    lcd_cmd(0x20)
    time.sleep(0.005)
    lcd_cmd(0x28)
    time.sleep(0.005)
    lcd_cmd(0x08)
    time.sleep(0.005)
    lcd_cmd(0x01)
    time.sleep(0.005)
    lcd_cmd(0x06)
    time.sleep(0.005)
    lcd_cmd(0x0C)
    time.sleep(0.005)


def set_rgb(r, g, b):
    for reg, val in [(0, 0), (1, 0), (0x08, 0xAA), (4, r), (3, g), (2, b)]:
        i2c_write(RGB_ADDR, reg, val)
        time.sleep(0.001)


def lcd_clear():
    lcd_cmd(0x01)
    time.sleep(0.005)


def lcd_set_cursor(col, row):
    addr = (0x40 * row) + col
    lcd_cmd(0x80 | addr)
    time.sleep(0.001)


def lcd_print(text):
    for ch in text:
        lcd_data(ord(ch))
        time.sleep(0.001)


def lcd_write(text, line):
    """Write text on given line (0 or 1)."""
    lcd_set_cursor(0, line)
    lcd_print(text.ljust(16))


def lcd_show_ready():
    """Blue screen: Line 0 = Smart, Line 1 = blank."""
    try:
        lcd_init()
        time.sleep(0.05)
        set_rgb(0, 128, 255)
        lcd_clear()
        time.sleep(0.005)
        lcd_write("Smart", 0)
        lcd_write("            ", 1)
        print("[LCD] Ready (BLUE)")
    except Exception as e:
        print("[LCD ERROR] %s" % e)


def lcd_show_request():
    """Red screen: Line 0 = stop name, Line 1 = stop number."""
    try:
        lcd_init()
        time.sleep(0.05)
        set_rgb(255, 0, 0)
        lcd_clear()
        time.sleep(0.005)
        lcd_write(STOP_NAME, 0)
        lcd_write("Stop " + STOP_NUMBER, 1)
        print("[LCD] %s — Stop %s (RED)" % (STOP_NAME, STOP_NUMBER))
    except Exception as e:
        print("[LCD ERROR] %s" % e)


# ══════════════════════════════════════════════════════════════════
# Speaker — cancellable
# ══════════════════════════════════════════════════════════════════


def stop_audio():
    """Kill any currently playing audio immediately."""
    global _audio_proc
    with _audio_lock:
        if _audio_proc and _audio_proc.poll() is None:
            _audio_proc.terminate()
            try:
                _audio_proc.wait(timeout=1)
            except Exception:
                pass
            _audio_proc = None


def play_audio(line, language="both"):
    """Play Italian then English audio for the given line."""
    global _audio_proc
    it_file = "%s/it_line_%s.wav" % (AUDIO_DIR, line)
    en_file = "%s/en_line_%s.wav" % (AUDIO_DIR, line)

    if language in ("it", "both") and os.path.exists(it_file):
        print("[SPEAKER] Italian: Linea %s" % line)
        stop_audio()
        with _audio_lock:
            _audio_proc = subprocess.Popen(
                "aplay -D %s %s 2>/dev/null" % (AUDIO_DEVICE, it_file), shell=True
            )
        _audio_proc.wait()

    if language in ("en", "both"):
        time.sleep(0.3)
        if os.path.exists(en_file):
            print("[SPEAKER] English: Line %s" % line)
            stop_audio()
            with _audio_lock:
                _audio_proc = subprocess.Popen(
                    "aplay -D %s %s 2>/dev/null" % (AUDIO_DEVICE, en_file), shell=True
                )
            _audio_proc.wait()
        else:
            print("[WARN] English audio not found: %s" % en_file)


# ══════════════════════════════════════════════════════════════════
# Timer
# ══════════════════════════════════════════════════════════════════


def cancel_timer():
    global timer_thread, timer_cancelled
    with timer_lock:
        timer_cancelled = True


def start_timer():
    global timer_thread, timer_cancelled

    def _run():
        for sec in range(TIMEOUT_SECONDS, 0, -1):
            with timer_lock:
                if timer_cancelled:
                    print("[TIMER] Cancelled")
                    return
            sys.stdout.write("\r[TIMER] %ds remaining... " % sec)
            sys.stdout.flush()
            time.sleep(1)
        print("\n[TIMER] Done — returning to Ready")
        lcd_show_ready()

    with timer_lock:
        timer_cancelled = False
        timer_thread = threading.Thread(target=_run, daemon=True)
        timer_thread.start()


# ══════════════════════════════════════════════════════════════════
# Request handler
# ══════════════════════════════════════════════════════════════════


def handle_request(line):
    print("\n" + "=" * 50)
    print("  REQUEST — Line %s  |  Stop %s" % (line, STOP_NUMBER))
    print("=" * 50)

    cancel_timer()
    stop_audio()  # stop any audio already playing

    def _display():
        lcd_show_request()
        time.sleep(0.5)
        play_audio(line, "both")

    threading.Thread(target=_display, daemon=True).start()
    start_timer()


# ══════════════════════════════════════════════════════════════════
# MQTT — ALL lines + cancelled
# ══════════════════════════════════════════════════════════════════


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("[MQTT] Connected — subscribing to all lines")
        client.subscribe("%s/+/request" % TOPIC_PREFIX)
        client.subscribe("%s/+/cancelled" % TOPIC_PREFIX)
    else:
        print("[MQTT] Connection failed, rc=%d" % rc)


def on_message(client, userdata, msg, properties=None):
    topic = msg.topic.decode() if isinstance(msg.topic, bytes) else msg.topic
    payload = msg.payload.decode() if isinstance(msg.payload, bytes) else msg.payload
    now = time.time()

    # Deduplicate — ignore same topic+payload within window
    cutoff = now - DEDUP_WINDOW
    key = (topic, payload)
    for saved_key, ts in _seen:
        if ts > cutoff and saved_key == key:
            return
    _seen.append((key, now))

    print("[MQTT] %s  %r" % (topic, payload))

    # Cancelled — stop audio, reset LCD
    m = re.match(r"bus-assistance/(\S+)/cancelled", topic)
    if m:
        print("[MQTT] Request cancelled — resetting display + stopping audio")
        cancel_timer()
        stop_audio()
        lcd_show_ready()
        return

    # Request — extract line number
    m = re.match(r"bus-assistance/(\S+)/request", topic)
    if m:
        handle_request(m.group(1))


# ══════════════════════════════════════════════════════════════════
# Shutdown
# ══════════════════════════════════════════════════════════════════


def shutdown_handler(signum=None, frame=None):
    global running
    print("\n[SHUTDOWN] Stopping...")
    running = False
    stop_audio()
    try:
        lcd_init()
        set_rgb(0, 0, 0)
        lcd_clear()
    except Exception:
        pass
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)


# ══════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════


def main():
    print("=" * 50)
    print("  SMART BUS DISPLAY — MQTT Edition")
    print("  Broker : %s:%s" % (BROKER_HOST, BROKER_PORT))
    print("  Stop   : %s (#%s)" % (STOP_NAME, STOP_NUMBER))
    print("  Mode   : ALL LINES active")
    print("=" * 50)

    lcd_show_ready()

    client = make_mqtt_client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        client.loop_start()
        sys.stdout.flush()
    except Exception as e:
        print("[ERROR] Cannot connect to broker: %s" % e)
        sys.exit(1)

    while running:
        time.sleep(1)


if __name__ == "__main__":
    main()
