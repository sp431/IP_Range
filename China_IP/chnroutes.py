#!/usr/bin/env python3
"""
chnroutes.py - Generate China IP routes for VPN split tunneling

This script fetches China IP allocation data from APNIC and generates
routing rules for various platforms to bypass VPN for China IPs.

Python 3 rewrite of the original chnroutes.py (Python 2).

Usage:
    python3 chnroutes.py -p <platform> [-m <metric>]

Platforms: openvpn, linux, mac, win, android, cidr
"""

import re
import urllib.request
import sys
import argparse
import math
import textwrap


def fetch_ip_data():
    """Fetch China IPv4 allocation data from APNIC."""
    print("Fetching data from apnic.net, it might take a few minutes, please wait...")
    url = r'https://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    data = urllib.request.urlopen(req, timeout=120).read().decode('utf-8')

    cnregex = re.compile(r'apnic\|cn\|ipv4\|[0-9\.]+\|[0-9]+\|[0-9]+\|a.*', re.IGNORECASE)
    cndata = cnregex.findall(data)

    results = []

    for item in cndata:
        unit_items = item.split('|')
        starting_ip = unit_items[3]
        num_ip = int(unit_items[4])

        # Calculate netmask
        imask = 0xffffffff ^ (num_ip - 1)
        imask = hex(imask)[2:]
        mask = [0] * 4
        mask[0] = imask[0:2]
        mask[1] = imask[2:4]
        mask[2] = imask[4:6]
        mask[3] = imask[6:8]

        mask = [int(i, 16) for i in mask]
        mask_str = "%d.%d.%d.%d" % tuple(mask)

        # CIDR prefix length
        mask2 = 32 - int(math.log(num_ip, 2))

        results.append((starting_ip, mask_str, mask2))

    return results


def generate_cidr():
    """Generate a simple CIDR format file (IP/prefix)."""
    results = fetch_ip_data()
    rfile = open('China_IP.txt', 'w')
    for ip, _, mask in results:
        rfile.write("%s/%s\n" % (ip, mask))
    rfile.close()
    print("Generated China_IP.txt with %d CIDR entries." % len(results))


def generate_ovpn(metric):
    """Generate OpenVPN route directives."""
    results = fetch_ip_data()
    rfile = open('routes.txt', 'w')
    for ip, mask, _ in results:
        route_item = "route %s %s net_gateway %d\n" % (ip, mask, metric)
        rfile.write(route_item)
    rfile.close()
    print("Usage: Append the content of the newly created routes.txt to your openvpn config file,"
          " and also add 'max-routes %d', which takes a line, to the head of the file." % (len(results) + 20))


def generate_linux(metric):
    """Generate Linux ip-up/ip-down scripts for PPTP."""
    results = fetch_ip_data()
    upscript_header = textwrap.dedent("""\
    #!/bin/bash
    export PATH="/bin:/sbin:/usr/sbin:/usr/bin"

    OLDGW=`ip route show | grep '^default' | sed -e 's/default via \\([^ ]*\\).*/\\1/'`

    if [ $OLDGW == '' ]; then
        exit 0
    fi

    if [ ! -e /tmp/vpn_oldgw ]; then
        echo $OLDGW > /tmp/vpn_oldgw
    fi

    """)

    downscript_header = textwrap.dedent("""\
    #!/bin/bash
    export PATH="/bin:/sbin:/usr/sbin:/usr/bin"

    OLDGW=`cat /tmp/vpn_oldgw`

    """)

    upfile = open('ip-pre-up', 'w')
    downfile = open('ip-down', 'w')

    upfile.write(upscript_header)
    upfile.write('\n')
    downfile.write(downscript_header)
    downfile.write('\n')

    for ip, mask, _ in results:
        upfile.write('route add -net %s netmask %s gw $OLDGW\n' % (ip, mask))
        downfile.write('route del -net %s netmask %s\n' % (ip, mask))

    downfile.write('rm /tmp/vpn_oldgw\n')
    upfile.close()
    downfile.close()

    print("For pptp only, please copy the file ip-pre-up to the folder /etc/ppp,"
          "and copy the file ip-down to the folder /etc/ppp/ip-down.d.")


def generate_mac(metric):
    """Generate Mac OS X ip-up/ip-down scripts for PPTP."""
    results = fetch_ip_data()

    upscript_header = textwrap.dedent("""\
    #!/bin/sh
    export PATH="/bin:/sbin:/usr/sbin:/usr/bin"

    OLDGW=`netstat -nr | grep '^default' | grep -v 'ppp' | sed 's/default *\\([0-9\\.]*\\) .*/\\1/' | awk '{if($1){print $1}}'`

    if [ ! -e /tmp/pptp_oldgw ]; then
        echo "${OLDGW}" > /tmp/pptp_oldgw
    fi

    dscacheutil -flushcache

    route add 10.0.0.0/8 "${OLDGW}"
    route add 172.16.0.0/12 "${OLDGW}"
    route add 192.168.0.0/16 "${OLDGW}"
    """)

    downscript_header = textwrap.dedent("""\
    #!/bin/sh
    export PATH="/bin:/sbin:/usr/sbin:/usr/bin"

    if [ ! -e /tmp/pptp_oldgw ]; then
            exit 0
    fi

    OLDGW=`cat /tmp/pptp_oldgw`

    route delete 10.0.0.0/8 "${OLDGW}"
    route delete 172.16.0.0/12 "${OLDGW}"
    route delete 192.168.0.0/16 "${OLDGW}"
    """)

    upfile = open('ip-up', 'w')
    downfile = open('ip-down', 'w')

    upfile.write(upscript_header)
    upfile.write('\n')
    downfile.write(downscript_header)
    downfile.write('\n')

    for ip, _, mask in results:
        upfile.write('route add %s/%s "${OLDGW}"\n' % (ip, mask))
        downfile.write('route delete %s/%s ${OLDGW}\n' % (ip, mask))

    downfile.write('\n\nrm /tmp/pptp_oldgw\n')
    upfile.close()
    downfile.close()

    print("For pptp on mac only, please copy ip-up and ip-down to the /etc/ppp folder,"
          " don't forget to make them executable with the chmod command.")


def generate_win(metric):
    """Generate Windows vpnup.bat/vpndown.bat for PPTP."""
    results = fetch_ip_data()

    upscript_header = textwrap.dedent("""@echo off
    for /F "tokens=3" %%* in ('route print ^| findstr "\\<0.0.0.0\\>"') do set "gw=%%*"

    """)

    upfile = open('vpnup.bat', 'w')
    downfile = open('vpndown.bat', 'w')

    upfile.write(upscript_header)
    upfile.write('\n')
    upfile.write('ipconfig /flushdns\n\n')

    downfile.write("@echo off")
    downfile.write('\n')

    for ip, mask, _ in results:
        upfile.write('route add %s mask %s %s metric %d\n' % (ip, mask, "%gw%", metric))
        downfile.write('route delete %s\n' % (ip))

    upfile.close()
    downfile.close()

    print("For pptp on windows only, run vpnup.bat before dialing to vpn,"
          " and run vpndown.bat after disconnected from the vpn.")


def generate_android(metric):
    """Generate Android vpnup.sh/vpndown.sh for PPTP."""
    results = fetch_ip_data()

    upscript_header = textwrap.dedent("""\
    #!/bin/sh
    alias netstat='/system/xbin/busybox netstat'
    alias grep='/system/xbin/busybox grep'
    alias awk='/system/xbin/busybox awk'
    alias route='/system/xbin/busybox route'

    OLDGW=`netstat -rn | grep ^0\\.0\\.0\\.0 | awk '{print $2}'`

    """)

    downscript_header = textwrap.dedent("""\
    #!/bin/sh
    alias route='/system/xbin/busybox route'

    """)

    upfile = open('vpnup.sh', 'w')
    downfile = open('vpndown.sh', 'w')

    upfile.write(upscript_header)
    upfile.write('\n')
    downfile.write(downscript_header)
    downfile.write('\n')

    for ip, mask, _ in results:
        upfile.write('route add -net %s netmask %s gw $OLDGW\n' % (ip, mask))
        downfile.write('route del -net %s netmask %s\n' % (ip, mask))

    upfile.close()
    downfile.close()

    print("Old school way to call up/down script from openvpn client."
          " Use the regular openvpn 2.1 method to add routes if it's possible.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate routing rules for VPN split tunneling.")
    parser.add_argument('-p', '--platform',
                        dest='platform',
                        default='openvpn',
                        nargs='?',
                        help="Target platforms: openvpn, mac, linux, win, android, cidr. openvpn by default.")
    parser.add_argument('-m', '--metric',
                        dest='metric',
                        default=5,
                        nargs='?',
                        type=int,
                        help="Metric setting for the route rules")

    args = parser.parse_args()

    if args.platform.lower() == 'openvpn':
        generate_ovpn(args.metric)
    elif args.platform.lower() == 'linux':
        generate_linux(args.metric)
    elif args.platform.lower() == 'mac' or args.platform.lower() == 'darwin':
        generate_mac(args.metric)
    elif args.platform.lower() == 'win':
        generate_win(args.metric)
    elif args.platform.lower() == 'android':
        generate_android(args.metric)
    elif args.platform.lower() == 'cidr':
        generate_cidr()
    else:
        print("Platform %s is not supported." % args.platform, file=sys.stderr)
        exit(1)
