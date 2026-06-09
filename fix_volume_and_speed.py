path = "/home/s4mpie2/smartbus/bus_display.py"
with open(path) as f:
    src = f.read()

# 1. Add INIT_VOLUME_PCT to config
old_cfg = """AUDIO_DEV = "plughw:1,0"
AUDIO_DIR = "/home/s4mpie2/smartbus/audio"
STOP_NAME = "Piazza Castello"
TIMER_SEC = 30"""
new_cfg = """AUDIO_DEV = "plughw:1,0"
AUDIO_DIR = "/home/s4mpie2/smartbus/audio"
STOP_NAME = "Piazza Castello"
TIMER_SEC = 30
INIT_VOLUME_PCT = 60  # 0-100, set on the USB speaker at startup"""
assert old_cfg in src
src = src.replace(old_cfg, new_cfg, 1)

# 2. Add a set_volume() function right BEFORE _audio_worker
old_worker_start = """# ── Audio ────────────────────────────────────────────────────────


def _audio_worker(line):"""
new_worker_start = '''# ── Audio ────────────────────────────────────────────────────────


def set_volume(percent):
    """Set USB speaker volume via ALSA. percent: 0-100. Silently no-op on failure."""
    try:
        import subprocess
        # Card 1 is the USB speaker (AUDIO_DEV = plughw:1,0); its mixer is just "PCM"
        result = subprocess.run(
            ["amixer", "-c", "1", "set", "PCM", f"{int(percent)}%"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print(f"[AUDIO] Volume set to {percent}% (card 1 PCM)")
        else:
            print(f"[AUDIO] Volume set failed: {result.stderr.strip() or result.stdout.strip()}")
    except FileNotFoundError:
        print("[AUDIO] amixer not found, cannot set volume")
    except Exception as e:
        print(f"[AUDIO] Volume set error: {e}")


def _audio_worker(line):'''
assert old_worker_start in src
src = src.replace(old_worker_start, new_worker_start, 1)

# 3. Reorder handle_request: audio first, then LCD
old_handle = """def handle_request(line):
    if not mqtt_ready:
        return
    print(f"[REQUEST] Line {line}")
    cancel_timer()
    stop_audio()
    show_request(line)
    time.sleep(0.5)
    play_audio(line)
    start_timer()"""
new_handle = """def handle_request(line):
    if not mqtt_ready:
        return
    print(f"[REQUEST] Line {line}")
    cancel_timer()
    stop_audio()
    # Start audio FIRST so it begins playing immediately,
    # in parallel with the LCD update (which can take ~2s).
    play_audio(line)
    show_request(line)
    start_timer()"""
assert old_handle in src
src = src.replace(old_handle, new_handle, 1)

# 4. Call set_volume at startup, after init_lcd
old_main = """    # 2. Initialize LCD immediately (shows nothing until first update)
    init_lcd()

    # 3. Show orange connecting screen
    show_connecting()"""
new_main = """    # 2. Initialize LCD immediately (shows nothing until first update)
    init_lcd()

    # 2b. Set USB speaker volume once at startup
    set_volume(INIT_VOLUME_PCT)

    # 3. Show orange connecting screen
    show_connecting()"""
assert old_main in src
src = src.replace(old_main, new_main, 1)

with open(path, "w") as f:
    f.write(src)
print("PATCHED OK")
