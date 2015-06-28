#!/usr/bin/env python


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


import collections
import os
import re
import shutil
import sys
import tempfile
import time
import urlparse
import zipfile

import bs4
import requests
import sh


Captcha = collections.namedtuple('Captcha', ['id', 'code'])


class AccountError(Exception):

    def __init__(self, message, errors, response, *args):
        super(AccountError, self).__init__(message, errors, response, *args)
        self.message = message
        self.errors = errors
        self.response = response


class NetworkError(Exception):

    pass


class WebClient(object):

    DOMAIN = 'https://mullvad.net'
    SETUP_PATH = '/en/setup/openvpn/'
    CONFIG_PATH = '/en/config/?server=se'

    def __init__(self):

        self._session = requests.Session()
        self._setup_url = urlparse.urljoin(
            WebClient.DOMAIN,
            WebClient.SETUP_PATH
        )
        self._config_url = urlparse.urljoin(
            WebClient.DOMAIN,
            WebClient.CONFIG_PATH
        )
        self._error_count = 0

    def create_account(self, setup_page=None):

        if not setup_page:
            setup_page = self._session.get(self._setup_url).content

        captcha = self._solve_captcha(setup_page)

        try:
            self._login(captcha)
        except AccountError as exception:
            WebClient._log_errors(exception)
            return self._retry(self.create_account, exception.response)
        except requests.exceptions.RequestException as error:
            WebClient._log_errors(error)
            raise

        try:
            config_file = self._download_config()
        except requests.exceptions.RequestException as error:
            WebClient._log_errors(error)
            raise

        return config_file

    def _solve_captcha(self, setup_page):
        captcha_id, captcha_image = self._fetch_captcha(setup_page)
        captcha_code = WebClient._display_captcha(captcha_image)
        return Captcha(captcha_id, captcha_code)

    def _fetch_captcha(self, setup_page):
        create_form = WebClient._get_create_form(setup_page)
        captcha_id = create_form.find(
            'input',
            {'id': 'id_captcha_0'}
        )['value']
        captcha_path = create_form.find(
            'img',
            {'class': 'captcha'}
        )['src']

        captcha_image = self._session.get(
            urlparse.urljoin(WebClient.DOMAIN, captcha_path),
            stream=True
        )

        return captcha_id, captcha_image.raw

    def _login(self, captcha):
        login_response = self._session.post(
            self._setup_url,
            data={
                'captcha_0': captcha.id,
                'captcha_1': captcha.code,
                'create_account': 'create',
            }
        )
        WebClient._validate_login(login_response.content)

    def _download_config(self):
        print('Downloading config...')

        downloaded_config = self._session.get(self._config_url, stream=True)
        downloaded_config.raise_for_status()

        mullvad_config = os.path.join(tempfile.mkdtemp(), 'mullvadconfig.zip')

        with open(mullvad_config, 'wb') as zip_file:
            for chunk in downloaded_config:
                zip_file.write(chunk)

        return mullvad_config

    def _retry(self, method, *args):
        self._error_count += 1
        if self._error_count < 3:
            return method(*args)
        else:
            raise

    @staticmethod
    def _get_create_form(page_content):
        html = bs4.BeautifulSoup(page_content)
        return html.find('form', {'id': 'create_account'})

    @staticmethod
    def _display_captcha(image):
        viewer = sh.display(_in=image, _bg=True)
        code = raw_input('Enter captcha: ')
        viewer.process.kill()

        return code

    @staticmethod
    def _validate_login(setup_page):
        create_form = WebClient._get_create_form(setup_page)
        if create_form is not None:
            errors = create_form.find(
                'ul',
                {'class': 'errorlist'}
            ).find_all('li')

            raise AccountError(
                'Failed to create account',
                [error.text for error in errors],
                setup_page
            )

    @staticmethod
    def _log_errors(exception):
        print(exception.message)
        if hasattr(exception, 'errors'):
            for error in exception.errors:
                print(' - {}'.format(error))


class FileManager(object):

    @staticmethod
    def unzip(file_name):
        print('Unzipping file', file_name)

        dest_dir = os.path.dirname(file_name)
        zip_file = zipfile.ZipFile(file_name)
        zip_file.extractall(dest_dir)
        zip_root = os.path.dirname(zip_file.namelist()[0])

        return os.path.join(dest_dir, zip_root)

    @staticmethod
    def move_files(src_dir, dst_dir):
        print('Moving files from \'{}\' to \'{}\''.format(src_dir, dst_dir))

        for node in os.listdir(src_dir):
            node_name = os.path.join(src_dir, node)
            if os.path.isfile(node_name):
                shutil.copy(node_name, dst_dir)


class NetworkManager(object):

    OPENVPN_CONFIG_DIR = '/etc/openvpn'
    TUNNEL_DEVICE = 'tun0'

    @staticmethod
    def start_vpn_service():
        print('Starting VPN service...')

        sh.service('openvpn', 'restart')

        # wait for configuration to be applied
        NetworkManager._wait_for_routes()

    @staticmethod
    def _wait_for_routes():
        sys.stdout.write('Waiting for routes to be established')
        sys.stdout.flush()

        for attempt in range(10):
            routes = sh.route('-n').stdout
            if re.search(
                'Iface\n0\.0\.0\.0.+{}'.format(NetworkManager.TUNNEL_DEVICE),
                routes
            ):
                print(
                    '\nDefault route through tunnel has been established:\n',
                    routes
                )
                return
            else:
                sys.stdout.write('.')
                sys.stdout.flush()
                time.sleep(1)

        raise NetworkError('No default route through tunnel was set')

    @staticmethod
    def ping(ip='4.2.2.2'):
        print('Pinging {}...'.format(ip))

        try:
            packets = sh.ping('-c4', ip).stdout
        except sh.ErrorReturnCode:
            raise NetworkError('Could not reach {}'.format(ip))
        else:
            print(packets)

    @staticmethod
    def check_external_ip():
        print('Checking external IP...')

        infos = requests.get('http://www.infosniper.net').content
        html = bs4.BeautifulSoup(infos)

        table = InfoSniperTable(html.table)

        print(
            ' - ISP: {} in {}/{}'.format(
                table[1]['Provider'],
                table[3]['Continent'],
                table[2]['Country']
            )
        )
        print(
            ' - IP: {} ({})'.format(
                table[0]['IP Address'],
                table[2]['Hostname']
            )
        )


class InfoSniperTable(object):

    class Row(object):

        def __init__(self, header_row, value_row):
            headers = [cell.text for cell in header_row.find_all('td')[::2]]
            values = [cell.text.strip() for cell in
                      value_row.find_all('td')[::2]]

            self._cells = {header: value for header, value in
                           zip(headers, values)}

        def __getitem__(self, index):
            return self._cells[index]

        def __repr__(self):
            return str(self._cells)

    def __init__(self, table):
        rows = table.find_all('tr')
        header_rows, value_rows = rows[::2], rows[1::2]
        self._rows = [InfoSniperTable.Row(*row_pair) for row_pair in
                      zip(header_rows, value_rows)]

    def __getitem__(self, index):
        return self._rows[index]

    def __repr__(self):
        return '\n'.join(map(str, self._rows))


if __name__ == '__main__':
    mullvad = WebClient()
    try:
        config_file = mullvad.create_account()
    except Exception as error:
        sys.exit('Failed to create account: {}'.format(error.message))
    else:
        config_dir = FileManager.unzip(config_file)
        FileManager.move_files(config_dir, NetworkManager.OPENVPN_CONFIG_DIR)

    try:
        NetworkManager.start_vpn_service()
    except Exception as error:
        sys.exit('Failed to connect to VPN: {}'.format(error.message))

    try:
        NetworkManager.ping()
    except Exception as error:
        sys.exit('Failed to verify connectivity: {}'.format(error.message))
    else:
        NetworkManager.check_external_ip()
