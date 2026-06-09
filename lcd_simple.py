#!/usr/bin/env python3
"""Simple LCD test - print just one word"""

import time

from smbus2 import SMBus

LCD = 0x3E
bus = SMBus(1)


def cmd(c):
    bus.write_byte_data(LCD, 0x80, c)
    time.sleep(0.05)


def data(c):
    bus.write_byte_data(LCD, 0x40, c)
    time.sleep(0.1)  # 100ms between chars


def init():
    time.sleep(0.15)
    cmd(0x30)
    time.sleep(0.006)
    cmd(0x30)
    time.sleep(0.002)
    cmd(0x30)
    time.sleep(0.002)
    cmd(0x20)
    time.sleep(0.002)  # 4-bit mode
    cmd(0x28)
    time.sleep(0.002)  # 2 lines
    cmd(0x08)
    time.sleep(0.002)  # display off
    cmd(0x01)
    time.sleep(0.005)  # clear
    cmd(0x06)
    time.sleep(0.002)  # entry mode
    cmd(0x0C)
    time.sleep(0.002)  # display on


def set_pos(col, row):
    cmd(0x80 + col + (0x40 if row else 0))


def write_text(text):
    for c in text:
        data(ord(c))
        time.sleep(0.1)


# Test
init()
cmd(0x01)  # clear
time.sleep(0.05)
set_pos(0, 0)
write_text("HELLO")
print("Check LCD for 'HELLO'")
