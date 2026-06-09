#!/usr/bin/env python3
"""Test script to verify LCD functions"""

import sys

sys.path.insert(0, "/home/s4mpie2/smartbus")
import bus_display

print("Testing LCD functions...")

# Test 1: Show idle
print("[1] Showing IDLE...")
bus_display.show_idle()
print("[1] IDLE shown - check LCD")

# Test 2: Show request
import time

time.sleep(3)
print("[2] Showing REQUEST 15...")
bus_display.show_request("15")
print("[2] REQUEST 15 shown - check LCD")

# Test 3: Back to idle
time.sleep(3)
print("[3] Back to IDLE...")
bus_display.show_idle()
print("[3] DONE - check LCD")
