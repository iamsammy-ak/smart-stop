#!/usr/bin/env python3
"""
Smart Stop — Bus Stop Assistance UI
Fullscreen kiosk on 7" 800x480 Raspberry Pi display.
"""

import json
import os
import random
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import font as tkfont
from zoneinfo import ZoneInfo

# Italy timezone (Turin is in Europe/Rome)
TZ_ROME = ZoneInfo("Europe/Rome")

import paho.mqtt.client as mqtt

from config import (
    BROKER_HOST,
    BROKER_PORT,
    BUS_LINES,
    HAPTIC_PIN,
    LINE_COLORS,
    REQUEST_TIMEOUT_SEC,
    accepted_topic,
    cancelled_topic,
    request_topic,
)

# ── Weather: Open-Meteo free Italy weather ───────────
WEATHER_TEMP = "--"
WEATHER_COND = ""
WEATHER_LOCK = threading.Lock()


def _fetch_weather(lat=41.9028, lon=12.4964):
    """Fetch real-time weather from Open-Meteo for Italy (no API key)."""
    global WEATHER_TEMP, WEATHER_COND
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,weather_code"
        f"&timezone=Europe/Rome"
    )
    try:
        import urllib.request

        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        cur = data.get("current", {})
        temp = cur.get("temperature_2m", 0)
        code = cur.get("weather_code", 0)
        with WEATHER_LOCK:
            WEATHER_TEMP = f"{temp:.0f}C"
            WEATHER_COND = _wmo_description(code)
        # Refresh every 10 minutes
        threading.Timer(600, _fetch_weather, args=[lat, lon]).start()
    except Exception:
        pass


def _wmo_description(code: int) -> str:
    codes = {
        0: "Clear",
        1: "Fair",
        2: "Cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Fog",
        51: "Drizzle",
        53: "Drizzle",
        55: "Drizzle",
        61: "Rain",
        63: "Rain",
        65: "Rain",
        71: "Snow",
        73: "Snow",
        75: "Snow",
        80: "Showers",
        81: "Showers",
        82: "Showers",
        95: "Thunder",
        96: "Thunder",
        99: "Thunder",
    }
    return codes.get(code, "")


# Start weather fetch in background thread (Open-Meteo free Italy weather)
threading.Thread(target=_fetch_weather, daemon=True).start()

# ══════════════════════════════════════════════════════
# Colours
# ══════════════════════════════════════════════════════
NAVY = "#001c3d"
YELLOW = "#fdb913"
WHITE = "#ffffff"
LGREY = "#e9ecef"
DGREY = "#6a6a6a"
BTN_BG = "#003872"
BTN_HOV = "#004a99"
BTN_DIS = "#3366a0"
RED_BTN = "#cc2222"
BLUE = "#0077cc"
GREEN = "#2ead66"
GREEN_D = "#1a7a4a"

# Info screen palette
# 0-3 min  -> green  (bus is here or about to be)
# 4-6 min  -> orange (coming soon)
# 7+ min   -> yellow (later)
ARRIVING_BG = "#1f9d54"  # green pill for 0-3 min
SOON_BG = "#ff7a1a"  # orange pill for 4-6 min
LATER_BG = "#fdb913"  # yellow pill for 7+ min
LATER_FG = "#1a1a1a"  # dark text on yellow pill
INFO_PILL_BG = "#001c3d"  # navy, for the "Tap to request" pill (matches header)

# ══════════════════════════════════════════════════════
# Stop info
# ══════════════════════════════════════════════════════
STOP_NAME = "Piazza Castello"
STOP_NUMBER = "462"
STOP_ADDR = "Via Roma, 10123 Torino TO"


# ══════════════════════════════════════════════════════
# Hardware
# ══════════════════════════════════════════════════════
def haptic_pulse():
    try:
        import RPi.GPIO as GPIO

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(HAPTIC_PIN, GPIO.OUT)
        GPIO.output(HAPTIC_PIN, GPIO.HIGH)
        time.sleep(0.06)
        GPIO.output(HAPTIC_PIN, GPIO.LOW)
    except Exception:
        pass


# ══════════════════════════════════════════════════════
# State
# ══════════════════════════════════════════════════════
waiting = False
active_line = None
timer = None
wait_page = None
wait_cv = None
wait_rect = None
pulse_job = None
anim_job = None
info_tick_job = None

# Fake arrivals for the info screen.
# 0 = "Arriving" (bus is at the stop), >0 = minutes until arrival.
# Realistic GTFS-style headways (minutes between buses at this stop, on
# average). Each line is different so the four rows look like four
# different services rather than four copies of the same one. Drawn from
# typical urban Italian bus frequencies.
LINE_BASE_HEADWAY_MIN = {
    "15": 10,   # Line 15: high-frequency
    "33": 14,   # Line 33: medium
    "42": 12,   # Line 42: medium
    "68": 8,    # Line 68: high-frequency
}

# Random per-line starting offset (minutes) so the four rows are not all
# 'X minutes away' at the same wall-clock moment.
def _line_start_offset():
    return random.randint(0, 8)


def _seed_arrivals_for_line(line):
    """Build a realistic 3-slot row for one line.

    Slot 0 = the next bus (the only slot that ever displays green).
    Slot 1 = the bus after that.
    Slot 2 = the bus after that.

    Headways are base + jitter, so consecutive slots are spaced by
    6-14 minutes. Only slot 0 is allowed to ever display green.
    """
    base = LINE_BASE_HEADWAY_MIN.get(line, 12)
    offset = _line_start_offset()
    s0 = max(1, offset + random.randint(0, base + 4))   # next bus: 1-22 min
    s1 = s0 + random.randint(6, 14)                      # +6-14 min
    s2 = s1 + random.randint(6, 14)                      # +6-14 min
    return [s0, s1, s2]


ARRIVALS = {line: _seed_arrivals_for_line(line) for line in BUS_LINES}

# Per-slot tick offset (in whole minutes) so slots don't all change colour
# at the same moment. This is added to the global 60s tick. The value is
# randomised once at startup, in the range [0, 55] seconds.
TICK_OFFSETS = {
    (line, slot): random.randint(0, 55) for line in BUS_LINES for slot in range(3)
}

# When a slot first reaches 0 we record the time. After NOW_RESTART_DELAY
# seconds of sitting at "Now" we re-seed it with a fresh value (the *next*
# bus) so the pill doesn't stay green forever and the info page keeps
# looking like live data instead of freezing once everything has arrived.
SLOT_ZERO_SINCE = {}  # (line, slot) -> epoch seconds when value first hit 0
NOW_RESTART_DELAY_SEC = 60  # 1 minute at "Now" before next-bus re-seed (slot 0 only)

# Per-slot "real-time confirmed" flag. Star ★ on the pill means the bus is
# confirmed running in real time (i.e. matched to a live vehicle position).
# Random 3-4 of the 12 total slots get the star on startup.
REAL_TIME = {(line, slot): False for line in BUS_LINES for slot in range(3)}
_star_slots = random.sample(
    [(line, slot) for line in BUS_LINES for slot in range(3)],
    k=random.randint(3, 4),
)
for key in _star_slots:
    REAL_TIME[key] = True

# Which screen is currently visible: "info" or "request"
current_screen = "info"

# ══════════════════════════════════════════════════════
# MQTT
# ══════════════════════════════════════════════════════
client = mqtt.Client(protocol=mqtt.MQTTv311, userdata={})
mqtt_ready = False
broker_connected = False


def on_connect(client, userdata, flags, rc, properties=None):
    global mqtt_ready, broker_connected
    if rc == 0:
        mqtt_ready = True
        broker_connected = True
        root.after(0, _set_broker_online)
    else:
        mqtt_ready = False
        broker_connected = False
        root.after(0, _set_broker_error)


def on_disconnect(client, userdata, rc, properties=None):
    global mqtt_ready, broker_connected
    mqtt_ready = False
    broker_connected = False
    root.after(0, _set_broker_offline)


def on_message(client, userdata, msg):
    topic = msg.topic.decode() if isinstance(msg.topic, bytes) else msg.topic
    payload = msg.payload.decode() if isinstance(msg.payload, bytes) else msg.payload
    root.after(0, lambda: handle_incoming(topic, payload))


def handle_incoming(topic, payload):
    if not waiting:
        return
    for line in BUS_LINES:
        if topic == accepted_topic(line) and active_line == line:
            root.after(0, show_accepted)
            return


# ══════════════════════════════════════════════════════
# Clock / temperature
# ══════════════════════════════════════════════════════
def update_clock():
    try:
        clock_lbl.config(text=time.strftime("%H:%M"))
        with WEATHER_LOCK:
            temp_str = WEATHER_TEMP
            cond_str = WEATHER_COND
        temp_lbl.config(text=temp_str if temp_str != "--" else "--")
        weather_lbl.config(text=cond_str)
    except Exception:
        pass
    root.after(60000, update_clock)


# ══════════════════════════════════════════════════════
# Root window
# ══════════════════════════════════════════════════════
root = tk.Tk()
root.title("Smart Stop")
root.geometry("800x480")
root.attributes("-fullscreen", True)
root.configure(bg=NAVY)
root.configure(cursor="none")

# Fonts
f_title = tkfont.Font(family="Helvetica", size=20, weight="bold")
f_stopname = tkfont.Font(family="Helvetica", size=14, weight="bold")
f_addr = tkfont.Font(family="Helvetica", size=10)
f_instr = tkfont.Font(family="Helvetica", size=17, weight="bold")
f_sub = tkfont.Font(family="Helvetica", size=10)
f_btn = tkfont.Font(family="Helvetica", size=30, weight="bold")
f_tap = tkfont.Font(family="Helvetica", size=10, weight="bold")
f_big = tkfont.Font(family="Helvetica", size=56, weight="bold")
f_body = tkfont.Font(family="Helvetica", size=13)
f_small = tkfont.Font(family="Helvetica", size=10)
f_stat = tkfont.Font(family="Helvetica", size=10)
f_footer = tkfont.Font(family="Helvetica", size=11, weight="bold")
f_cancel = tkfont.Font(family="Helvetica", size=12, weight="bold")
f_other = tkfont.Font(family="Helvetica", size=11, weight="bold")
# Info screen fonts
f_info_badge = tkfont.Font(family="Helvetica", size=28, weight="bold")
f_info_pill = tkfont.Font(family="Helvetica", size=22, weight="bold")
f_info_pill_sub = tkfont.Font(family="Helvetica", size=8, weight="bold")
f_info_pill_main = tkfont.Font(family="Helvetica", size=15, weight="bold")
f_info_pill_hint = tkfont.Font(family="Helvetica", size=10)

# ══════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════
header = tk.Frame(root, bg=NAVY, height=86)
header.pack(fill="x", side="top")
header.pack_propagate(False)

# ── Left: logo circle + brand ───────────────────────
left_area = tk.Frame(header, bg=NAVY)
left_area.pack(side="left", padx=(18, 14), pady=8)

# White circle with navy border as logo background
logo_cnv = tk.Canvas(left_area, width=52, height=52, bg=NAVY, highlightthickness=0)
logo_cnv.pack(side="left", padx=(0, 10))
logo_cnv.create_oval(1, 1, 51, 51, fill=WHITE, outline=NAVY, width=2)

# Load and scale logo image to fit inside the circle (46x46 inside the border)
logo_img_raw = tk.PhotoImage(
    file=os.path.join(os.path.dirname(__file__), "polito_logo.png")
)
# Scale from 447x447 down to 46x46 (about 9.7x subsample)
logo_scaled = logo_img_raw.subsample(7, 7)
logo_cnv.create_image(26, 26, image=logo_scaled)
logo_cnv.image = logo_scaled  # keep reference

brand = tk.Frame(left_area, bg=NAVY)
brand.pack(side="left")
tk.Label(brand, text="Smart", bg=NAVY, fg=YELLOW, font=f_title, anchor="w").pack(
    anchor="w"
)
tk.Label(brand, text="Stop", bg=NAVY, fg=WHITE, font=f_title, anchor="w").pack(
    anchor="w"
)

# ── Divider ──────────────────────────────────────────
div = tk.Frame(header, bg=YELLOW, width=2)
div.pack(side="left", fill="y", pady=8)
div.pack_propagate(False)

# ── Right: stop info ────────────────────────────────
right_area = tk.Frame(header, bg=NAVY)
right_area.pack(side="right", padx=(10, 18), pady=6, anchor="e", fill="both")

tk.Label(
    right_area,
    text=f"{STOP_NAME}  —  Stop {STOP_NUMBER}",
    bg=NAVY,
    fg=WHITE,
    font=f_stopname,
    anchor="e",
).pack(anchor="e")

tk.Label(
    right_area, text=STOP_ADDR, bg=NAVY, fg="#aaaacc", font=f_addr, anchor="e"
).pack(anchor="e")

status_row = tk.Frame(right_area, bg=NAVY)
status_row.pack(anchor="e", pady=(4, 0))

# ── Broker indicator ───────────────────────────────────
broker_ind = tk.Canvas(status_row, width=10, height=10, bg=NAVY, highlightthickness=0)
broker_ind.create_oval(1, 1, 9, 9, fill="#ff9900", outline="")
broker_ind.pack(side="left", padx=(0, 4))
broker_lbl = tk.Label(status_row, text="Broker", bg=NAVY, fg="#ff9900", font=f_stat)
broker_lbl.pack(side="left", padx=(0, 10))


def _set_broker_online():
    broker_ind.itemconfigure(1, fill="#2ead66")
    broker_lbl.config(text="Broker Online", fg="#2ead66")


def _set_broker_offline():
    broker_ind.itemconfigure(1, fill="#ff9900")
    broker_lbl.config(text="Broker Offline", fg="#ff9900")


def _set_broker_error():
    broker_ind.itemconfigure(1, fill="#cc2222")
    broker_lbl.config(text="Broker Error", fg="#cc2222")


# ── Clock ─────────────────────────────────────────────
tk.Label(
    status_row, text="CLK", bg=NAVY, fg="#ffcc00", font=("Helvetica", 9, "bold")
).pack(side="left")
clock_lbl = tk.Label(status_row, text="--:--", bg=NAVY, fg=WHITE, font=f_stat)
clock_lbl.pack(side="left", padx=(2, 8))

# ── Temperature ─────────────────────────────────────────
tk.Label(
    status_row, text="TMP", bg=NAVY, fg="#ffcc00", font=("Helvetica", 9, "bold")
).pack(side="left")
temp_lbl = tk.Label(status_row, text="--", bg=NAVY, fg=WHITE, font=f_stat)
temp_lbl.pack(side="left", padx=(2, 0))

# ── Weather condition ──────────────────────────────────────
weather_lbl = tk.Label(status_row, text="", bg=NAVY, fg=WHITE, font=f_stat)
weather_lbl.pack(side="left", padx=(4, 0))

# ── Yellow stripe ────────────────────────────────────
stripe = tk.Frame(root, bg=YELLOW, height=3)
stripe.pack(fill="x", side="top")

# ══════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════
main = tk.Frame(root, bg=WHITE)
main.pack(fill="both", expand=True, side="top")

status_lbl = tk.Label(
    main,
    text="",
    bg=WHITE,
    fg=DGREY,
    font=f_stat,
    anchor="w",
    padx=28,
    pady=3,
)
status_lbl.pack(fill="x")


# ══════════════════════════════════════════════════════
# INFO PAGE (default landing screen — read-only bus arrivals)
# ══════════════════════════════════════════════════════
info_page = tk.Frame(main, bg=WHITE)
# Note: not packed here. Packed by show_info() / show_request() at runtime.
info_widgets = {}  # cached references so we can update in-place each tick


def _format_arrival(value):
    """
    Convert minutes-from-now to (bg, fg, primary_label, sub_label) for the pill.
    Wall-clock time is shown in Europe/Rome.

    Color rules (green is reserved for slot 0 only, the 'next bus'):
      0 min   -> green    (bus is at the stop right now)
      1-3 min -> orange   (about to arrive)
      4-7 min -> orange   (coming soon)
      8+ min  -> yellow   (later)
    """
    now = datetime.now(TZ_ROME)
    arrival_dt = now + timedelta(minutes=value)
    if value == 0:
        return ARRIVING_BG, WHITE, "Now", ""
    if value <= 7:
        return SOON_BG, WHITE, arrival_dt.strftime("%H:%M"), f"{value}m"
    return LATER_BG, LATER_FG, arrival_dt.strftime("%H:%M"), ""


def _make_pill(parent, value, slot, line):
    """
    Build one timing pill. Primary label is the wall-clock arrival time (HH:MM
    in Europe/Rome, or "Now" if 0). Sub-label is "Xm" for 1-5 min slots.
    A small ★ in the top-right indicates the bus is real-time confirmed.
    Returns a dict of widgets so the tick timer can re-style in place.
    """
    bg, fg, label, sub = _format_arrival(value)
    has_star = REAL_TIME.get((line, slot), False)

    wrap = tk.Frame(
        parent, bg=bg, cursor="arrow", highlightthickness=1, highlightbackground=bg
    )
    wrap.pack_propagate(False)

    tk.Label(wrap, text=label, bg=bg, fg=fg, font=f_info_pill, anchor="center").pack(
        expand=True, fill="both", padx=4, pady=(2, 0)
    )

    if sub:
        tk.Label(
            wrap, text=sub, bg=bg, fg=fg, font=f_info_pill_sub, anchor="center"
        ).pack(pady=(0, 2))

    # Real-time indicator star (top-right corner)
    if has_star:
        star_lbl = tk.Label(
            wrap,
            text="\u2605",
            bg=bg,
            fg="#fff3b0",
            font=("Helvetica", 10, "bold"),
            anchor="ne",
        )
        star_lbl.place(relx=1.0, x=-3, y=2, anchor="ne")

    return {
        "frame": wrap,
        "bg": bg,
        "fg": fg,
        "has_star": has_star,
        "kind": "arriving" if value <= 3 else ("soon" if value <= 6 else "later"),
    }


def _restyle_pill(pill, value):
    """Re-paint an existing pill in place when the value changes.
    The star (if present) is not removed on restyle — a confirmed bus stays
    confirmed until the kiosk restarts."""
    bg, fg, label, sub = _format_arrival(value)

    pill["frame"].config(bg=bg, highlightbackground=bg)
    # First child = the main label, optional second child = sub-label
    children = pill["frame"].winfo_children()
    if children:
        children[0].config(bg=bg, fg=fg, text=label)
    if sub and len(children) > 1:
        children[1].config(bg=bg, fg=fg, text=sub)
    elif sub and len(children) == 1:
        tk.Label(
            pill["frame"], text=sub, bg=bg, fg=fg, font=f_info_pill_sub, anchor="center"
        ).pack(pady=(0, 2))
    elif not sub and len(children) > 1:
        children[1].destroy()
    pill["bg"] = bg
    pill["fg"] = fg
