#!/bin/bash
# Set I2C bus speed to 100kHz to fix LCD doubled character issue
# Add to /etc/rc.local or run at startup

# Check current speed
SPEED_FILE="/sys/module/i2c_bcm2708/parameters/baudrate"
if [ -f "$SPEED_FILE" ]; then
    echo 100000 > "$SPEED_FILE"
    echo "I2C speed set to 100kHz"
else
    # Try alternative path for newer kernels
    SPEED_FILE2="/sys/class/i2c-adapter/i2c-1/speed"
    if [ -f "$SPEED_FILE2" ]; then
        echo 100000 > "$SPEED_FILE2"
        echo "I2C speed set to 100kHz via $SPEED_FILE2"
    else
        echo "Could not set I2C speed - driver may not support runtime changes"
        echo "Add 'dtparam=i2c_baudrate=100000' to /boot/config.txt and reboot"
    fi
fi
