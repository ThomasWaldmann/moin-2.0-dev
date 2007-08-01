"""
    MoinMoin external interfaces

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.

    TODO: acl checking
"""

import UserDict

from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, BackendError, LockingError
from MoinMoin.storage.interfaces import DataBackend, MetadataBackend, ACL, EDIT_LOCK_TIMESTAMP, EDIT_LOCK_USER, DELETED, SIZE


class ItemCollection(UserDict.DictMixin, object):
    """
    The ItemCollection class realizes the access to the stored Items via the
    correct backend and maybe caching.
    """

    log_pos = None

    def __init__(self, backend, user=None):
        """
        Initializes the proper StorageBackend.
        """
        self._backend = backend
        self._user = user

        self._items = None

    def __contains__(self, name):
        """
        Checks if an Item exists.
        """
        return self._backend.has_item(name)

    def __getitem__(self, name):
        """
        Loads an Item.
        """
        backend = self._backend.has_item(name)
        if backend:
            return Item(name, backend, self._user)
        else:
            raise NoSuchItemError(_("No such item %r.") % name)

    def __delitem__(self, name):
        """
        Deletes an Item.
        """
        self._backend.remove_item(name)
        self._items = None

    def keys(self, filters=None):
        """
        Returns a list of all item names. With filters you can add
        filtering stuff which is described more detailed in
        StorageBackend.list_items(...).
        """
        if filters is None:
            return self.items[:]
        else:
            return self._backend.list_items(filters)[:]

    def new_item(self, name):
        """
        Returns a new Item with the given name.
        """
        self._backend.create_item(name)
        self._items = None
        return self[name]

    def rename_item(self, name, newname):
        """
        Renames an Item.
        """
        self._backend.rename_item(name, newname)
        self._items = None

    def copy_item(self, name, newname):
        """
        Copies an Item.
        """
        if newname == name:
            raise BackendError(_("Copy failed because name and newname are equal."))

        if not newname:
            raise BackendError(_("You cannot copy to an empty item name."))

        if newname in self.items:
            raise BackendError(_("Copy failed because an item with name %r already exists.") % newname)

        if not name in self.items:
            raise NoSuchItemError(_("Copy failed because there is no item with name %r.") % name)

        newitem = self.new_item(newname)
        newitem.lock = True

        olditem = self[name]

        for revno in olditem:
            newrev = newitem.new_revision(revno)
            oldrev = olditem[revno]

            newrev.data.write(oldrev.data.read())
            newrev.data.close()
            oldrev.data.close()

            for key, value in oldrev.metadata.iteritems():
                newrev.metadata[key] = value
            newrev.metadata.save()

        newitem.lock = False

        self._items = None

    def get_items(self):
        """
        Lazy load items.
        """
        if self._items is None:
            self._items = self._backend.list_items()
        return self._items

    items = property(get_items)


class Item(UserDict.DictMixin, object):
    """
    The Item class represents a StorageItem. This Item has a name and revisions.
    An Item can be anything MoinMoin must save, e.g. Pages, Attachements or
    Users. A list of revision numbers is only loaded on access. Via Item[0]
    you can access the last revision. The specified Revision is only loaded on
    access as well. On every access the ACLs will be checked.
    """

    def __init__(self, name, backend, userobj):
        """
        Initializes the Item with the required parameters.
        """
        self.name = name

        self._backend = backend
        self._userobj = userobj

        self._lock = False

        self.reset()

    def reset(self):
        """
        Reset the lazy loaded stuff which is dependend on adding/removing revisions.
        """
        self._revisions = None
        self._revision_objects = dict()
        self._current = None
        self._acl = None
        self._edit_lock = None
        self._metadata = None

    def __contains__(self, revno):
        """
        Checks if a Revision with the given revision number exists.
        """
        return self._backend.has_revision(self.name, revno)

    def __getitem__(self, revno):
        """
        Returns the revision specified by a revision number (LazyLoaded).
        """
        if revno == 0:
            revno = self.current

        try:
            return self._revision_objects[revno]
        except KeyError:
            if self._backend.has_revision(self.name, revno):
                rev = Revision(revno, self)
                self._revision_objects[revno] = rev
                return rev
            else:
                raise NoSuchRevisionError(_("Revision %r of item %r does not exist.") % (revno, self.name))

    def __delitem__(self, revno):
        """
        Deletes the Revision specified by the given revision number.
        """
        self._check_lock()
        self.reset()
        self._backend.remove_revision(self.name, revno)

    def keys(self):
        """
        Returns a sorted (highest first) list of all real revision numbers.
        """
        return self.revisions[:]

    def new_revision(self, revno=0):
        """
        Creates and returns a new revision with the given revision number.
        If the revision number is None the next possible number will be used.
        """
        self._check_lock()
        self.reset()
        rev = self._backend.create_revision(self.name, revno)
        return self[rev]

    def get_metadata(self):
        """
        Lazy load metadata.
        """
        if self._metadata is None:
            self._metadata = Revision(-1, self).metadata
        return self._metadata

    metadata = property(get_metadata)

    def get_revisions(self):
        """
        Lazy load the revisions.
        """
        if self._revisions is None:
            self._revisions = self._backend.list_revisions(self.name)
        return self._revisions

    revisions = property(get_revisions)

    def get_current(self):
        """
        Lazy load the current revision no.
        """
        if self._current is None:
            self._current = self._backend.current_revision(self.name)
        return self._current

    current = property(get_current)

    def get_acl(self):
        """
        Get the acl property.
        """
        if self._acl is None:
            from MoinMoin.security import AccessControlList
            self._acl = AccessControlList(self._backend._cfg, self[0].acl)
        return self._acl

    acl = property(get_acl)

    def get_edit_lock(self):
        """
        Get the lock property.
        It is a tuple containing the timestamp of the lock and the user.
        """
        if self._edit_lock is None:
            if EDIT_LOCK_TIMESTAMP in self.metadata and EDIT_LOCK_USER in self.metadata:
                self._edit_lock = (True, long(self.metadata[EDIT_LOCK_TIMESTAMP]), self.metadata[EDIT_LOCK_USER])
            else:
                self._edit_lock = False, 0, None
        return self._edit_lock

    def set_edit_lock(self, edit_lock):
        """
        Set the lock property.
        It must either be False or a tuple containing timestamp and user.
        You still have to call item.metadata.save() to actually save the change.
        """
        self._check_lock()

        if not edit_lock:
            del self.metadata[EDIT_LOCK_TIMESTAMP]
            del self.metadata[EDIT_LOCK_USER]
        elif isinstance(edit_lock, tuple) and len(edit_lock) == 2:
            self.metadata[EDIT_LOCK_TIMESTAMP] = str(edit_lock[0])
            self.metadata[EDIT_LOCK_USER] = edit_lock[1]
        else:
            raise ValueError(_("Lock must be either False or a tuple containing timestamp and user."))
        self._edit_lock = None

    edit_lock = property(get_edit_lock, set_edit_lock)

    def get_lock(self):
        """
        Checks if the item is locked.
        """
        return self._lock

    def set_lock(self, lock):
        """
        Set the item lock state.
        """
        if lock:
            self._backend.lock(self.name)
            self.reset()
        else:
            self._backend.unlock(self.name)
        self._lock = lock

    lock = property(get_lock, set_lock)

    def _check_lock(self):
        """
        Checks whether the item is locked and raises an exception otherwise.
        """
        if not self.lock:
            raise LockingError(_("This item currently not locked so you can only use it readonly."))


class Revision(object):
    """
    A Revision contains the data and metadata for one revision of the Item. The
    Metadata and Data classes will be created when the revision is created, but
    they take care that their content is loaded lazily. On every access the ACLs
    will be checked.
    """

    def __init__(self, revno, item):
        """
        Initalizes the Revision with the required parameters.
        """
        self.revno = revno
        self.item = item

        self._data = None
        self._metadata  = None

    def get_metadata(self):
        """
        Lazy load metadata.
        """
        if self._metadata is None:
            metadata = self.item._backend.get_metadata_backend(self.item.name, self.revno)
            if self.item.lock:
                self._metadata = metadata
            else:
                self._metadata = ReadonlyMetadata(metadata, LockingError, _("This item is currently readonly."))
        return self._metadata

    metadata = property(get_metadata)

    def get_data(self):
        """
        Lazy load metadata.
        """
        if self._data is None:
            data = self.item._backend.get_data_backend(self.item.name, self.revno)
            if self.item.lock:
                self._data = data
            else:
                self._data = ReadonlyData(data, LockingError, _("This item is currently readonly."))
        return self._data

    data = property(get_data)

    def get_acl(self):
        """
        ACL Property.
        """
        acl = self.metadata.get(ACL, [])
        if type(acl) != list:
            acl = [acl]
        return acl

    def set_acl(self, value):
        """
        ACL Property.
        """
        self.metadata[ACL] = value

    acl = property(get_acl, set_acl)

    def get_deleted(self):
        """
        Deleted Property.
        """
        return self.metadata.get(DELETED, False)

    def set_deleted(self, value):
        """
        Deleted Property.
        """
        self.metadata[DELETED] = value

    deleted = property(get_deleted, set_deleted)

    def get_size(self):
        """
        Size Property.
        """
        size = self.metadata.get(SIZE, 0L)
        if not size:
            size = len(self.data.read())
            self.data.close()
        return size

    size = property(get_size)

    def __getattr__(self, name):
        """
        Get edit lock values.
        """
        if name in ('mtime', 'action', 'addr', 'hostname', 'userid', 'extra', 'comment'):
            return self.metadata.get("edit_log_" + name, "")
        raise AttributeError, name


class Decorator(object):
    """
    Decorator class.
    """

    def __init__(self, obj, exception, message):
        """"
        Init stuff.
        """
        self._obj = obj
        self._exception = exception
        self._message = message

    def raiseException(self, size=None):
        """
        Raises an exception
        """
        raise self._exception(self._message)

    def __getattribute__(self, name):
        """
        Returns the method.
        """
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return getattr(self._obj, name)


class ReadonlyMetadata(Decorator):
    """
    Readonly Metadata implementation.
    """

    __implements__ = MetadataBackend

    def __getattribute__(self, name):
        """
        Returns the name.
        """
        if name in ["__contains__", "__getitem__", "keys"]:
            return getattr(self._obj, name)
        elif name in ["__setitem__", "__delitem__", "save"]:
            return self.raiseException
        else:
            return Decorator.__getattribute__(self, name)


class WriteonlyMetadata(Decorator):
    """
    Writeonly Metadata implementation.
    """

    __implements__ = MetadataBackend

    def __getattribute__(self, name):
        """
        Returns the name.
        """
        if name in ["__contains__", "__getitem__", "keys"]:
            return self.raiseException
        elif name in ["__setitem__", "__delitem__", "save"]:
            return getattr(self._obj, name)
        else:
            return Decorator.__getattribute__(self, name)


class ReadonlyData(Decorator):
    """
    This class implements read only access to the DataBackend.
    """

    __implements__ = DataBackend

    def __getattribute__(self, name):
        """
        Returns the name.
        """
        if name in ["read", "seek", "tell", "close"]:
            return getattr(self._obj, name)
        elif name == "write":
            return self.raiseException
        else:
            return Decorator.__getattribute__(self, name)


class WriteonlyData(Decorator):
    """
    This class implements write only access to the DataBackend.
    """

    __implements__ = DataBackend

    def __getattribute__(self, name):
        """
        Returns the name.
        """
        if name in ["read", "seek", "tell", "close"]:
            return self.raiseException
        elif name == "write":
            return getattr(self._obj, name)
        else:
            return Decorator.__getattribute__(self, name)


_ = lambda x: x
