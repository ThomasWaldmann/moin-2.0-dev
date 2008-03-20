"""
    Common functionality and helper functions that all backends
    can profit from.

    @copyright: 2007 MoinMoin:HeinrichWendel,
                2008 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""


from MoinMoin.storage.error import BackendError, NoSuchItemError, NoSuchRevisionError
from MoinMoin.storage.interfaces import StorageBackend
from MoinMoin.storage.external import UNDERLAY, DELETED


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
        """
        @see MoinMoin.storage.interfaces.StorageBackend.rename_item
        """
        if name == newname:
            raise BackendError(_("Failed to rename item because name and newname are equal."))

        if not newname:
            raise BackendError(_("You cannot rename to an empty item name."))

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


def check_filter(backend, item, filters, filterfn):
    """
    Check if a given item matches the given filters.
    """

    if not filters and not filterfn:
        return True

    metadata = _get_metadata(backend, item, [-1, 0])

    if filters:
        for key, value in filters.iteritems():
            if key == UNDERLAY:
                if value != backend.is_underlay:
                    return False
            elif key == DELETED:
                # items w/o DELETED member are not deleted
                deleted = metadata.get(DELETED, False)
                if deleted != value:
                    return False
            elif key in metadata:
                val = metadata[key]
                if isinstance(val, (tuple, list)):
                    vals = val
                elif isinstance(val, dict):
                    vals = val.keys()
                else:
                    assert isinstance(val, unicode)
                    vals = [val]
                if not value in vals:
                    return False
            else:
                return False

    if filterfn:
        return filterfn(item, metadata)

    return True

_ = lambda x: x
