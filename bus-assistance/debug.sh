#!/bin/bash
env > /tmp/bus-env.txt
echo "--- xauth:" >> /tmp/bus-env.txt
xauth list >> /tmp/bus-env.txt 2>&1
ls -la /home/s4mpie/.Xauthority >> /tmp/bus-env.txt 2>&1
echo "---" >> /tmp/bus-env.txt
DISPLAY=:0 XAUTHORITY=/home/s4mpie/.Xauthority python3 -c "import tkinter as tk; w=tk.Tk(); print('OK'); w.destroy()" >> /tmp/bus-env.txt 2>&1
