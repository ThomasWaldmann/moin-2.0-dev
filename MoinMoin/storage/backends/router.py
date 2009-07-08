# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - routing backend

    You can use this backend to route requests to different backends
    depending on the item name. I.e., you can specify mountpoints and
    map them to different backends. E.g. you could route all your items
    to an FSBackend and only items below hg/<youritemnamehere> go into
    a MercurialBackend and similarly tmp/<youritemnamehere> is for
    temporary items in a MemoryBackend() that are discarded when the
    process terminates.

    @copyright: 2008 MoinMoin:ThomasWaldmann,
                2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import re

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.error import ConfigurationError

from MoinMoin.storage import Backend
from MoinMoin.storage.backends import copy_item

from UserDict import DictMixin


class RouterBackend(Backend):
    """
    Router Backend - routes requests to different backends depending
    on the item name.

    For method docstrings, please see the "Backend" base class.
    """
    def __init__(self, mapping, users):
        """
        Initialise router backend.

        The mapping given must satisfy the following criteria:
            * Order matters.
            * Mountpoints are just item names, including the special '' (empty)
              root item name. A trailing '/' of a mountpoint will be ignored.
            * There *must* be a backend with mountpoint '' (or '/') at the very
              end of the mapping. That backend is then used as root, which means
              that all items that don't lie in the namespace of any other
              backend are stored there.

        The user backend provided must be a regular backend.

        @type mapping: list of tuples of mountpoint -> backend mappings
        @param mapping: [(mountpoint, backend), ...]
        @type users: subclass of MoinMoin.storage.Backend
        @param users: The backend where users are stored.
        """
        self.user_backend = users
        self.mapping = [(mountpoint.rstrip('/'), backend) for mountpoint, backend in mapping]

        if not mapping or self.mapping[-1][0] != '':
            raise ConfigurationError("You must specify a backend for '/' or '' as the last backend in the mapping.")
        if not users:
            raise ConfigurationError("You must specify a backend for user storage.")


    def _get_backend(self, itemname):
        """
        For a given fully-qualified itemname (i.e. something like Company/Bosses/Mr_Joe)
        find the backend it belongs to (given by this instance's mapping), the local
        itemname inside that backend and the mountpoint of the backend.

        Note: Internally (i.e. in all Router* classes) we always use the normalized
              item name for consistency reasons.

        @type itemname: str
        @param itemname: fully-qualified itemname
        @return: tuple of (backend, itemname, mountpoint)
        """
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Item names must have string type, not %s" % (type(itemname)))

        for mountpoint, backend in self.mapping:
            if itemname == mountpoint or itemname.startswith(mountpoint and mountpoint + '/' or ''):
                lstrip = mountpoint and len(mountpoint)+1 or 0
                return backend, itemname[lstrip:], mountpoint
        # This point should never be reached since at least the last mountpoint, '/', should
        # contain the item.
        raise AssertionError('No backend found for %s. Available backends: %r' % (itemname, self.mapping))

    def _iteritems(self):
        """
        This only iterates over all non-user items. We don't want them to turn up in history.
        """
        for mountpoint, backend in self.mapping:
            for item in backend.iteritems():
                yield RouterItem(item, mountpoint, item.name, self)

    def iteritems(self):
        """
        Iterate over all items, even users. (Necessary for traversal.)

        @see: Backend.iteritems.__doc__
        """
        for item in self._iteritems():
            yield item
        for user in self.user_backend.iteritems():
            yield user

    def history(self, reverse=True):
        """
        Just the basic, slow implementation of history with the difference
        that we don't iterate over users. For traversal of the items
        of all the backends defined in the mapping, use self.iteritems.

        @see: Backend.history.__doc__
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
            rev = item.get_revision(revno)
            yield RouterRevision(item, rev)

    def has_item(self, itemname):
        """
        @see: Backend.has_item.__doc__
        """
        # While we could use the inherited, generic implementation
        # it is generally advised to override this method.
        # Thus, we pass the call down.
        backend, itemname, mountpoint = self._get_backend(itemname)
        return backend.has_item(itemname)

    def get_item(self, itemname):
        """
        @see: Backend.get_item.__doc__
        """
        backend, itemname, mountpoint = self._get_backend(itemname)
        return RouterItem(backend.get_item(itemname), mountpoint, itemname, self)

    def create_item(self, itemname):
        """
        @see: Backend.create_item.__doc__
        """
        backend, itemname, mountpoint = self._get_backend(itemname)
        return RouterItem(backend.create_item(itemname), mountpoint, itemname, self)


class RouterItem(object):
    """
    Router Item - Wraps 'real' storage items to make them aware of their full name.

    Items stored in the backends managed by the RouterBackend do not know their full
    name since the backend they belong to is looked up from a list for a given
    mountpoint and only the itemname itself (without leading mountpoint) is given to
    the specific backend.
    This is done so as to allow mounting a given backend at a different mountpoint.
    The problem with that is, of course, that items do not know their full name if they
    are retrieved via the specific backends directly. Thus, it is neccessary to wrap the
    items returned from those specific backends in an instance of this RouterItem class.
    This makes sure that an item in a specific backend only knows its local name (as it
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
        """
        @rtype: str
        @return: the item's fully-qualified name
        """
        mountpoint = self._mountpoint
        if mountpoint:
            mountpoint += '/'
        return mountpoint + self._itemname

    def __setitem__(self, key, value):
        """
        @see: Item.__setitem__.__doc__
        """
        return self._item.__setitem__(key, value)

    def __delitem__(self, key):
        """
        @see: Item.__delitem__.__doc__
        """
        return self._item.__delitem__(key)

    def __getitem__(self, key):
        """
        @see: Item.__getitem__.__doc__
        """
        return self._item.__getitem__(key)

    def __getattr__(self, attr):
        """
        Redirect all attribute lookups to the item that is proxied by this instance.
        """
        # Note: this would fail if we subclassed Item
        return getattr(self._item, attr)

    def rename(self, newname):
        """
        For intra-backend renames, this is the same as the normal Item.rename
        method.
        For inter-backend renames, this *moves* the complete item over to the
        new backend, possibly with a new item name.

        @see: Item.rename.__doc__
        """
        # XXX copy first, rename later. improve
        old_name = self._item.name
        backend, itemname, mountpoint = self._get_backend(newname)
        if mountpoint != self._mountpoint:
            # Mountpoint changed! That means we have to copy the item over.
            converts, skips, fails = copy_item(self._item, backend, verbose=False)
            assert len(converts) == 1
            new_item = backend.get_item(old_name)
            new_item.rename(itemname)

            self._item = new_item
            self._mountpoint = mountpoint
            self._itemname = itemname
            # TODO 'delete' old item

        else:
            # Mountpoint didn't change
            self._item.rename(itemname)
            self._itemname = itemname

    def create_revision(self, revno):
        """
        In order to make item name lookups via revision.item.name work, we need
        to wrap the revision here.

        @see: Item.create_revision.__doc__
        """
        rev = self._item.create_revision(revno)
        return RouterRevision(self, rev)

    def get_revision(self, revno):
        """
        In order to make item name lookups via revision.item.name work, we need
        to wrap the revision here.

        @see: Item.get_revision.__doc__
        """
        rev = self._item.get_revision(revno)
        return RouterRevision(self, rev)


class RouterRevision(DictMixin):
    """
    This classes sole purpose is to make item name lookups via revision.item.name
    work return the item's fully-qualified item name.

    It needs to subclass DictMixin to allow the `metadata key in rev` syntax.
    If we'd inherit from Revision we'd need to redirect all methods manually
    since __getattr__ wouldn't work anymore. See RouterItem.__doc__ for an
    explanation.
    """
    def __init__(self, router_item, revision):
        self._item = router_item
        self._revision = revision

    @property
    def item(self):
        """
        Here we have to return the RouterItem, which in turn wraps the real item
        and provides it with its full name that we need for the rev.item.name lookup.

        @see: Revision.item.__doc__
        """
        assert isinstance(self._item, RouterItem)
        return self._item

    def __setitem__(self, key, value):
        """
        We only need to redirect this manually here because python doesn't do that
        in combination with __getattr__. See RouterBackend.__doc__ for an explanation.

        As this class wraps generic Revisions, this may very well result in an exception
        being raised if the wrapped revision is a StoredRevision.
        """
        return self._revision.__setitem__(key, value)

    def __delitem__(self, key):
        """
        @see: RouterRevision.__setitem__.__doc__
        """
        return self._revision.__delitem__(key)

    def __getitem__(self, key):
        """
        @see: RouterRevision.__setitem__.__doc__
        """
        return self._revision.__getitem__(key)

    def __getattr__(self, attr):
        """
        Redirect all attribute lookups to the revision that is proxied by this instance.
        """
        return getattr(self._revision, attr)

