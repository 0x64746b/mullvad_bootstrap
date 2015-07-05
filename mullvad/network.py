#!/usr/bin/env python


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


import re
import socket
import time

import bs4
import ipaddress
import netifaces
import requests
import sh

from . import output


OPENVPN_CONFIG_DIR = '/etc/openvpn/'


class NetworkError(Exception):

    pass


class InfoSniperTable(dict):

    def __init__(self, table):
        rows = table.find_all('tr')
        header_rows, value_rows = rows[::2], rows[1::2]

        for row_pair in zip(header_rows, value_rows):
            self.update(self._parse_row(*row_pair))

    def _parse_row(self, header_row, value_row):
        headers = [cell.text for cell in header_row.find_all('td')[::2]]
        values = [cell.text.strip() for cell in value_row.find_all('td')[::2]]

        return {header: value for header, value in zip(headers, values)}

    def __str__(self):
        return (
            '\n'
            ' - ISP: {} in {}/{}\n'
            ' - IP: {} ({})'.format(
                self['Provider'],
                self['Continent'],
                self['Country'],
                self['IP Address'],
                self['Hostname'],
            )
        )


def start_vpn_service(tunnel_prefix):
    output.itemize('Restarting VPN service...')

    openvpn = sh.service.bake('openvpn')

    # stop openvpn to remove an existing tunnel device
    openvpn('stop')
    time.sleep(1)
    existing_devices = netifaces.interfaces()

    openvpn('start')

    # detect upcoming device
    tunnel_device = _detect_tunnel_device(existing_devices, tunnel_prefix)

    # wait for configuration to be applied
    _wait_for_routes(tunnel_device)

    return tunnel_device


def _detect_tunnel_device(existing_devices, tunnel_prefix):
    with output.Attempts('Detecting tunnel device', 15) as attempts:
        tunnel_device = None

        for attempt in attempts:
            new_tunnels = filter(
                lambda dev:
                    dev.startswith(tunnel_prefix) and
                    dev not in existing_devices,
                netifaces.interfaces()
            )

            if len(new_tunnels) == 0:
                attempt.passed()
            elif len(new_tunnels) == 1:
                tunnel_device = new_tunnels.pop()
                attempt.successful = True
            else:
                raise NetworkError(
                    'Failed to uniquely identify tunnel device: {} new devices'
                    ' detected: {}'.format(len(new_tunnels), new_tunnels)
                )

        if not attempts.successful:
            raise NetworkError(
                'Failed to detect tunnel device: No new tunnels found.'
            )

        return tunnel_device


def _wait_for_routes(tunnel_device):
    route = sh.route.bake('-n')

    with output.Attempts('Waiting for routes to be established') as attempts:
        for attempt in attempts:
            if re.search(
                'Iface\n0\.0\.0\.0.+{}'.format(tunnel_device),
                route().stdout
            ):
                attempt.successful = True
            else:
                attempt.passed()

        if not attempts.successful:
            raise NetworkError('No default route through tunnel was set')


def remove_unencrypted_default_routes(tunnel_device):
    route = sh.route.bake('-n')

    default_interfaces = re.findall(
        '^0\.0\.0\.0 .+ (\w+)$',
        route().stdout,
        re.MULTILINE
    )

    for device in filter(
        lambda device: device != tunnel_device,
        default_interfaces
    ):
        output.itemize(
            'Removing default route from interface {}'.format(device)
        )
        route('del', 'default', 'dev', device)

    print(route().stdout)


def ping(ip='4.2.2.2'):
    output.itemize('Pinging {}...'.format(ip))

    try:
        packets = sh.ping('-c4', ip).stdout
    except sh.ErrorReturnCode:
        raise NetworkError('Could not reach {}'.format(ip))
    else:
        print(packets)


def get_connection_info(_output_level=1):
    output.itemize('Getting connection info...', _output_level)

    infos = requests.get('http://www.infosniper.net').content
    html = bs4.BeautifulSoup(infos)

    return InfoSniperTable(html.table)


def check_external_ip(original_connection, requested_exit_country):
    output.itemize('Checking external IP...')

    current_connection = get_connection_info()
    actual_exit_country = current_connection['TLD'].lower()

    if actual_exit_country != requested_exit_country:
        raise NetworkError(
            'Current connection ends in \'{}\', not in \'{}\''.format(
                actual_exit_country,
                requested_exit_country
            )
        )

    print('Original connection: {}'.format(original_connection))
    print('Current connection: {}'.format(current_connection))


def get_local_networks(tunnel_device):
    blacklisted_ifaces = ['lo', tunnel_device]
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
                networks.append((name, str(interface.network)))

    return networks


def get_vpn_gateway(_output_level=2):
    route = sh.route(_bg=True)

    with output.Attempts(
        'Resolving IP of VPN gateway',
        num_attempts=20,
        _output_level=_output_level
    ) as attempts:
        for attempt in attempts:
            if route.process.is_alive():
                attempt.passed()
            else:
                attempt.successful = True

        if not attempts.successful:
            raise NetworkError('Failed to resolve IP of VPN gateway')

    row = re.search(
        '^(?P<domain>.+\.mullvad\.net) .+ (?P<device>.+)$',
        route.stdout,
        re.MULTILINE
    )

    if row:
        gateway_ip = socket.gethostbyname(row.group('domain'))
    else:
        raise NetworkError('No route to VPN gateway detected.')

    return (row.group('device'), gateway_ip)
