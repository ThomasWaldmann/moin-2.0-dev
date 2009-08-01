#!/usr/bin/env python
"""
    MoinMoin - Migrate old 1.7, 1.8 and 1.9 wikis to the new storage format.

    This script can be invoked in order to:
        * create new data and user backends where the converted data will live
        * fill the new backends with the old wiki's data

    Invoke this script as follows:
        migrate_old_wiki_data.py <path/to/old/wiki/data> <backend_uri>

    E.g.:
        migrate_old_wiki_data.py wiki/data instance/

    After conversion is complete, you need the following in your wikiconfig:

        from MoinMoin.storage.backends.enduser import get_enduser_backend
        storage = get_enduser_backend('<backend_uri>')

    E.g.:
        storage = get_enduser_backend('instance/')


    @copyright: 2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""
# TODO: Support specifying destination user backend as well

import sys
from os.path import join, isdir

from MoinMoin.storage.backends import clone, fs19, enduser


def get_target_backends(backend_uri):
    router_backend = enduser.get_enduser_backend(backend_uri)
    return router_backend, router_backend.user_backend


def run(source, backend_uri, only_these=[]):
    """
    Source must be a path to a MoinMoin wiki's data folder, i.e. something like
    'MoinMoin/wiki/data'.
    """
    if not isdir(source):
        sys.exit('Incorrect path for source folder specified.')
    src_pages = fs19.FSPageBackend(source)
    src_user = fs19.FSUserBackend(source)
    dest_data, dest_user = get_target_backends(backend_uri)

    clone(src_pages, dest_data, verbose=True, only_these=only_these)
    clone(src_user, dest_user, verbose=True)

    print "Conversion succeeded."


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit("You need to specify both:\n\t* The path to the old wiki data\n\t* The new backend_uri\nAbort!")
    run(sys.argv[1], sys.argv[2])

