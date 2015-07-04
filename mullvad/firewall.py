# coding: utf-8


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


import os.path
import tempfile

import sh

from . import network, output


def backup_config():
    backup_file = os.path.join(tempfile.mkdtemp(), 'iptables.cfg.bak')

    output.itemize(
        'Backing up firewall configuration to \'{}\''.format(backup_file)
    )

    sh.iptables_save(_out=backup_file)


def block_traffic():
    output.itemize('Blocking relatable traffic...')

    output.itemize('Resetting config', level=1)
    sh.iptables('-P', 'INPUT', 'ACCEPT')
    sh.iptables('-P', 'FORWARD', 'ACCEPT')
    sh.iptables('-P', 'OUTPUT', 'ACCEPT')
    sh.iptables('-F')

    output.itemize('Allowing traffic over loopback interface', level=1)
    sh.iptables('-I', 'INPUT', '-i', 'lo', '-j', 'ACCEPT')
    sh.iptables('-I', 'OUTPUT', '-o', 'lo', '-j', 'ACCEPT')

    output.itemize('Allowing traffic over local networks', level=1)
    lans = network.get_local_networks()
    for lan in lans:
        output.itemize(
            'Allowing traffic over {} for {}'.format(lan[0], lan[1]), level=2
        )
        sh.iptables('-I', 'INPUT', '-i', lan[0], '-s', lan[1], '-j', 'ACCEPT')
        sh.iptables('-I', 'OUTPUT', '-o', lan[0], '-d', lan[1], '-j', 'ACCEPT')

    output.itemize('Allowing traffic over VPN interface', level=1)
    sh.iptables('-I', 'INPUT', '-i', 'tun+', '-j', 'ACCEPT')
    sh.iptables('-I', 'OUTPUT', '-o', 'tun+', '-j', 'ACCEPT')

    output.itemize('Allowing traffic to VPN gateway', level=1)
    vpn_gate = network.get_vpn_gateway()
    sh.iptables(
        '-I', 'INPUT',
        '-i', vpn_gate[0],
        '-p', 'udp',
        '-s', vpn_gate[1],
        '--sport', '1300',
        '-j', 'ACCEPT'
    )
    sh.iptables(
        '-I', 'OUTPUT',
        '-o', vpn_gate[0],
        '-p', 'udp',
        '-d', vpn_gate[1],
        '--dport', '1300',
        '-j', 'ACCEPT'
    )

    output.itemize('Dropping all other traffic', level=1)
    sh.iptables('-P', 'INPUT', 'DROP')
    sh.iptables('-P', 'OUTPUT', 'DROP')
    sh.iptables('-P', 'FORWARD', 'DROP')

    for line in sh.iptables('-vL', _iter=True):
        print(line.rstrip())
