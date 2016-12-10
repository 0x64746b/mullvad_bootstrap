# coding: utf-8


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


import collections
import os
import re
import tempfile
import urlparse

import bs4
import requests
import sh

from . import output


Captcha = collections.namedtuple('Captcha', ['id', 'code', 'csrf'])


class AccountError(Exception):

    def __init__(self, message, response, *args):
        super(AccountError, self).__init__(message, response, *args)
        self.message = message
        self.response = response


class Client(object):

    DOMAIN = 'https://mullvad.net'
    SIGNUP_PATH = '/account/create/'
    CONFIG_PATH = '/download/config/'

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
            output.error(exception.message)
            return self._retry(
                self.create_account,
                exception.response
            )
        except requests.exceptions.RequestException as error:
            Client._log_errors(error)
            raise

        return account_number

    def _solve_captcha(self, signup_page):
        captcha_id, captcha_image, csrf_token = self._fetch_captcha(signup_page)
        captcha_code = Client._display_captcha(captcha_image)
        return Captcha(captcha_id, captcha_code, csrf_token)

    def _fetch_captcha(self, signup_page):
        html = bs4.BeautifulSoup(signup_page)
        captcha_id = html.find(
            'input',
            {'id': 'id_captcha_0'}
        )['value']
        captcha_path = html.find(
            'img',
            {'class': 'captcha'}
        )['src']
        csrf_token = html.find(
            'input',
            {'name': 'csrfmiddlewaretoken'}
        )['value']

        captcha_image = self._session.get(
            urlparse.urljoin(Client.DOMAIN, captcha_path),
            stream=True
        )

        return captcha_id, captcha_image.raw, csrf_token

    def _login(self, captcha):
        login_response = self._session.post(
            self._signup_url,
            headers={'referer': self._signup_url},
            data={
                'captcha_0': captcha.id,
                'captcha_1': captcha.code,
                'csrfmiddlewaretoken': captcha.csrf,
            }
        )

        return Client._extract_account_number(login_response.content)

    def download_config(self, exit_country):
        output.itemize('Downloading config...')

        config_page = bs4.BeautifulSoup(self._session.get(self._config_url).content)
        other_platforms = config_page.find('input', {'name':'type', 'value':'zip'}).parent

        downloaded_config = self._session.post(
            self._config_url,
            headers={'referer': self._config_url},
            data={
                'csrfmiddlewaretoken': other_platforms.find('input', {'name': 'csrfmiddlewaretoken'})['value'],
                'type': other_platforms.find('input', {'name': 'type'})['value'],
                'account_number': other_platforms.find('input', {'name': 'account_number'})['value'],
                'port': other_platforms.find('option', {'selected': 'selected'})['value'],
                'country': exit_country,
            },
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
    def _display_captcha(image):
        viewer = sh.display(_in=image, _bg=True)
        code = raw_input('Enter captcha: ')
        viewer.process.kill()

        return code

    @staticmethod
    def _extract_account_number(signup_page):
        html = bs4.BeautifulSoup(signup_page)

        try:
            return html.find('h3', text=re.compile('Your account number')).text.split()[-1]
        except AttributeError:
            raise AccountError(
                'Failed to create account (probably the CAPTCHA was wrong)',
                signup_page
            )
