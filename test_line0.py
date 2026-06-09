#!/usr/bin/env python3
"""Test line 0 only"""

import sys
import time

sys.path.insert(0, "/home/s4mpie2/smartbus")
import bus_display

bus_display.init_lcd()
bus_display.clear_lcd()
time.sleep(0.2)

# Test line 0 only
print("Testing line 0...")
bus_display.set_pos(0, 0)
time.sleep(0.1)

# Write characters
chars = "ABCDEFGHIJKLMNOP"
print(f"Writing: {chars}")
for c in chars:
    bus_display.data(ord(c))
    time.sleep(0.05)

print("[DONE] Check LCD line 0 - should show: ABCDEFGHIJKLMNOP")
