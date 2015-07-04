# coding: utf-8


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


import os.path
import re
import socket
import tempfile

import ipaddress
import netifaces
import sh

from . import output


def backup_config():
    backup_file = os.path.join(tempfile.mkdtemp(), 'iptables.cfg.bak')

    output.itemize(
        'Backing up firewall configuration to \'{}\''.format(backup_file)
    )

    sh.iptables_save(_out=backup_file)


def block_traffic():
    output.itemize('Blocking relatable traffic...')

    output.itemize('Removing existing routes', level=1)
    sh.iptables('-F')

    output.itemize('Allowing traffic over loopback interface', level=1)
    sh.iptables('-I', 'INPUT', '-i', 'lo', '-j', 'ACCEPT')
    sh.iptables('-I', 'OUTPUT', '-o', 'lo', '-j', 'ACCEPT')

    output.itemize('Allowing traffic over local networks', level=1)
    lans = _get_local_networks()
    for lan in lans:
        output.itemize('Allowing traffic for {}'.format(lan), level=2)
        sh.iptables('-I', 'INPUT', '-s', lan, '-j', 'ACCEPT')
        sh.iptables('-I', 'OUTPUT', '-d', lan, '-j', 'ACCEPT')

    output.itemize('Allowing traffic over VPN interface', level=1)
    sh.iptables('-I', 'INPUT', '-i', 'tun+', '-j', 'ACCEPT')
    sh.iptables('-I', 'OUTPUT', '-o', 'tun+', '-j', 'ACCEPT')

    output.itemize('Allowing traffic to VPN gateway', level=1)
    vpn_gate = _get_vpn_gateway()
    sh.iptables(
        '-I', 'INPUT',
        '-p', 'udp',
        '-s', vpn_gate,
        '--sport', '1300',
        '-j', 'ACCEPT'
    )
    sh.iptables(
        '-I', 'OUTPUT',
        '-p', 'udp',
        '-d', vpn_gate,
        '--dport', '1300',
        '-j', 'ACCEPT'
    )

    output.itemize('Dropping all other traffic', level=1)
    sh.iptables('-P', 'INPUT', 'DROP')
    sh.iptables('-P', 'OUTPUT', 'DROP')
    sh.iptables('-P', 'FORWARD', 'DROP')

    print(sh.iptables('-vL'))


def _get_local_networks():
    blacklisted_ifaces = ['lo', 'tun0']
    networks = []

    iface_names = filter(
        lambda iface: iface not in blacklisted_ifaces,
        netifaces.interfaces()
    )

    for name in iface_names:
        try:
            ipv4_addresses = netifaces.ifaddresses(name)[netifaces.AF_INET]
        except KeyError:
            output.itemize(
                'Skipping inactive interface {}'.format(name),
                level=2
            )
        else:
            for address in ipv4_addresses:
                interface = ipaddress.IPv4Interface(
                    '{}/{}'.format(address['addr'], address['netmask'])
                )
                networks.append(str(interface.network))

    return networks


def _get_vpn_gateway(_output_level=2):
    output.itemize('Resolving IP of VPN gateway', _output_level)
    route = sh.route()

    domain = re.search(
        '^(.+\.mullvad\.net)',
        route.stdout,
        re.MULTILINE
    ).group()

    return socket.gethostbyname(domain)
