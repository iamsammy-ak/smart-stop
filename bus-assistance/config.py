"""
Bus Assistance System — Configuration
Edit this file to change bus lines and hardware settings.
"""

# ── MQTT Broker ──────────────────────────────────────────────────
# The mosquitto broker runs on the STOP Pi (this Pi). The Bus Pi
# connects *to* us. Using a hostname via mDNS (Avahi) means we don't
# break when DHCP gives us a new IP.
#     getent hosts smartstop-pi.local
#     ping smartstop-pi.local
BROKER_HOST = "smartstop-pi.local"
BROKER_PORT = 1883

# ── MQTT Topics ─────────────────────────────────────────────────
TOPIC_PREFIX = "bus-assistance"


def request_topic(line):
    """Topic a bus stop publishes to when requesting assistance."""
    return f"{TOPIC_PREFIX}/{line}/request"


def accepted_topic(line):
    """Topic the bus Pi publishes back when driver accepts the request."""
    return f"{TOPIC_PREFIX}/{line}/accepted"


def cancelled_topic(line):
    """Topic published when user cancels a request."""
    return f"{TOPIC_PREFIX}/{line}/cancelled"


# ── Bus Lines ────────────────────────────────────────────────────
# Edit this list to show the actual bus lines at your stop.
# Designed to fit nicely in a 2-column grid on the 7" 800x480 screen.
# NOTE: these must match the audio files on the Bus Pi in
#       /home/s4mpie2/smartbus/audio/{it,en}_line_<N>.wav
BUS_LINES = [
    "15",  # Line 15 — blue
    "68",  # Line 68 — pink
    "42",  # Line 42 — purple
    "33",  # Line 33 — black
]

# Line badge color for the info screen and the request buttons.
LINE_COLORS = {
    "15": "#0077cc",  # blue
    "68": "#d6336c",  # pink
    "42": "#5b3a8c",  # purple
    "33": "#1a1a1a",  # black
}

# ── Timing ──────────────────────────────────────────────────────
REQUEST_TIMEOUT_SEC = 30  # Auto-reset after this long with no response

# ── Hardware Pin ────────────────────────────────────────────────
HAPTIC_PIN = 12  # BCM GPIO12 — vibration motor (optional, set to None to disable)
