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

from MoinMoin.storage import Backend


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
        self.backends = [backend[1] for backend in self.mapping] + [users, ]

    def _get_backend(self, itemname):
        for mountpoint, backend in self.mapping:
            if itemname == mountpoint or itemname.startswith(mountpoint and mountpoint + '/' or ''):
                lstrip = mountpoint and len(mountpoint)+1 or 0
                return backend, itemname[lstrip:]
        # If we couldn't find a backend for the given namespace it means that that
        # namespace has no special backend, so we just return the default backend
        # and the itemname unchanged.
        return self.default, itemname

    def iteritems(self):
        for backend in self.backends:
            for item in backend.iteritems():
                yield item # XXX item does not know its full name

    def has_item(self, itemname):
        # While we could use the inherited, generic implementation
        # it is generally advised to override this method.
        # Thus, we pass the call down.
        backend, itemname = self._get_backend(itemname)
        return backend.has_item(itemname)

    def get_item(self, itemname):
        backend, itemname = self._get_backend(itemname)
        return backend.get_item(itemname) # XXX item does not know its full name

    def create_item(self, itemname):
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Itemnames must have string type, not %s" % (type(itemname)))

        backend, itemname = self._get_backend(itemname)
        return backend.create_item(itemname)  # XXX item does not know it's full name
