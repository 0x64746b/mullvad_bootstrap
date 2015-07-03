# coding: utf-8


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


import os.path
import tempfile

import sh

from . import output


def backup_config():
    backup_file = os.path.join(tempfile.mkdtemp(), 'iptables.cfg.bak')

    output.itemize(
        'Backing up firewall configuration to \'{}\''.format(backup_file)
    )

    sh.iptables_save(_out=backup_file)
