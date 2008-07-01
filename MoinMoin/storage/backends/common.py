"""
    Common functionality and helper functions that all backends
    can profit from.

    @copyright: 2007 MoinMoin:HeinrichWendel,
                2008 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""


from MoinMoin.storage.error import BackendError, NoSuchItemError, NoSuchRevisionError
from MoinMoin.storage.interfaces import StorageBackend


class CommonBackend(object):
    """
    This class implements the MoinMoin 1.6 compatible Page Storage Stuff.
    """

    __implements__ = StorageBackend

    def __init__(self, name, other):
        """
        Init stuff.
        """
        self.name = name
        self._other = other

    def __getattr__(self, name):
        """
        Get attribute from other backend if we don't have one.
        """
        return getattr(self._other, name)

    def has_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_item
        """
        if self._other.has_item(name):
            return self
        return None

    def create_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.create_item
        """
        try:
            self._other.create_item(name)
            return self
        except Exception, err:
            if self._other.has_item(name):
                raise BackendError(_("Item %r already exists.") % name)
            else:
                _handle_error(self, err, name, None)

    def remove_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.remove_item
        """
        try:
            self._other.remove_item(name)
        except Exception, err:
            _handle_error(self, err, name, None)

    def rename_item(self, name, newname):
        # XXX These tests do not really belong here, on a backend level
        #     renaming an item to itself should be a no-op, but this trips
        #     up the broken test suite.
        if name == newname:
            raise BackendError(_("Failed to rename item because name and newname are equal."))

        # Why not? And why check for this here of all places?
        if not newname:
            raise BackendError(_("You cannot rename to an empty item name."))

        # XXX This requires locking although that isn't actually necessary for rename_item
        if self.has_item(newname):
            raise BackendError(_("Failed to rename item because an item with name %r already exists.") % newname)

        return self._other.rename_item(name, newname)

    def current_revision(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.current_revision
        """
        try:
            return self._other.current_revision(name)
        except Exception, err:
            _handle_error(self, err, name)

    def list_revisions(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_revisions
        """
        try:
            return self._other.list_revisions(name)
        except Exception, err:
            _handle_error(self, err, name)

    def has_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_revision
        """
        try:
            return self._other.has_revision(name, revno)
        except Exception, err:
            _handle_error(self, err, name, revno)

    def create_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.create_revisions
        """
        if revno <= -1:
            raise BackendError(_("Invalid revisions number %r") % revno)

        try:
            self._other.create_revision(name, revno)
        except Exception, err:
            _handle_error(self, err, name, revno)

    def remove_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.remove_revisions
        """
        if revno <= -1:
            raise BackendError(_("Invalid revisions number %r") % revno)

        try:
            self._other.remove_revision(name, revno)
        except Exception, err:
            _handle_error(self, err, name, revno)


def _handle_error(backend, err, name, revno=None):
    """
    Handle error messages.
    """
    if not backend.has_item(name):
        raise NoSuchItemError(_("Item %r does not exist.") % name)
    elif revno is not None and revno != -1 and not backend.has_revision(name, revno):
        raise NoSuchRevisionError(_("Revision %r of item %r does not exist.") % (revno, name))
    else:
        raise err


def _get_metadata(backend, item, revnos):
    """
    Returns the metadata of an item and the specified revision numbers.
    """
    metadata = dict()
    for revno in revnos:
        if revno == 0:
            revno = backend.current_revision(item)
        if revno != 0:
            metadata_rev = backend.get_metadata_backend(item, revno)
            metadata.update(metadata_rev)
    return metadata


class _get_item_metadata_cache:
    """
    Helps implement filtering: If no search term needs the
    metadata, it won't be loaded, but if multiple need it
    then it will still be loaded only once.
    """
    def __init__(self, backend, item):
        self.backend = backend
        self.item = item
        self._cached = None

    def __call__(self):
        if self._cached is None:
            self._cached = (_get_metadata(self.backend, self.item, [-1]),
                            _get_metadata(self.backend, self.item, [0]))
        return self._cached

_ = lambda x: x
