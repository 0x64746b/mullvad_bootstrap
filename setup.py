# coding: utf-8


from __future__ import (
    absolute_import,
    division,
    print_function,
)


import distutils.core


distutils.core.setup(
    name='mullvad_bootstrap',
    version='0.1',
    scripts=['bin/mullvad'],
    packages=['mullvad'],
    provides='mullvad',

    # metadata for upload to PyPI
    author='D.',
    author_email='dtk@gmx.de',
    description='Bootstrap a VPN connection from a Mullvad test account.',
    license='GNU GPLv3',
    keywords='mullvad vpn bootstrap',
    url='https://github.com/0x64746b/mullvad_bootstrap',
)
