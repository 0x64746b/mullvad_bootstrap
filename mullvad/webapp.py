# coding: utf-8


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


import collections
import os
import tempfile
import urlparse

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


class Client(object):

    DOMAIN = 'https://mullvad.net'
    SETUP_PATH = '/en/setup/openvpn/'
    CONFIG_PATH = '/en/config/?server={}'

    def __init__(self):

        self._session = requests.Session()
        self._setup_url = urlparse.urljoin(
            Client.DOMAIN,
            Client.SETUP_PATH
        )
        self._config_url = urlparse.urljoin(
            Client.DOMAIN,
            Client.CONFIG_PATH
        )
        self._error_count = 0

    def create_account(self, exit_country, setup_page=None):

        if not setup_page:
            setup_page = self._session.get(self._setup_url).content

        captcha = self._solve_captcha(setup_page)

        try:
            self._login(captcha)
        except AccountError as exception:
            Client._log_errors(exception)
            return self._retry(
                self.create_account,
                exit_country,
                exception.response
            )
        except requests.exceptions.RequestException as error:
            Client._log_errors(error)
            raise

        try:
            config_file = self._download_config(exit_country)
        except requests.exceptions.RequestException as error:
            Client._log_errors(error)
            raise

        return config_file

    def _solve_captcha(self, setup_page):
        captcha_id, captcha_image = self._fetch_captcha(setup_page)
        captcha_code = Client._display_captcha(captcha_image)
        return Captcha(captcha_id, captcha_code)

    def _fetch_captcha(self, setup_page):
        create_form = Client._get_create_form(setup_page)
        captcha_id = create_form.find(
            'input',
            {'id': 'id_captcha_0'}
        )['value']
        captcha_path = create_form.find(
            'img',
            {'class': 'captcha'}
        )['src']

        captcha_image = self._session.get(
            urlparse.urljoin(Client.DOMAIN, captcha_path),
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
        Client._validate_login(login_response.content)

    def _download_config(self, exit_country):
        print('Downloading config...')

        downloaded_config = self._session.get(
            self._config_url.format(exit_country),
            stream=True
        )
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
        create_form = Client._get_create_form(setup_page)
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
