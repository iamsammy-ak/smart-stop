#!/usr/bin/env python3
import os, shutil
src = "/var/run/lightdm/root/:0"
dst = "/home/s4mpie/.Xauthority"
try:
    shutil.copy2(src, dst)
    os.chmod(dst, 0o600)
    os.chown(dst, 1000, 1000)  # uid/gid for s4mpie
    print("OK")
except Exception as e:
    print(f"FAIL: {e}", file=__import__('sys').stderr)
