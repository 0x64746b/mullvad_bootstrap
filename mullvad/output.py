# coding: utf-8


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


import sys

import termcolor


def notify(text):
    termcolor.cprint(text, 'green', attrs=['bold'])


def die(text):
    sys.exit(termcolor.colored(text, 'red'))
