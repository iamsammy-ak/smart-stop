#!/usr/bin/env python3
"""
Smart Stop Bus Assistance System
Raspberry Pi bus stop arrival display with LCD, buzzer alerts,
real-time Italy weather, and MQTT broker connection monitoring.
"""

import json
import logging
import sys
import threading
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

try:
    import RPi.GPIO as GPIO

    GPIO.setmode(GPIO.BCM)
    RPI_AVAILABLE = True
except Exception:
    RPI_AVAILABLE = False
    logger.warning("RPi.GPIO not available — running in simulation mode")


class LCDManager:
    """Manages 16x2 LCD display with bus times, weather, and broker status."""

    ROWS = 2
    COLS = 16

    # Row 1 — scrolling bus info or welcome/weather
    # Row 2 — static info: broker status + time

    def __init__(self, address=0x27, bus=1):
        self._lock = threading.Lock()
        self._running = False
        self._scroll_thread = None
        self._address = address
        self._bus = bus

        if RPI_AVAILABLE:
            try:
                from lcd import drivers

                self._driver = drivers.Lcd16x2(i2c_addr=address, bus=bus)
                logger.info(f"LCD initialized at 0x{address:02X}, bus {bus}")
            except Exception as e:
                logger.warning(f"LCD init failed: {e} — simulation mode")
                self._driver = None
        else:
            self._driver = None

        self._lines = ["", ""]
        self._scroll_pos = 0

    def _write_sim(self, line1, line2):
        print(f"\n{'=' * self.COLS}")
        print(f"{line1:<{self.COLS}}")
        print(f"{line2:<{self.COLS}}")
        print(f"{'=' * self.COLS}")

    def clear(self):
        with self._lock:
            if self._driver:
                self._driver.lcd_clear()
            self._lines = ["", ""]

    def display(self, line1="", line2=""):
        """Display two lines immediately. Text longer than COLS is truncated."""
        with self._lock:
            self._update(line1, line2)
            self._lines = [
                line1[: self.COLS].ljust(self.COLS),
                line2[: self.COLS].ljust(self.COLS),
            ]

    def _update(self, line1, line2):
        """Write to LCD / simulator WITHOUT acquiring the lock.
        Caller must hold _lock or be in a context where deadlock is safe.
        Used by _scroll_worker to avoid deadlock.
        """
        line1 = str(line1)[: self.COLS].ljust(self.COLS)
        line2 = str(line2)[: self.COLS].ljust(self.COLS)
        if self._driver:
            try:
                self._driver.lcd_display_string(line1, 1)
                self._driver.lcd_display_string(line2, 2)
            except Exception as e:
                logger.error(f"LCD write error: {e}")
        else:
            self._write_sim(line1, line2)

    def display_scroll(self, line1="", line2=""):
        """Display line1 scrolling if > COLS chars; line2 is static.
        If already scrolling, restarts with new text only after stop completes.
        """
        with self._lock:
            self._running = False
            if self._scroll_thread and self._scroll_thread.is_alive():
                self._scroll_thread.join(timeout=0.5)

            self._running = True
            self._scroll_line1 = str(line1)
            self._scroll_line2 = str(line2)
            self._scroll_thread = threading.Thread(
                target=self._scroll_worker, daemon=True
            )
            self._scroll_thread.start()

    def _scroll_worker(self):
        """Runs in its own thread. Calls _update directly to avoid deadlock."""
        pad = "  "
        text = self._scroll_line1 + pad
        pos = 0
        while self._running:
            visible = text[pos : pos + self.COLS].ljust(self.COLS)
            line2 = self._scroll_line2[: self.COLS].ljust(self.COLS)
            with self._lock:  # ← safe: we DON'T call self.display()
                self._update(visible, line2)
            pos = (pos + 1) % len(text)
            time.sleep(0.35)

    def stop_scroll(self):
        self._running = False
        if self._scroll_thread:
            self._scroll_thread.join(timeout=1)

    def cleanup(self):
        self.stop_scroll()
        if RPI_AVAILABLE and self._driver:
            try:
                self.clear()
            except Exception:
                pass


class BuzzerController:
    """Controls buzzer for arrival alerts."""

    BUZZER_PIN = 18  # BCM pin 18 (GPIO.18)

    def __init__(self):
        self._pin = self.BUZZER_PIN
        self._is_on = False
        if RPI_AVAILABLE:
            try:
                GPIO.setup(self._pin, GPIO.OUT)
                GPIO.output(self._pin, GPIO.LOW)
                logger.info(f"Buzzer configured on GPIO{self._pin}")
            except Exception as e:
                logger.warning(f"Buzzer setup failed: {e}")

    def beep(self, count=2, duration_ms=300, gap_ms=150):
        """Play a series of short beeps to alert the user."""
        if not RPI_AVAILABLE:
            logger.info(f"[SIM] Buzzer beep {count}x {duration_ms}ms")
            return

        for i in range(count):
            try:
                GPIO.output(self._pin, GPIO.HIGH)
                time.sleep(duration_ms / 1000)
                GPIO.output(self._pin, GPIO.LOW)
                if i < count - 1:
                    time.sleep(gap_ms / 1000)
            except Exception as e:
                logger.error(f"Buzzer error: {e}")

    def alarm(self, duration_s=1.5):
        """Continuous tone for arrival alarm."""
        if not RPI_AVAILABLE:
            logger.info(f"[SIM] Buzzer alarm {duration_s}s")
            return
        end = time.time() + duration_s
        while time.time() < end:
            try:
                GPIO.output(self._pin, GPIO.HIGH)
                time.sleep(0.2)
                GPIO.output(self._pin, GPIO.LOW)
                time.sleep(0.1)
            except Exception:
                break

    def cleanup(self):
        if RPI_AVAILABLE:
            try:
                GPIO.output(self._pin, GPIO.LOW)
            except Exception:
                pass


class WeatherService:
    """Fetches real-time weather for Italy using Open-Meteo (free, no API key)."""

    def __init__(self, latitude=41.9028, longitude=12.4964):  # Rome default
        self._lat = latitude
        self._lon = longitude
        self._cache = None
        self._cache_time = 0
        self._cache_ttl = 600  # 10 minutes
        self._last_update = None

    def fetch(self):
        """Get current weather from Open-Meteo."""
        if self._cache and (time.time() - self._cache_time) < self._cache_ttl:
            return self._cache

        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={self._lat}&longitude={self._lon}"
            f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
            f"&timezone=Europe/Rome"
        )

        try:
            import urllib.request

            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            current = data.get("current", {})
            self._cache = {
                "temp": current.get("temperature_2m", 0),
                "humidity": current.get("relative_humidity_2m", 0),
                "weather_code": current.get("weather_code", 0),
                "wind_speed": current.get("wind_speed_10m", 0),
            }
            self._cache_time = time.time()
            self._last_update = datetime.now().strftime("%H:%M")
            logger.info(f"Weather updated: {self._cache['temp']}°C")
            return self._cache
        except Exception as e:
            logger.error(f"Weather fetch failed: {e}")
            return self._cache or {
                "temp": 0,
                "humidity": 0,
                "weather_code": 0,
                "wind_speed": 0,
            }

    @staticmethod
    def weather_description(code: int) -> str:
        """Map WMO weather codes to descriptions."""
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
        return codes.get(code, "Unknown")

    def format_display(self) -> str:
        """Short string for LCD: T°C condition."""
        w = self.fetch()
        cond = self.weather_description(w.get("weather_code", 0))
        temp = w.get("temp", 0)
        return f"{temp:.0f}C {cond}"


class MQTTManager:
    """Manages MQTT connection to broker with live status."""

    def __init__(
        self,
        broker_host="localhost",
        broker_port=1883,
        topic="bus/arrivals",
        client_id="smartstop-01",
    ):
        self._broker_host = broker_host
        self._broker_port = broker_port
        self._topic = topic
        self._client_id = client_id
        self._status = "DISCONNECTED"
        self._status_lock = threading.Lock()
        self._client = None
        self._on_message_callback = None
        self._thread = None
        self._running = False
        self._should_reconnect = True  # used by on_disconnect to signal reconnect

        self._connect()

    @property
    def status(self) -> str:
        with self._status_lock:
            return self._status

    def _set_status(self, s):
        with self._status_lock:
            self._status = s
        logger.info(f"MQTT status: {s}")

    def _format_status(self) -> str:
        s = self.status
        if s == "CONNECTED":
            return "Broker: ON-LINE  "
        elif s == "CONNECTING":
            return "Broker: STARTING "
        elif s == "ERROR":
            return "Broker: ERROR    "
        else:
            return "Broker: OFF-LINE "

    def _connect(self):
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._should_reconnect = True
        self._thread = threading.Thread(target=self._connect_loop, daemon=True)
        self._thread.start()

    def _connect_loop(self):
        while self._running and self._should_reconnect:
            self._set_status("CONNECTING")
            try:
                import paho.mqtt.client as mqtt

                def on_connect(c, userdata, flags, reason_code, properties=None):
                    if reason_code.is_failure:
                        logger.warning(f"MQTT connection failed: {reason_code}")
                        self._set_status("ERROR")
                    else:
                        self._set_status("CONNECTED")
                        c.subscribe(self._topic)
                        logger.info(f"Subscribed to {self._topic}")

                def on_disconnect(c, userdata, reason_code, properties=None):
                    self._set_status("DISCONNECTED")
                    logger.warning(f"MQTT disconnected: {reason_code}")

                def on_message(c, userdata, msg):
                    if self._on_message_callback:
                        self._on_message_callback(msg.payload.decode())

                self._client = mqtt.Client(
                    client_id=self._client_id,
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                )
                self._client.on_connect = on_connect
                self._client.on_disconnect = on_disconnect
                self._client.on_message = on_message
                self._client.connect(self._broker_host, self._broker_port, keepalive=30)
                self._client.loop_start()

                # Wait for disconnect or shutdown signal
                while self._running and self._should_reconnect:
                    time.sleep(2)

            except ImportError:
                logger.warning("paho-mqtt not installed")
                self._set_status("ERROR")
                time.sleep(30)
            except Exception as e:
                logger.error(f"MQTT error: {e}")
                self._set_status("ERROR")
                time.sleep(10)

    def set_message_callback(self, cb):
        self._on_message_callback = cb

    def publish(self, payload, topic=None):
        if self._client and self.status == "CONNECTED":
            try:
                self._client.publish(topic or self._topic, payload)
            except Exception as e:
                logger.error(f"MQTT publish error: {e}")

    def stop(self):
        self._should_reconnect = False
        self._running = False
        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass


class BusArrivalMonitor:
    """Simulated bus arrival monitor with MQTT integration."""

    def __init__(
        self,
        mqtt: MQTTManager,
        buzzer: BuzzerController,
        city_lat=41.9028,
        city_lon=12.4964,
    ):
        self._mqtt = mqtt
        self._buzzer = buzzer
        self._weather = WeatherService(city_lat, city_lon)
        self._announced = set()  # already buzzed for these arrival IDs
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._mqtt.set_message_callback(self._on_arrival)
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _on_arrival(self, payload):
        """Handle incoming arrival data from MQTT broker."""
        try:
            data = json.loads(payload)
        except Exception:
            logger.warning(f"Invalid MQTT payload: {payload}")
            return

        line = data.get("line", "?")
        dest = data.get("destination", "")
        mins = data.get("minutes", 0)

        # Alert when arrival is imminent
        if mins <= 2 and data.get("id") not in self._announced:
            self._announced.add(data.get("id"))
            self._buzzer.alarm(1.5)
            logger.info(f"ALERT: {line} to {dest} in {mins} min")

    def _poll_loop(self):
        while self._running:
            try:
                # Refresh weather every cycle
                w = self._weather.fetch()
                logger.debug(f"Live data: {w}")
                time.sleep(30)
            except Exception as e:
                logger.error(f"Poll error: {e}")
                time.sleep(30)


class UIController:
    """Main UI loop — cycles LCD views with broker + weather info."""

    def __init__(
        self,
        lcd: LCDManager,
        mqtt: MQTTManager,
        weather: WeatherService,
        buzzer: BuzzerController,
        city_name="Roma",
    ):
        self._lcd = lcd
        self._mqtt = mqtt
        self._weather = weather
        self._buzzer = buzzer
        self._city_name = city_name
        self._running = False
        self._thread = None
        self._mode = "welcome"
        self._mode_lock = threading.Lock()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._ui_loop, daemon=True)
        self._thread.start()

    def _get_broker_status(self) -> str:
        """Broker status for row 2: ● ONLINE / ○ STARTING / ✕ OFFLINE."""
        s = self._mqtt.status
        if s == "CONNECTED":
            return "Broker: ON-LINE  "
        elif s == "CONNECTING":
            return "Broker: STARTING "
        elif s == "ERROR":
            return "Broker: ERROR    "
        else:
            return "Broker: OFF-LINE "

    def _ui_loop(self):
        """Cycle between: welcome → weather → time+broker."""
        cycle = 0
        while self._running:
            broker_bar = self._get_broker_status()
            now_str = datetime.now().strftime("%H:%M")

            if cycle % 3 == 0:
                # Welcome view
                self._lcd.display_scroll(
                    f"Smart Stop Bus", f"{now_str} {self._city_name}"
                )
                time.sleep(8)

            elif cycle % 3 == 1:
                # Weather view
                weather_str = self._weather.format_display()
                self._lcd.display(
                    f"Weather {self._city_name}", f"{weather_str} {now_str}"
                )
                time.sleep(6)

            else:
                # Status + time view
                self._lcd.display(f"Smart Stop Bus", f"{broker_bar} {now_str}")
                time.sleep(4)

            cycle += 1

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)


def main():
    from config import (
        BUZZER_PIN,
        CITY_NAME,
        LCD_ADDRESS,
        LCD_BUS,
        MQTT_BROKER,
        MQTT_PORT,
        MQTT_TOPIC,
        WEATHER_LAT,
        WEATHER_LON,
    )

    print("=" * 40)
    print("  Smart Stop Bus Assistance System")
    print("=" * 40)
    print()

    # Initialize components
    lcd = LCDManager(address=LCD_ADDRESS, bus=LCD_BUS)

    # Override buzzer pin from config
    BuzzerController.BUZZER_PIN = BUZZER_PIN
    buzzer = BuzzerController()

    weather = WeatherService(latitude=WEATHER_LAT, longitude=WEATHER_LON)

    mqtt = MQTTManager(broker_host=MQTT_BROKER, broker_port=MQTT_PORT, topic=MQTT_TOPIC)

    # Show initial splash
    lcd.display("Smart Stop Bus", "System loading...")
    time.sleep(2)

    # Start services
    monitor = BusArrivalMonitor(
        mqtt=mqtt, buzzer=buzzer, city_lat=WEATHER_LAT, city_lon=WEATHER_LON
    )
    monitor.start()

    ui = UIController(
        lcd=lcd, mqtt=mqtt, weather=weather, buzzer=buzzer, city_name=CITY_NAME
    )
    ui.start()

    logger.info("System running — press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
            # Live broker status poll (visible in logs)
            if mqtt.status == "CONNECTED":
                logger.debug(f"Broker: ONLINE | Weather: {weather.fetch()}")
            else:
                logger.info(f"Broker: {mqtt.status}")
    except KeyboardInterrupt:
        logger.info("Shutdown requested...")
    finally:
        ui.stop()
        mqtt.stop()
        buzzer.cleanup()
        lcd.cleanup()
        if RPI_AVAILABLE:
            GPIO.cleanup()
        logger.info("System stopped cleanly.")
