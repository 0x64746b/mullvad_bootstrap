# coding: utf-8


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


import os
import re
import shutil
import zipfile

from . import output


def unzip(file_name):
    output.itemize('Unzipping file \'{}\''.format(file_name))

    dest_dir = os.path.dirname(file_name)
    zip_file = zipfile.ZipFile(file_name)
    zip_file.extractall(dest_dir)
    zip_root = os.path.dirname(zip_file.namelist()[0])

    return os.path.join(dest_dir, zip_root)


def grep(regex, file_name):
    output.itemize('Extracting \'{}\' from \'{}\''.format(regex, file_name))
    with open(file_name) as input_file:
        for line in input_file.readlines():
            match = re.search(regex, line)
            if match:
                return match.groups()


def move(src_dir, dst_dir):
    output.itemize(
        'Moving files from \'{}\' to \'{}\''.format(src_dir, dst_dir)
    )

    for node in os.listdir(src_dir):
        node_name = os.path.join(src_dir, node)
        if os.path.isfile(node_name):
            shutil.copy(node_name, dst_dir)


def remove(directory, _output_level=0):
    output.itemize('Removing \'{}\''.format(directory), _output_level)

    shutil.rmtree(directory)
