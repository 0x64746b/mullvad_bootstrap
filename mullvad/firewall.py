# coding: utf-8


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


import os.path
import random
import string
import tempfile

import sh

from . import files, network, output


def backup_config():
    backup_file = os.path.join(tempfile.mkdtemp(), 'iptables.cfg.bak')

    output.itemize(
        'Backing up firewall configuration to \'{}\''.format(backup_file)
    )

    sh.iptables_save(_out=backup_file)

    return backup_file


def restore_config(config_file):
    output.itemize(
        'Restoring firewall configuration from \'{}\''.format(config_file)
    )

    sh.iptables_restore(sh.cat(config_file))
    files.remove(os.path.dirname(config_file), _output_level=1)


def block_traffic(tunnel_device):
    output.itemize('Blocking relatable traffic...')

    output.itemize('Resetting config', level=1)
    sh.iptables('-P', 'INPUT', 'ACCEPT')
    sh.iptables('-P', 'FORWARD', 'ACCEPT')
    sh.iptables('-P', 'OUTPUT', 'ACCEPT')
    sh.iptables('-F')
    sh.iptables('-X')

    output.itemize('Allowing traffic over loopback interface', level=1)
    sh.iptables('-I', 'INPUT', '-i', 'lo', '-j', 'ACCEPT')
    sh.iptables('-I', 'OUTPUT', '-o', 'lo', '-j', 'ACCEPT')

    output.itemize('Allowing traffic over local networks', level=1)
    lans = network.get_local_networks(tunnel_device)
    for lan in lans:
        output.itemize(
            'Allowing traffic over {} for {}'.format(lan[0], lan[1]), level=2
        )
        sh.iptables('-I', 'INPUT', '-i', lan[0], '-s', lan[1], '-j', 'ACCEPT')
        sh.iptables('-I', 'OUTPUT', '-o', lan[0], '-d', lan[1], '-j', 'ACCEPT')

    output.itemize('Allowing traffic over VPN interface', level=1)
    sh.iptables('-I', 'INPUT', '-i', tunnel_device, '-j', 'ACCEPT')
    sh.iptables('-I', 'OUTPUT', '-o', tunnel_device, '-j', 'ACCEPT')

    output.itemize('Allowing traffic to VPN gateway', level=1)
    vpn_gate = network.get_vpn_gateway()
    sh.iptables(
        '-I', 'INPUT',
        '-i', vpn_gate[0],
        '-p', 'udp',
        '-s', vpn_gate[1],
        '--sport', '1301',
        '-j', 'ACCEPT'
    )
    sh.iptables(
        '-I', 'OUTPUT',
        '-o', vpn_gate[0],
        '-p', 'udp',
        '-d', vpn_gate[1],
        '--dport', '1301',
        '-j', 'ACCEPT'
    )

    output.itemize('Logging dropped traffic', level=1)
    sh.iptables(
        '-A', 'INPUT',
        '-m', 'limit',
        '--limit', '1/min',
        '-j', 'LOG',
        '--log-prefix', 'iptables:dropped input: ',
        '--log-level', '4',
    )
    sh.iptables(
        '-A', 'OUTPUT',
        '-m', 'limit',
        '--limit', '1/min',
        '-j', 'LOG',
        '--log-prefix', 'iptables:dropped output: ',
        '--log-level', '4',
    )
    sh.iptables(
        '-A', 'FORWARD',
        '-m', 'limit',
        '--limit', '1/min',
        '-j', 'LOG',
        '--log-prefix', 'iptables:dropped forward: ',
        '--log-level', '4',
    )

    output.itemize('Dropping all other traffic', level=1)
    sh.iptables('-P', 'INPUT', 'DROP')
    sh.iptables('-P', 'OUTPUT', 'DROP')
    sh.iptables('-P', 'FORWARD', 'DROP')

    for line in sh.iptables('-vnL', _iter=True):
        print(line.rstrip())


def abort_prompt():
    security_code = ''.join(random.choice(string.lowercase) for i in range(4))

    output.itemize(
        'Enter \'{}\' to terminate protection'.format(security_code)
    )
    entered_code = raw_input('Security code: ')

    if entered_code != security_code:
        output.error('Invalid code')
        abort_prompt()
