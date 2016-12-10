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

from . import output


Captcha = collections.namedtuple('Captcha', ['id', 'code'])


class AccountError(Exception):

    def __init__(self, message, errors, response, *args):
        super(AccountError, self).__init__(message, errors, response, *args)
        self.message = message
        self.errors = errors
        self.response = response


class Client(object):

    DOMAIN = 'https://mullvad.net'
    SIGNUP_PATH = '/en/signup/'
    CONFIG_PATH = '/en/config/?server={}'

    def __init__(self):

        self._session = requests.Session()
        self._signup_url = urlparse.urljoin(
            Client.DOMAIN,
            Client.SIGNUP_PATH
        )
        self._config_url = urlparse.urljoin(
            Client.DOMAIN,
            Client.CONFIG_PATH
        )
        self._error_count = 0

    def create_account(self, signup_page=None):

        if not signup_page:
            response = self._session.get(self._signup_url)
            response.raise_for_status()
            signup_page = response.content

        captcha = self._solve_captcha(signup_page)

        try:
            account_number = self._login(captcha)
        except AccountError as exception:
            Client._log_errors(exception)
            return self._retry(
                self.create_account,
                exception.response
            )
        except requests.exceptions.RequestException as error:
            Client._log_errors(error)
            raise

        return account_number

    def _solve_captcha(self, signup_page):
        captcha_id, captcha_image = self._fetch_captcha(signup_page)
        captcha_code = Client._display_captcha(captcha_image)
        return Captcha(captcha_id, captcha_code)

    def _fetch_captcha(self, signup_page):
        html = bs4.BeautifulSoup(signup_page)

        container = Client._get_captcha_container(html)
        captcha_id = container.find(
            'input',
            {'id': 'id_captcha_0'}
        )['value']
        captcha_path = container.find(
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
            self._signup_url,
            data={
                'payment_method': 'paypal',
                'captcha_0': captcha.id,
                'captcha_1': captcha.code,
                'create_account': 'create',
            }
        )

        return Client._extract_account_number(login_response.content)

    def download_config(self, exit_country):
        output.itemize('Downloading config...')

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
    def _get_captcha_container(html):
        return html.find('div', {'class': 'captcha'})

    @staticmethod
    def _display_captcha(image):
        viewer = sh.display(_in=image, _bg=True)
        code = raw_input('Enter captcha: ')
        viewer.process.kill()

        return code

    @staticmethod
    def _extract_account_number(signup_page):
        html = bs4.BeautifulSoup(signup_page)

        try:
            return html.find('p', {'class': 'acc-number'}).contents[2].strip()
        except AttributeError:
            error = Client._get_captcha_container(html).find(
                'p',
                {'class': 'text-danger'}
            ).contents[2].strip()

            raise AccountError(
                'Failed to create account',
                [error],
                signup_page
            )

    @staticmethod
    def _log_errors(exception):
        output.error(exception.message)
        if hasattr(exception, 'errors'):
            for error in exception.errors:
                output.error(' - {}'.format(error))
