#!/usr/bin/env python


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


import collections
from os import path
import re
import sys
import tempfile
import urlparse

import bs4
import requests
import sh


Captcha = collections.namedtuple('Captcha', ['id', 'code'])


class LoginError(Exception):

    def __init__(self, message, errors, response, *args):
        super(LoginError, self).__init__(message, errors, response, *args)
        self.message = message
        self.errors = errors
        self.response = response


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
        except LoginError as exception:
            WebClient._log_errors(exception)
            self._retry(self.create_account, exception.response)
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

        mullvad_config = path.join(tempfile.mkdtemp(), 'mullvadconfig.zip')
        with open(mullvad_config, 'wb') as zip_file:
            for chunk in downloaded_config:
                zip_file.write(chunk)

        return mullvad_config

    def _retry(self, method, *args):
        self._error_count += 1
        if self._error_count < 3:
            method(*args)
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

            raise LoginError(
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
    def unzip(zip_file):
        print('Unzipping config file', zip_file)

        tmp_dir = path.dirname(zip_file)
        process = sh.unzip(zip_file, '-d', tmp_dir)
        output_dir = re.search(
            '^ extracting: {}/(\d+)/.+  $'.format(tmp_dir),
            process.stdout,
            re.MULTILINE
        ).group(1)

        return path.join(tmp_dir, output_dir)


if __name__ == '__main__':
    mullvad = WebClient()
    try:
        config_file = mullvad.create_account()
    except Exception:
        sys.exit('Ultimately failed to create account')
    else:
        config_dir = FileManager.unzip(config_file)
        print('Extracted config files to', config_dir)
