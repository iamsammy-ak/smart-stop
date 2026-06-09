#!/usr/bin/env python3
"""Test LCD character display and heart"""

import sys
import time

sys.path.insert(0, "/home/s4mpie2/smartbus")
import bus_display

print("Testing LCD...")

# Clear and init
bus_display.init_lcd()
bus_display.clear_lcd()
bus_display.set_color(255, 255, 0)
time.sleep(0.1)

# Test line 0
print("[1] Writing 'Smart Stop Ready' on line 0")
bus_display.set_pos(0, 0)
bus_display.write_text("Smart Stop Ready")

# Test line 1 with heart
print("[2] Writing 'Yellow team' + heart on line 1")
bus_display.set_pos(0, 1)
bus_display.write_text("Yellow team ")

# Create heart in position 1 and display it
print("[3] Creating heart character")
bus_display.cmd(0x40)  # CGRAM address for char 1
for r in [0, 10, 31, 31, 14, 4, 0, 0]:
    bus_display.data(r)
bus_display.cmd(0x80)  # Back to DDRAM
bus_display.data(0x01)  # Display char 1 (heart)

print("[DONE] Check LCD")
