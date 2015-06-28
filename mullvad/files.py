# coding: utf-8


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


import os
import shutil
import zipfile


def unzip(file_name):
    print('Unzipping file', file_name)

    dest_dir = os.path.dirname(file_name)
    zip_file = zipfile.ZipFile(file_name)
    zip_file.extractall(dest_dir)
    zip_root = os.path.dirname(zip_file.namelist()[0])

    return os.path.join(dest_dir, zip_root)


def move(src_dir, dst_dir):
    print('Moving files from \'{}\' to \'{}\''.format(src_dir, dst_dir))

    for node in os.listdir(src_dir):
        node_name = os.path.join(src_dir, node)
        if os.path.isfile(node_name):
            shutil.copy(node_name, dst_dir)
