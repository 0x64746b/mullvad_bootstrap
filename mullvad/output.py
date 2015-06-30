# coding: utf-8


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


import sys
import time

import termcolor


def notify(text):
    termcolor.cprint(text, 'green', attrs=['bold'])


def itemize(text):
    print(_make_item(text))


def _make_item(text):
    return termcolor.colored('[*] ' + text, 'green')


def error(text):
    termcolor.cprint(text, 'red')


def die(text):
    sys.exit(termcolor.colored(text, 'red', attrs=['bold']))


class Attempts(object):

    def __init__(self, text, num_attempts=10, delay=1):
        self._item = _make_item(text)
        self._num_attempts = num_attempts
        self._delay = delay

        self._current_attempt = 0
        self._successful = False

    @property
    def successful(self):
        return self._successful

    @successful.setter
    def successful(self, value):
        self._successful = value

    def __enter__(self):
        sys.stdout.write(self._item)
        sys.stdout.flush()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.write('\n')
        sys.stdout.flush()
        return False

    def passed(self):
        sys.stdout.write(termcolor.colored('.', 'green'))
        sys.stdout.flush()
        time.sleep(self._delay)

    def __iter__(self):
        return self

    def next(self):
        if self._current_attempt < self._num_attempts and not self._successful:
            self._current_attempt += 1
            return self
        else:
            raise StopIteration()
