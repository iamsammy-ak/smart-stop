#!/usr/bin/env python3
"""
Smart Bus Display - Clean & Simple Version
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

# Config
BROKER = "10.39.44.121"
PORT = 1883
TOPIC = "bus-assistance"
LCD = 0x3E
RGB = 0x62
AUDIO = "plughw:1,0"
AUDIO_DIR = "/home/s4mpie2/smartbus/audio"
STOP = "Piazza Castello"
TIMER = 30
I2C_SPEED_HZ = 100000  # Set to 100kHz to fix doubled chars (was 400kHz)

# State
running = True
timer_cancelled = False
timer_lock = threading.Lock()
_audio = None
_audio_lock = threading.Lock()
seen = deque(maxlen=50)
bus = SMBus(1)


# Apply slower I2C clock to fix doubled character issue
def configure_i2c_speed():
    """Try to set I2C bus to 100kHz to fix LCD timing issues"""
    try:
        # Method 1: Try to set via sysfs (Raspberry Pi)
        speed_files = [
            "/sys/module/i2c_bcm2708/parameters/baudrate",
            "/sys/class/i2c-adapter/i2c-1/speed",
            "/sys/devices/platform/soc/3f205000.i2c/i2c-1/speed",
        ]
        for path in speed_files:
            if os.path.exists(path):
                try:
                    with open(path, "w") as f:
                        f.write(str(I2C_SPEED_HZ))
                    print(f"[I2C] Speed set to {I2C_SPEED_HZ}Hz via {path}")
                    return True
                except:
                    pass

        # Method 2: Try using i2c-tools
        result = subprocess.run(
            ["i2cdetect", "-y", "1"], capture_output=True, text=True, timeout=2
        )
        print("[I2C] Bus detected, using software timing")
        return False

    except Exception as e:
        print(f"[I2C] Speed config: {e}")
        return False


configure_i2c_speed()


def mqtt_client():
    ver = getattr(mqtt, "CallbackAPIVersion", None)
    if ver:
        return mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    return mqtt.Client(protocol=mqtt.MQTTv311)


# LCD Functions


def write_i2c(addr, reg, data_byte):
    try:
        bus.write_byte_data(addr, reg, data_byte)
        time.sleep(0.05)
    except Exception as e:
        print(f"[I2C ERROR] {e}")


def cmd(c):
    write_i2c(LCD, 0x80, c)
    time.sleep(0.05)  # Extra delay after command


def data(c):
    write_i2c(LCD, 0x40, c)
    time.sleep(0.05)  # Extra delay after data


def init_lcd():
    """One-time LCD initialization - only call once at startup"""
    time.sleep(0.15)

    cmd(0x30)
    time.sleep(0.006)
    cmd(0x30)
    time.sleep(0.002)
    cmd(0x30)
    time.sleep(0.002)

    cmd(0x20)
    time.sleep(0.002)
    cmd(0x28)
    time.sleep(0.002)
    cmd(0x08)
    time.sleep(0.002)
    cmd(0x01)
    time.sleep(0.005)
    cmd(0x06)
    time.sleep(0.002)
    cmd(0x0C)
    time.sleep(0.005)

    print("[LCD] Initialized")


def clear_lcd():
    cmd(0x01)
    time.sleep(0.01)


def set_pos(col, row):
    if row == 0:
        cmd(0x80 + col)
    else:
        cmd(0x80 + 0x40 + col)
    time.sleep(0.01)


def write_text(text):
    """Write text with proper timing"""
    for c in text:
        if c == " ":
            data(0x20)
        else:
            data(ord(c))
        time.sleep(0.1)


def fill_spaces(n):
    for _ in range(n):
        data(0x20)


def make_heart():
    """Create heart character in CGRAM position 7 (far from text)"""
    cmd(0x40 + 56)  # CGRAM address for position 7 (56 = 7*8)
    time.sleep(0.01)
    for r in [0, 10, 31, 31, 14, 4, 0, 0]:
        data(r)
        time.sleep(0.01)
    cmd(0x80)  # Return to DDRAM
    time.sleep(0.01)


def show_heart():
    """Display the heart character (position 7)"""
    data(0x07)  # Character 7
    time.sleep(0.01)


def set_color(r, g, b):
    for reg, val in [(0, 0), (1, 0), (8, 170), (4, r), (3, g), (2, b)]:
        write_i2c(RGB, reg, val)
    time.sleep(0.01)


# Display Functions


def show_idle():
    """Display idle screen"""
    clear_lcd()
    set_color(255, 255, 0)
    time.sleep(0.05)

    set_pos(0, 0)
    write_text("Smart Stop Ready")

    set_pos(0, 1)
    write_text("Yellow team ")
    make_heart()  # Recreate heart (CGRAM resets after clear)
    show_heart()  # Display heart

    print("[LCD] IDLE")


def show_request(line):
    """Display request screen"""
    clear_lcd()
    set_color(255, 0, 0)
    time.sleep(0.05)

    set_pos(0, 0)
    write_text(STOP)

    set_pos(0, 1)
    write_text("Linea " + line)

    print("[LCD] REQUEST: " + STOP + " Linea " + line)


# Audio


def stop_audio():
    global _audio
    with _audio_lock:
        if _audio and _audio.poll() is None:
            _audio.terminate()
            try:
                _audio.wait(timeout=1)
            except:
                pass
            _audio = None


def play_audio(line):
    global _audio
    it = AUDIO_DIR + "/it_line_" + line + ".wav"
    en = AUDIO_DIR + "/en_line_" + line + ".wav"

    print(f"[AUDIO] Playing Italian: {it}")
    if os.path.exists(it):
        stop_audio()
        with _audio_lock:
            _audio = subprocess.Popen(
                ["aplay", "-D", AUDIO, it],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        _audio.wait()
        print("[AUDIO] Italian done")
    else:
        print(f"[AUDIO] File not found: {it}")

    time.sleep(0.3)

    print(f"[AUDIO] Playing English: {en}")
    if os.path.exists(en):
        stop_audio()
        with _audio_lock:
            _audio = subprocess.Popen(
                ["aplay", "-D", AUDIO, en],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        _audio.wait()
        print("[AUDIO] English done")
    else:
        print(f"[AUDIO] File not found: {en}")


# Timer


def cancel_timer():
    global timer_cancelled
    with timer_lock:
        timer_cancelled = True


def start_timer():
    global timer_cancelled

    def run():
        for sec in range(TIMER, 0, -1):
            with timer_lock:
                if timer_cancelled:
                    return
            sys.stdout.write("\r[TIMER] " + str(sec) + " ")
            sys.stdout.flush()
            time.sleep(1)
        print("\n[TIMER] DONE")
        show_idle()

    with timer_lock:
        timer_cancelled = False
        t = threading.Thread(target=run, daemon=True)
        t.start()


def handle_request(line):
    print("[REQUEST] Line " + line)
    cancel_timer()
    stop_audio()
    show_request(line)
    time.sleep(0.5)
    play_audio(line)
    start_timer()


# MQTT


def on_connect(client, userdata, flags, rc, props=None):
    if rc == 0:
        print("[MQTT] Connected")
        client.subscribe(TOPIC + "/+/request")
        client.subscribe(TOPIC + "/+/cancelled")
        client.subscribe(TOPIC + "/timer/expired")
    else:
        print("[MQTT] Failed: " + str(rc))


def on_message(client, userdata, msg, props=None):
    topic = msg.topic.decode() if isinstance(msg.topic, bytes) else msg.topic
    now = time.time()

    key = (topic, now)
    for k, t in seen:
        if abs(now - t) < 2 and k == key:
            return
    seen.append((topic, now))

    print("[MQTT] " + topic)

    if "/cancelled" in topic:
        print("[CANCEL]")
        cancel_timer()
        stop_audio()
        show_idle()
        return

    m = re.match(r"bus-assistance/(\d+)/request", topic)
    if m:
        handle_request(m.group(1))
        return

    if "timer/expired" in topic:
        print("[TIMER EXP]")
        cancel_timer()
        stop_audio()
        show_idle()


# Main


def main():
    print("=" * 40)
    print("SMART BUS DISPLAY")
    print("=" * 40)

    show_idle()

    client = mqtt_client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, keepalive=60)
        client.loop_start()
    except Exception as e:
        print("[ERROR] " + str(e))
        sys.exit(1)

    while running:
        time.sleep(1)


if __name__ == "__main__":
    main()
