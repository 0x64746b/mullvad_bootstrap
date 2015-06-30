#!/usr/bin/env python


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


import re
import time

import bs4
import requests
import sh

from . import output


OPENVPN_CONFIG_DIR = '/etc/openvpn/'
TUNNEL_DEVICE = 'tun0'


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


def start_vpn_service():
    output.itemize('Starting VPN service...')

    sh.service('openvpn', 'restart')

    # wait for configuration to be applied
    _wait_for_routes()


def _wait_for_routes():
    output.start_progress('Waiting for routes to be established')

    route = sh.route.bake('-n')
    for attempt in range(10):
        if re.search(
            'Iface\n0\.0\.0\.0.+{}'.format(TUNNEL_DEVICE),
            route().stdout
        ):
            output.finish_progress()
            return
        else:
            output.progress()
            time.sleep(1)

    raise NetworkError('No default route through tunnel was set')


def remove_unencrypted_default_routes():
    route = sh.route.bake('-n')

    interfaces = re.findall(
        '^0\.0\.0\.0 .+ (\w+)$',
        route().stdout,
        re.MULTILINE
    )

    for device in filter(
        lambda device: device != TUNNEL_DEVICE,
        interfaces
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


def check_external_ip():
    output.itemize('Checking external IP...')

    infos = requests.get('http://www.infosniper.net').content
    html = bs4.BeautifulSoup(infos)

    table = InfoSniperTable(html.table)

    print(
        ' - ISP: {} in {}/{}'.format(
            table['Provider'],
            table['Continent'],
            table['Country'],
        )
    )
    print(
        ' - IP: {} ({})'.format(
            table['IP Address'],
            table['Hostname'],
        )
    )
