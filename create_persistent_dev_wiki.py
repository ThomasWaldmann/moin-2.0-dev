#!/usr/bin/env python
"""
    MoinMoin - Create Persistent Dev Wiki

    Just a simple script that devs/betatesters can invoke
    in order to:
        * create an 'instance' folder that will contain all data
        * untar the underlay folder
        * fill the instance with the underlay data
        * remove the untared underlay files

    In your wikiconfig you will need to set the following options:
        from MoinMoin.storage.backends.enduser import get_enduser_backend
        storage = get_enduser_backend('<path/to/instance>')

    E.g.:
        storage = get_enduser_backend('instance/')

    @copyright: 2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import os
from os.path import join
from shutil import rmtree
import tarfile

from MoinMoin.storage.backends import clone, fs19, fs
from MoinMoin.i18n.strings import all_pages


DATA = 'data'
USER = 'user'


def create_instance_folder(instance):
    os.makedirs(join(instance, DATA))
    os.mkdir(join(instance, USER))


def untar_underlay(instance):
    tar = tarfile.open(join('wiki', 'underlay.tar'))
    tar.extractall(instance)
    tar.close()


def fill_instance(underlay_tmp, instance):
    fs_src = fs19.FSPageBackend(join(instance, underlay_tmp))
    fs_dst = fs.FSBackend(join(instance, DATA))
    clone(fs_src, fs_dst, verbose=True, only_these=all_pages)


def cleanup(underlay_tmp, instance):
    rmtree(join(instance, underlay_tmp))


def run(instance, underlay_tmp):
    print "Starting underlay conversion..."
    create_instance_folder(instance)
    untar_underlay(instance)
    fill_instance(underlay_tmp, instance)
    cleanup(underlay_tmp, instance)


if __name__ == '__main__':
    run()
