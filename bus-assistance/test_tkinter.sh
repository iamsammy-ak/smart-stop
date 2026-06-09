#!/bin/bash
echo "Starting at $(date)" >> /tmp/bus-stop.log
echo "DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY" >> /tmp/bus-stop.log
ls -la $XAUTHORITY >> /tmp/bus-stop.log
/usr/bin/python3 /home/s4mpie/bus-assistance/bus_stop/app.py >> /tmp/bus-stop.log 2>&1
