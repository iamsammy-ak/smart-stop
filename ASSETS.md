# Binary assets

This directory contains image and audio assets used by the running
applications. They are **not** tracked in git because the GitHub
content API used to push source files only accepts UTF-8 text.

## Stop Pi — `bus-assistance/bus_stop/polito_logo.png`

The Politecnico di Torino crest (≈ 447 × 447 px) shown in the
top-left of the kiosk home screen. Replace with a copy of the
project's logo before deploying.

To add the asset on a Pi after pulling this repo:

```bash
# From your local machine
scp polito_logo.png s4mpie@<stop-pi>:/home/s4mpie/bus-assistance/bus_stop/
```

If the file is missing, the Stop Pi app will fail at startup with
`FileNotFoundError: polito_logo.png` — that is the only missing
binary dependency.

## Bus Pi — `audio/it_line_<N>.wav`, `audio/en_line_<N>.wav`

WAV files used by the bus Pi's `bus_display.py` to announce the
bus line in Italian and English. One pair per bus line
(`{15, 68, 42, 33}`). Recommended format: 24 kHz, 16-bit, mono,
1-3 seconds long. Generate with `espeak`:

```bash
espeak -w it_line_15.wav "Linea quindici"   -v it -s 130
espeak -w en_line_15.wav "Line fifteen"     -v en -s 130
```

On the Bus Pi, drop them into `/home/s4mpie2/smartbus/audio/`
(matching the `AUDIO_DIR` in `bus_display.py`).
