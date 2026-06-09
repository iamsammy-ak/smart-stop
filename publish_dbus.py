#!/usr/bin/env python3
import struct, socket, os, sys

def dbus_connect():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect('/var/run/dbus/system_bus_socket')
    return sock

def dbus_call(sock, path, iface, method, *args):
    serial = 1
    # Build message header
    data = bytearray()
    # Simple method call for EntryGroupNew
    # We'll use busctl subprocess instead for simplicity
    return None

# Use busctl subprocess - this works without sudo!
import subprocess

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip(), r.returncode

# Step 1: Get API version
ver, rc = run(['busctl', 'call', 'org.freedesktop.Avahi', '/', 
               'org.freedesktop.Avahi.Server', 'GetAPIVersion'])
print(f'API version: {ver}')

# Step 2: Create EntryGroup - try different approaches
# Method 1: EntryGroupNew (no args)
out, rc = run(['busctl', '--system', 'call', 'org.freedesktop.Avahi', '/',
               'org.freedesktop.Avahi.Server', 'EntryGroupNew'])
print(f'EntryGroupNew: rc={rc} out={out[:100]}')

if rc != 0:
    # Method 2: Try with int32 interface=0, protocol=0
    out, rc = run(['busctl', '--system', 'call', 'org.freedesktop.Avahi', '/',
                   'org.freedesktop.Avahi.Server', 'EntryGroupNew'])
    print(f'EntryGroupNew v2: rc={rc} out={out[:100]}')

if rc == 0:
    path = out.strip().strip('\"')
    print(f'Group path: {path}')
    
    # Step 3: Add service
    out2, rc2 = run(['busctl', '--system', 'call', 'org.freedesktop.Avahi', path,
                     'org.freedesktop.Avahi.EntryGroup', 'AddService',
                     '0',  # flags
                     '0',  # interface (0=first, -1=any)
                     '2',  # protocol (2=IPv4)
                     'MQTT Broker',
                     '_mqtt._tcp',
                     '',
                     '',
                     '1883',
                     '0',  # no TXT records
                    ])
    print(f'AddService: rc={rc2} out={out2[:100]} err={rc2}')
    
    if rc2 == 0:
        # Step 4: Commit
        out3, rc3 = run(['busctl', '--system', 'call', 'org.freedesktop.Avahi', path,
                         'org.freedesktop.Avahi.EntryGroup', 'Commit'])
        print(f'Commit: rc={rc3} out={out3}')
        if rc3 == 0:
            print('SUCCESS: MQTT _mqtt._tcp service published!')
        else:
            print(f'Commit failed: {out3}')
    else:
        print(f'AddService failed: {rc2}')
else:
    print(f'EntryGroupNew failed, rc={rc}')
