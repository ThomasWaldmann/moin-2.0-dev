# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - routing backend

    You can use this backend to route requests to different backends
    depending on the item name.

    TODO: wrap backend items in wrapper items, so we can fix item
          names, support rename between backends, etc.

    @copyright: 2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import re

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.storage import Backend

class NoMatchingBackend(Exception):
    """ Exception raised when no backend is found for some item name """


class RouterBackend(Backend):
    """
    Router Backend - routes requests to different backends depending
    on the item name.

    For method docstrings, please see the "Backend" base class.
    """
    def __init__(self, mapping):
        """
        Initialise router backend.

        @type mapping: dictionary
        @param mapping: dictionary of mountpoint -> backend mappings
        """
        self.mapping = [(mountpoint.rstrip('/'), backend) for mountpoint, backend in mapping.iteritems()]

    def _get_backend(self, itemname):
        for mountpoint, backend in self.mapping:
            if itemname.startswith(mountpoint):
                lstrip = mountpoint and len(mountpoint)+1 or 0
                return backend, itemname[lstrip:]
        raise NoMatchingBackend("No matching backend found for: %r" % itemname)

    def iteritems(self):
        for mountpoint, backend in self.mapping:
            for item in backend.iteritems():
                yield item # XXX item does not know its full name

    def get_item(self, itemname):
        backend, itemname = self._get_backend(itemname)
        return backend.get_item(itemname) # XXX item does not know its full name

    def create_item(self, itemname):
        """
        Creates an item with a given itemname. If that item already exists,
        raise an exception.

        @type itemname: unicode
        @param itemname: Name of the item we want to create.
        @rtype: item object
        @raise ItemAlreadyExistsError: The item you were trying to create already exists.
        """
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Itemnames must have string type, not %s" % (type(itemname)))

        backend, itemname = self._get_backend(itemname)
        return backend.create_item(itemname)  # XXX item does not know it's full name
