#!/usr/bin/env python3
"""Test audio playback"""

import subprocess
import time

AUDIO = "plughw:1,0"
AUDIO_DIR = "/home/s4mpie2/smartbus/audio"

print("[1] Testing Italian audio...")
result = subprocess.run(
    ["aplay", "-D", AUDIO, AUDIO_DIR + "/it_line_15.wav"],
    capture_output=True,
    text=True,
)
print("[1] Result:", "OK" if result.returncode == 0 else "FAILED")
print("[1] Stderr:", result.stderr[:100] if result.stderr else "none")

time.sleep(1)

print("[2] Testing English audio...")
result = subprocess.run(
    ["aplay", "-D", AUDIO, AUDIO_DIR + "/en_line_15.wav"],
    capture_output=True,
    text=True,
)
print("[2] Result:", "OK" if result.returncode == 0 else "FAILED")

print("[DONE] Audio tests complete")
