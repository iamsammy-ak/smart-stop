#!/usr/bin/env python3
"""Test both lines together"""

import sys
import time

sys.path.insert(0, "/home/s4mpie2/smartbus")
import bus_display

bus_display.init_lcd()
bus_display.clear_lcd()
bus_display.set_color(255, 255, 0)
time.sleep(0.1)

# Line 0
print("Writing line 0...")
bus_display.set_pos(0, 0)
time.sleep(0.05)
for c in "Smart Stop Ready":
    bus_display.data(ord(c))
    time.sleep(0.05)

# Line 1
print("Writing line 1...")
bus_display.set_pos(0, 1)
time.sleep(0.05)
for c in "Yellow team ":
    bus_display.data(ord(c))
    time.sleep(0.05)

# Heart
print("Creating heart...")
bus_display.cmd(0x48)  # CGRAM position 1 (0x40 + 8)
time.sleep(0.02)
for r in [0, 10, 31, 31, 14, 4, 0, 0]:
    bus_display.data(r)
    time.sleep(0.02)
bus_display.set_pos(13, 1)  # Position 13 on line 1
time.sleep(0.02)
bus_display.data(0x01)  # Heart character

print("[DONE] Check LCD")
