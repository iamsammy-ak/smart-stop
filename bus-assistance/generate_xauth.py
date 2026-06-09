#!/usr/bin/env python3
"""Generate X11 trusted cookie for display :0 using Python's xlib."""
import os, struct, socket

# Read the existing cookie from LightDM's auth file
src = "/var/run/lightdm/root/:0"
try:
    with open(src, 'rb') as f:
        raw = f.read()
    print(f"Read {len(raw)} bytes from {src}")
except Exception as e:
    print(f"Cannot read {src}: {e}")
    # Fall back: try to generate a new cookie
    raw = None

# Write to user's Xauthority
dst = "/home/s4mpie/.Xauthority"
try:
    if raw:
        with open(dst, 'wb') as f:
            f.write(raw)
        os.chmod(dst, 0o600)
        os.chown(dst, 1000, 1000)
        print(f"Wrote cookie to {dst}")
except Exception as e:
    print(f"Cannot write {dst}: {e}")
