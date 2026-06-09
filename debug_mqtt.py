#!/usr/bin/env python3
"""Debug test - check MQTT subscription and message handling"""

import time

import paho.mqtt.client as mqtt


def on_connect(c, u, f, rc, p=None):
    print(f"[DEBUG] MQTT Connected! rc={rc}")
    c.subscribe("bus-assistance/+/request")


def on_message(c, u, msg, p=None):
    topic = msg.topic
    print(f"[DEBUG] MESSAGE: {topic}")


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("[DEBUG] Connecting to 10.39.44.121:1883...")
client.connect("10.39.44.121", 1883, keepalive=10)
client.loop_start()
print("[DEBUG] Waiting for messages (30 seconds)...")
for i in range(30):
    time.sleep(1)
    print(f"[DEBUG] ...{30 - i}s")
client.loop_stop()
print("[DEBUG] Done")
