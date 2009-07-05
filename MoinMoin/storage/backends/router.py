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

    def _get_backend(self, itemname):
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Item names must have string type, not %s" % (type(itemname)))

        for mountpoint, backend in self.mapping:
            if itemname == mountpoint or itemname.startswith(mountpoint and mountpoint + '/' or ''):
                lstrip = mountpoint and len(mountpoint)+1 or 0
                return backend, itemname[lstrip:], itemname[:lstrip]
        # This point should never be reached since at least the last mountpoint, '/', should
        # contain the item.
        raise AssertionError('No backend found for %s. Available backends: %r' % (itemname, self.mapping))

    def _iteritems(self):
        """
        This only iterates over all non-user and non-trash items. We don't
        want them to turn up in history.
        """
        for mountpoint, backend in self.mapping:
            mountpoint = mountpoint + "/" if mountpoint else mountpoint
            for item in backend.iteritems():
                yield RouterItem(item, mountpoint, item.name, self)

    def iteritems(self):
        """
        Iterate over all items, even users. (Necessary for traversal.)
        """
        for item in self._iteritems():
            yield item
        for user in self.user_backend.iteritems():
            yield user

    def history(self, reverse=True):
        """
        Just the basic, slow implementation of history with the difference
        that we don't iterate over users/trash.
        """
        revs = []
        for item in self._iteritems():
            for revno in item.list_revisions():
                rev = item.get_revision(revno)
                revs.append((rev.timestamp, rev.revno, item.name, ))
        revs.sort() # from oldest to newest
        if reverse:
            revs.reverse()
        for ts, revno, name in revs:
            item = self.get_item(name)
            yield item.get_revision(revno)

    def has_item(self, itemname):
        # While we could use the inherited, generic implementation
        # it is generally advised to override this method.
        # Thus, we pass the call down.
        backend, itemname, mountpoint = self._get_backend(itemname)
        return backend.has_item(itemname)

    def get_item(self, itemname):
        backend, itemname, mountpoint = self._get_backend(itemname)
        return RouterItem(backend.get_item(itemname), mountpoint, itemname, self)

    def create_item(self, itemname):
        backend, itemname, mountpoint = self._get_backend(itemname)
        return RouterItem(backend.create_item(itemname), mountpoint, itemname, self)


class RouterItem(object):
    """
    Router Item - Wraps 'real' storage items to make them aware of their full name.

    Items that the RouterBackend stores do not know their full name since the backend
    they belong to is looked up from a list for a given mountpoint and only the itemname
    itself (without leading mountpoint) is given to the specific backend.
    This is done so as to allow mounting a given backend at a different mountpoint.
    The problem with that is, of course, that items do not know their full name if they
    are retrieved via the specific backends directly. Thus, it is neccessary to wrap the
    items returned from those specific backends in an instance of this RouterItem class.
    This makes sure that an item in a specific backend only knows it's local name (as it
    should be; this allows mounting at a different place without renaming all items) but
    items that the RouterBackend creates or gets know their fully qualified name.

    In order to achieve this, we must mimic the Item interface here. In addition to that,
    a backend implementor may have decided to provide additional methods on his Item class.
    We can not know that here, ahead of time. We must redirect any attribute lookup to the
    encapsulated item, hence, and only intercept calls that are related to the item name.
    To do this, we store the wrapped item and redirect all calls via this classes __getattr__
    method. For this to work, RouterItem *must not* inherit from Item, because otherwise
    the attribute would be looked up on the abstract base class, which certainly is not what
    we want.
    Furthermore there's a problem with __getattr__ and new-style classes' special methods
    which can be looked up here:
    http://docs.python.org/reference/datamodel.html#special-method-lookup-for-new-style-classes
    """
    def __init__(self, item, mountpoint, itemname, backend):
        self._item = item
        self._mountpoint = mountpoint
        self._itemname = itemname
        self._get_backend = backend._get_backend

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
        backend, itemname, mountpoint = self._get_backend(newname)
        if mountpoint != self._mountpoint:
            # Mountpoint changed! That means we have to copy the item over.
            assert not backend.has_item(itemname)  # TODO handle sanely
            new_item = backend.create_item(itemname)
            for revno in self._item.list_revisions():
                oldrev = self._item.get_revision(revno)
                newrev = new_item.create_revision(revno)
                for key, value in oldrev:
                    newrev[key] = value
                newrev.write(oldrev.read())        # TODO read buffered
                new_item.commit()

            self._item = new_item
            self._mountpoint = mountpoint
            self._itemname = itemname
            # TODO 'delete' old item

        else:
            # Mountpoint didn't change
            self._item.rename(itemname)
            self._itemname = itemname
