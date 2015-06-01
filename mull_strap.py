#!/usr/bin/env python


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


from collections import namedtuple

from bs4 import BeautifulSoup
from requests import Session
from sh import display
import sys
from urlparse import urljoin


class LoginError(Exception):

    def __init__(self, message, errors, response, *args):
        super(LoginError, self).__init__(message, errors, response, *args)
        self.message = message
        self.errors = errors
        self.response = response


class Mullvad(object):

    DOMAIN = 'https://mullvad.net'
    SETUP_PATH = '/en/setup/openvpn/'

    Captcha = namedtuple('Captcha', ['id', 'code'])

    def __init__(self):

        self._session = Session()
        self._setup_url = urljoin(Mullvad.DOMAIN, Mullvad.SETUP_PATH)
        self._error_count = 0

    def create_account(self, setup_page=None):

        if not setup_page:
            setup_page = self._session.get(self._setup_url).content

        captcha = self._solve_captcha(setup_page)

        try:
            self._login(captcha)
        except LoginError as exception:
            Mullvad._log_errors(exception)
            self._error_count += 1
            if self._error_count < 3:
                self.create_account(exception.response)
            else:
                raise exception
        else:
            return self._download_config()

    def _solve_captcha(self, setup_page):
        captcha_id, captcha_image = self._fetch_captcha(setup_page)
        captcha_code = Mullvad._display_captcha(captcha_image)
        return Mullvad.Captcha(captcha_id, captcha_code)

    def _fetch_captcha(self, setup_page):
        create_form = Mullvad._get_create_form(setup_page)
        captcha_id = create_form.find(
            'input',
            {'id': 'id_captcha_0'}
        )['value']
        captcha_path = create_form.find(
            'img',
            {'class': 'captcha'}
        )['src']

        captcha_image = self._session.get(
            urljoin(Mullvad.DOMAIN, captcha_path),
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
        Mullvad._validate_login(login_response.content)

    def _download_config(self):
        print('Downloading config... NOT YET IMPLEMENTED')

    @staticmethod
    def _get_create_form(page_content):
        html = BeautifulSoup(page_content)
        return html.find('form', {'id': 'create_account'})

    @staticmethod
    def _display_captcha(image):
        viewer = display(_in=image, _bg=True)
        code = raw_input('Enter captcha: ')
        viewer.process.kill()

        return code

    @staticmethod
    def _validate_login(setup_page):
        create_form = Mullvad._get_create_form(setup_page)
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
        for error in exception.errors:
            print(' - {}'.format(error))


if __name__ == '__main__':
    mullvad = Mullvad()
    try:
        config = mullvad.create_account()
    except LoginError as exception:
        sys.exit('Ultimately failed to create account')
    else:
        print('Successfully downloaded config file:', config)
