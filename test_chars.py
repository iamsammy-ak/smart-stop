#!/usr/bin/env python3
"""Test individual characters"""

import sys
import time

sys.path.insert(0, "/home/s4mpie2/smartbus")
import bus_display

bus_display.init_lcd()
bus_display.clear_lcd()
bus_display.set_color(255, 255, 0)
time.sleep(0.1)

# Test characters one by one
test_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
bus_display.set_pos(0, 0)
for c in test_chars[:16]:
    bus_display.data(ord(c))
    time.sleep(0.1)

bus_display.set_pos(0, 1)
for c in test_chars[16:32]:
    bus_display.data(ord(c))
    time.sleep(0.1)

print("[DONE] Check LCD - 32 characters shown")
print("Should see: ABCDEFGHIJKLMNOP and KLMNOPQRSTUVWXYZabcdef")
