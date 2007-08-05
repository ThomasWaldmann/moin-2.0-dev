"""
    Common functionality that all backends can profit from.

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""


from MoinMoin.storage.error import BackendError, NoSuchItemError, NoSuchRevisionError, StorageError
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

    def _call(self, method, message, *arg, **kwarg):
        """
        Call a function an use _handle_error if required.
        """
        try:
            return getattr(self._other, method)(*arg, **kwarg)
        except Exception, err:
            if len(arg) > 1:
                revno = arg[1]
            else:
                revno = None
            _handle_error(self, err, arg[0], revno, message=message)

    def _get_revno(self, item, revno):
        """
        Get the correct revno with correct error handling.
        """
        if revno == 0:
            try:
                revno = self.current_revision(item, includeEmpty=True)
            except Exception, err:
                _handle_error(self, err, item, revno, message=_("Failed to get current revision for item") % item)
        return revno

    def list_items(self, filters=None):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_items
        """
        return self._call("list_items", _("Failed to list items"), filters)

    def has_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_item
        """
        if self._call("has_item", _("Failed check if item %r exists.") % name, name):
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
                _handle_error(self, err, name, message=_("Failed to create item %r.") % name)

    def remove_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.remove_item
        """
        return self._call("remove_item", _("Failed to remove item %r.") % name, name)

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

        return self._call("rename_item", _("Failed to rename item %r.") % name, name, newname)

    def list_revisions(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_revisions
        """
        return self._call("list_revisions", _("Failed to list revisions of item %r.") % name, name)

    def current_revision(self, name, includeEmpty=False):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.current_revision
        """
        return self._call("current_revision", _("Failed to get current revision for item %r.") % name, name, includeEmpty)

    def has_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_revision
        """
        revno = self._get_revno(name, revno)

        return self._call("has_revision", _("Failed to check if revision %r for item %r exists.") % (revno, name), name, revno)

    def create_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.create_revisions
        """
        if revno == 0:
            revno = self._get_revno(name, revno) + 1

        self._call("create_revision", _("Failed to create revision %r for item %r.") % (revno, name), name, revno)

        return revno

    def remove_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.remove_revisions
        """
        revno = self._get_revno(name, revno)
        self._call("remove_revision", _("Failed to remove revision %r for item %r.") % (revno, name), name, revno)
        return revno

    def get_data_backend(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.get_data_backend
        """
        revno = self._get_revno(name, revno)

        return self._call("get_data_backend", _("Failed to get data backend with revision %r for item %r.") % (revno, name), name, revno)

    def get_metadata_backend(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.get_metadata_backend
        """
        revno = self._get_revno(name, revno)

        return self._call("get_metadata_backend", _("Failed to get metadata backend with revision %r for item %r.") % (revno, name), name, revno)

    def lock(self, identifier, timeout=1, lifetime=60):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.lock
        """
        return self._call("lock", _("Failed to create a log for %r.") % identifier, identifier, timeout, lifetime)

    def unlock(self, identifier):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.unlock
        """
        return self._call("unlock", _("Failed to create remove the log for %r.") % identifier, identifier)


def _handle_error(backend, err, name, revno=None, message=""):
    """
    Handle error messages.
    """
    if isinstance(err, StorageError):
        raise err
    elif not backend.has_item(name):
        raise NoSuchItemError(_("Item %r does not exist.") % name)
    elif revno is not None and revno != -1 and not backend.has_revision(name, revno):
        raise NoSuchRevisionError(_("Revision %r of item %r does not exist.") % (revno, name))
    else:
        raise StorageError(message)


def _get_metadata(backend, item, revnos):
    """
    Returns the metadata of an item and the specified revision numbers.
    """
    metadata = dict()
    for revno in revnos:
        if revno == 0:
            revno = backend.current_revision(item, includeEmpty=True)
        metadata_rev = backend.get_metadata_backend(item, revno)
        metadata.update(metadata_rev)
    return metadata


def get_bool(arg):
    arg = arg.lower()
    if arg in [u'1', u'true', u'yes']:
        return True
    return False


_ = lambda x: x
