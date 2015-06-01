#!/usr/bin/env python


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


from bs4 import BeautifulSoup
from requests import Session
from sh import display
from urlparse import urljoin


MULLVAD_DOMAIN = 'https://mullvad.net'
SETUP_PATH = '/en/setup/openvpn/'


def _get_create_form(page_content):
    html = BeautifulSoup(page_content)
    return html.find('form', {'id': 'create_account'})


if __name__ == '__main__':
    setup_url = urljoin(MULLVAD_DOMAIN, SETUP_PATH)

    session = Session()

    setup_response = session.get(setup_url)

    create_form = _get_create_form(setup_response.content)
    captcha_name = create_form.find('input', {'id': 'id_captcha_0'})['value']
    captcha_path = create_form.find('img', {'class': 'captcha'})['src']

    captcha_response = session.get(
        urljoin(MULLVAD_DOMAIN, captcha_path),
        stream=True
    )

    captcha = display(_in=captcha_response.raw, _bg=True)
    captcha_value = raw_input('Enter captcha: ')
    captcha.process.kill()

    login_response = session.post(
        setup_url,
        data={
            'captcha_0': captcha_name,
            'captcha_1': captcha_value,
            'create_account': 'create',
        }
    )

    create_form = _get_create_form(login_response.content)
    if create_form is not None:
        errors = create_form.find(
            'ul',
            {'class': 'errorlist'}
        ).find_all(
            'li'
        )
        for error in errors:
            print(error.text)
    else:
        print('You are now logged in')
