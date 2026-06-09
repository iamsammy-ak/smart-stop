#!/usr/bin/env python3
"""Publish _mqtt._tcp service via avahi-daemon D-Bus API."""
import socket, struct, os, sys

# Use the busctl shell interface to call avahi D-Bus
def busctl(*args):
    import subprocess
    result = subprocess.run(['busctl'] + list(args), capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

# Get the Server object path
out, err, rc = busctl('call', 'org.freedesktop.Avahi', '/', 
    'org.freedesktop.Avahi.Server', 'GetAPIVersion')
print(f'API version: {out.strip()}')

# Create an EntryGroup
out, err, rc = busctl('call', 'org.freedesktop.Avahi', '/',
    'org.freedesktop.Avahi.Server', 'EntryGroupNew')
entry_group_path = out.strip().strip('"')
print(f'EntryGroup path: {entry_group_path}')

if not entry_group_path:
    print('Failed to create entry group')
    sys.exit(1)

# Build the service: name, type, domain, port
# avahi_entry_group_add_service(group, flags, interface, protocol, 
#   name, type, domain, host, port, txt_records...)
service_name = 'MQTT Broker'
service_type = '_mqtt._tcp'
domain = ''
host = ''
port = 1883

# Add the service — using protocol IPv4 (3), interface (-1 = all), flags (0)
# Format: s q i s s s s s i a(sv)
out, err, rc = busctl('call', 'org.freedesktop.Avahi', entry_group_path,
    'org.freedesktop.Avahi.EntryGroup', 'AddService', 
    '0',  # flags
    '-1', # interface (all interfaces = -1 = 0xffffffff)
    '3',  # protocol IPv4 (0=any, 2=v4, 3=v4-only)
    service_name,
    service_type,
    domain,
    host,      # empty = auto
    str(port), # port as string
    '0',       # number of TXT records
)
print(f'AddService result: rc={rc}, out={out.strip()}')

# Commit the entry group
out, err, rc = busctl('call', 'org.freedesktop.Avahi', entry_group_path,
    'org.freedesktop.Avahi.EntryGroup', 'Commit')
print(f'Commit result: rc={rc}, out={out.strip()}')
print('MQTT service published!')
