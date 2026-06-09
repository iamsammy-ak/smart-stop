"""
Configuration for Smart Stop Bus Assistance System.
Adjust values for your hardware and location.
"""

# ── LCD Display (I2C 16x2) ──────────────────────────────────────────
LCD_ADDRESS = 0x27  # I2C address of the LCD backpack (check with: i2cdetect -y 1)
LCD_BUS = 1  # I2C bus number (0 on older Pi, 1 on Pi 2/3/4)

# ── Buzzer ────────────────────────────────────────────────────────
BUZZER_PIN = 18  # BCM GPIO pin connected to the buzzer signal

# ── MQTT Broker ───────────────────────────────────────────────────
MQTT_BROKER = "10.39.44.121"  # Broker hostname / IP address (Stop Pi)
MQTT_PORT = 1883  # Broker port
MQTT_TOPIC = "bus/arrivals"  # Topic to subscribe to for bus arrival data

# ── Italy City Coordinates (change for your location) ──────────────
# Cities available in Open-Meteo (free, no API key needed):
#   Rome     : 41.9028, 12.4964
#   Milan    : 45.4642,  9.1900
#   Naples   : 40.8518, 14.2681
#   Florence : 43.7696, 11.2558
#   Turin    : 45.0703,  7.6869
#   Bologna  : 44.4949, 11.3426
#   Palermo  : 38.1157, 13.3615
#   Genoa    : 44.4056,  8.9463

CITY_NAME = "Roma"
WEATHER_LAT = 41.9028
WEATHER_LON = 12.4964

# ── Weather refresh interval (seconds) ───────────────────────────
WEATHER_TTL = 600  # 10 minutes — Open-Meteo free tier
