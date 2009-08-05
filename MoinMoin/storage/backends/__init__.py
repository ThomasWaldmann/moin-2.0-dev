"""
    MoinMoin - Backends

    This package contains code for the backends of the new storage layer.

    @copyright: 2007 MoinMoin:HeinrichWendel,
    @copyright: 2008 MoinMoin:PawelPacana,
    @copyright: 2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import sys
import os

from MoinMoin.storage.serialization import unserialize
from MoinMoin.storage.error import NoSuchItemError, RevisionAlreadyExistsError


def copy_item(item, destination, verbose=False, name=None):
    return destination.copy_item(item, verbose, name)


def clone(source, destination, verbose=False, only_these=[]):
    return destination.clone(source, verbose, only_these)


def upgrade_syspages(request, packagepath):
    """
    Upgrade the wiki's system pages from an XML file.

    @type packagepath: basestring
    @param packagepath: Name of the item containing the system pages xml as data.
    """
    # !! Uses ACL-free storage !!
    storage = request.unprotected_storage
    try:
        item = storage.get_item(packagepath)
        rev = item.get_revision(-1)
    except NoSuchItemError, NoSuchRevisionError:
        raise BackendError("No such item %r." % packagepath)

    tmp_backend = memory.MemoryBackend()
    unserialize(tmp_backend, rev)

    # clone to real backend from config WITHOUT checking ACLs!
    clone(tmp_backend, storage)
