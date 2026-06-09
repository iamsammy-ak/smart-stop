#!/bin/bash
# Run the bus stop UI from within the user's GUI session

export DISPLAY=:0
export XAUTHORITY=/var/run/lightdm/root/:0

# Wait for X to be ready
sleep 2

# Grant access to all users
xhost +local: 2>/dev/null || true

cd /home/s4mpie/bus-assistance
PYTHONPATH=/home/s4mpie/bus-assistance python3 bus_stop/app.py
