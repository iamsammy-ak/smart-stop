#!/usr/bin/env python3
import subprocess, sys

def busctl(*args):
    r = subprocess.run(['busctl'] + list(args), capture_output=True, text=True)
    return r.stdout, r.stderr, r.returncode

# Try the raw dbus-send instead
print('=== dbus-send approach ===')
out, err, rc = busctl('call', 'org.freedesktop.Avahi', '/', 
    'org.freedesktop.Avahi.Server', 'GetAPIVersion')
print(f'version: {out}')

# Get server entry group with correct interface number
out, err, rc = busctl('call', 'org.freedesktop.Avahi', '/',
    'org.freedesktop.Avahi.Server', 'EntryGroupNew')
print(f'group: {out} {err}')

# Try different protocol values (2 = IPv4, 3 = IPv4 only? actually 0=any, 1=v6, 2=v6-only, 3=v4?)
# Let's try interface=0 (first interface), protocol=2 (IPv4)
out, err, rc = busctl('call', 'org.freedesktop.Avahi', '/Client0/EntryGroup1',
    'org.freedesktop.Avahi.EntryGroup', 'AddService',
    '0',    # flags
    '0',    # interface (0 = first interface, -1 = all = 0xffffffff)
    '2',    # protocol (2 = IPv4)
    'MQTT Broker',
    '_mqtt._tcp',
    '',
    '',     # host (empty)
    '1883', # port
    '0'     # txt records count
)
print(f'AddService: rc={rc}, out={out}, err={err}')

if rc == 0:
    out, err, rc = busctl('call', 'org.freedesktop.Avahi', '/Client0/EntryGroup1',
        'org.freedesktop.Avahi.EntryGroup', 'Commit')
    print(f'Commit: rc={rc}, out={out}, err={err}')
else:
    # Try with protocol=0 (ANY)
    out, err, rc = busctl('call', 'org.freedesktop.Avahi', '/Client0/EntryGroup1',
        'org.freedesktop.Avahi.EntryGroup', 'AddService',
        '0', '0', '0', 'MQTT Broker', '_mqtt._tcp', '', '', '1883', '0')
    print(f'AddService proto=0: rc={rc}, out={out}, err={err}')
    if rc == 0:
        out, err, rc = busctl('call', 'org.freedesktop.Avahi', '/Client0/EntryGroup1',
            'org.freedesktop.Avahi.EntryGroup', 'Commit')
        print(f'Commit: rc={rc}, out={out}')
