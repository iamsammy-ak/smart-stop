#!/usr/bin/env python3
"""LCD Test Script - Test different timing approaches"""

import time

from smbus2 import SMBus

LCD = 0x3E  # LCD I2C address
bus = SMBus(1)


def cmd(c):
    bus.write_byte_data(LCD, 0x80, c)
    time.sleep(0.001)


def data(c):
    bus.write_byte_data(LCD, 0x40, c)
    time.sleep(0.001)


def init():
    time.sleep(0.15)
    cmd(0x30)
    time.sleep(0.006)
    cmd(0x30)
    time.sleep(0.002)
    cmd(0x30)
    time.sleep(0.002)
    cmd(0x20)
    time.sleep(0.002)
    cmd(0x28)
    time.sleep(0.002)
    cmd(0x08)
    time.sleep(0.002)
    cmd(0x01)
    time.sleep(0.003)
    cmd(0x06)
    time.sleep(0.002)
    cmd(0x0C)
    time.sleep(0.002)


def clear():
    cmd(0x01)
    time.sleep(0.005)


def set_pos(col, row):
    if row == 0:
        cmd(0x80 + col)
    else:
        cmd(0x80 + 0x40 + col)


def write_text(text, char_delay=0.02):
    for c in text:
        if c == " ":
            data(0x20)
        else:
            data(ord(c))
        time.sleep(char_delay)


# Test 1: Very slow character delay
print("[1] Testing char_delay=0.05")
init()
clear()
time.sleep(0.05)
set_pos(0, 0)
write_text("HELLO", char_delay=0.05)
print("[1] Done")
