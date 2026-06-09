#!/bin/bash
sleep 4
export DISPLAY=:0
export XAUTHORITY=/home/s4mpie/.Xauthority
export PYTHONPATH=/home/s4mpie/bus-assistance
cd /home/s4mpie/bus-assistance
exec python3 bus_stop/app.py >> /tmp/bus-stop.log 2>&1
