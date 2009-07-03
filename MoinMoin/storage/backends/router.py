# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - routing backend

    You can use this backend to route requests to different backends
    depending on the item name.

    TODO: wrap backend items in wrapper items, so we can fix item
          names, support rename between backends, etc.

    @copyright: 2008 MoinMoin:ThomasWaldmann,
                2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import re

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.error import ConfigurationError

from MoinMoin.storage import Backend, Item


class RouterBackend(Backend):
    """
    Router Backend - routes requests to different backends depending
    on the item name.

    For method docstrings, please see the "Backend" base class.
    """
    def __init__(self, mapping, users):
        """
        Initialise router backend.

        @type mapping: list of tuples
        @param mapping: [(mountpoint, backend), ...]
        """
        if not mapping or not (mapping[-1][0] == '/'):
            raise ConfigurationError("You must specify a backend for '/' as the last backend in the mapping.")
        elif not users:
            raise ConfigurationError("You must specify a backend for user storage.")

        self.user_backend = users
        self.mapping = [(mountpoint.rstrip('/'), backend) for mountpoint, backend in mapping]

    def _get_backend(self, itemname):
        for mountpoint, backend in self.mapping:
            if itemname == mountpoint or itemname.startswith(mountpoint and mountpoint + '/' or ''):
                lstrip = mountpoint and len(mountpoint)+1 or 0
                return backend, itemname[lstrip:], itemname[:lstrip]
        # This point should never be reached since at least the last mountpoint, '/', should
        # contain the item.
        raise AssertionError('No backend found for %s. Available backends: %r' % (itemname, self.mapping))

    def iteritems(self):
        for mountpoint, backend in self.mapping:
            mountpoint = mountpoint + "/" if mountpoint else mountpoint
            for item in backend.iteritems():
                yield RouterItem(item, mountpoint, item.name)

    def has_item(self, itemname):
        # While we could use the inherited, generic implementation
        # it is generally advised to override this method.
        # Thus, we pass the call down.
        backend, itemname, mountpoint = self._get_backend(itemname)
        return backend.has_item(itemname)

    def get_item(self, itemname):
        backend, itemname, mountpoint = self._get_backend(itemname)
        return RouterItem(backend.get_item(itemname), mountpoint, itemname)

    def create_item(self, itemname):
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Itemnames must have string type, not %s" % (type(itemname)))

        backend, itemname, mountpoint = self._get_backend(itemname)
        return RouterItem(backend.create_item(itemname), mountpoint, itemname)


class RouterItem(object):
    """
    http://docs.python.org/reference/datamodel.html#special-method-lookup-for-new-style-classes
    """
    def __init__(self, item, mountpoint, itemname):
        self._item = item
        self._mountpoint = mountpoint
        self._itemname = itemname

    @property
    def name(self):
        return self._mountpoint + self._itemname

    def __setitem__(self, key, value):
        return self._item.__setitem__(key, value)

    def __delitem__(self, key):
        return self._item.__delitem__(key)

    def __getitem__(self, key):
        return self._item.__getitem__(key)

    def __getattr__(self, attr):
        #!! XXX will fail if inheriting from Item
        return getattr(self._item, attr)

    def rename(self, newname):
        # TODO How would this best work? Do we want to allow cross-backend renames?
        self._item.rename(newname)
        self._itemname = newname
