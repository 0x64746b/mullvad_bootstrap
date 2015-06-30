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


def itemize(text):
    start_progress(text)
    finish_progress()


def start_progress(text):
    sys.stdout.write(termcolor.colored('[*] ' + text, 'green'))
    sys.stdout.flush()


def progress():
    sys.stdout.write(termcolor.colored('.', 'green'))
    sys.stdout.flush()


def finish_progress():
    sys.stdout.write('\n')
    sys.stdout.flush()


def error(text):
    termcolor.cprint(text, 'red')


def die(text):
    sys.exit(termcolor.colored(text, 'red', attrs=['bold']))
