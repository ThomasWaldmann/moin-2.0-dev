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
        self.backend = backend
        self.user = user

        self.__items = None

    def __contains__(self, name):
        """
        Checks if an Item exists.
        """
        return self.backend.has_item(name)

    def __getitem__(self, name):
        """
        Loads an Item.
        """
        backend = self.backend.has_item(name)
        if backend:
            return Item(name, backend, self.user)
        else:
            raise NoSuchItemError(_("No such item %r.") % name)

    def __delitem__(self, name):
        """
        Deletes an Item.
        """
        self.backend.remove_item(name)
        self.__items = None

    def keys(self, filters=None):
        """
        Returns a list of all item names. With filters you can add
        filtering stuff which is described more detailed in
        StorageBackend.list_items(...).
        """
        if filters is None:
            return self.items
        else:
            return self.backend.list_items(filters)

    def new_item(self, name):
        """
        Returns a new Item with the given name.
        """
        self.backend.create_item(name)
        self.__items = None
        return self[name]

    def rename_item(self, name, newname):
        """
        Renames an Item.
        """
        self.backend.rename_item(name, newname)
        self.__items = None

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

        self.__items = None

    def get_items(self):
        """
        Lazy load items.
        """
        if self.__items is None:
            self.__items = self.backend.list_items()
        return self.__items

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
        self.backend = backend
        self.userobj = userobj

        self.__lock = False

        self.reset()

    def reset(self):
        """
        Reset the lazy loaded stuff which is dependend on adding/removing revisions.
        """
        self.__revisions = None
        self.__revision_objects = dict()
        self.__current = None
        self.__acl = None
        self.__edit_lock = None
        self.__metadata = None

    def __contains__(self, revno):
        """
        Checks if a Revision with the given revision number exists.
        """
        return self.backend.has_revision(self.name, revno)

    def __getitem__(self, revno):
        """
        Returns the revision specified by a revision number (LazyLoaded).
        """
        if revno == 0:
            revno = self.current

        try:
            return self.__revision_objects[revno]
        except KeyError:
            if self.backend.has_revision(self.name, revno):
                rev = Revision(revno, self)
                self.__revision_objects[revno] = rev
                return rev
            else:
                raise NoSuchRevisionError(_("Revision %r of item %r does not exist.") % (revno, self.name))

    def __delitem__(self, revno):
        """
        Deletes the Revision specified by the given revision number.
        """
        self._check_lock()
        self.reset()
        self.backend.remove_revision(self.name, revno)

    def keys(self):
        """
        Returns a sorted (highest first) list of all real revision numbers.
        """
        return self.revisions

    def new_revision(self, revno=0):
        """
        Creates and returns a new revision with the given revision number.
        If the revision number is None the next possible number will be used.
        """
        self._check_lock()
        self.reset()
        rev = self.backend.create_revision(self.name, revno)
        return self[rev]

    def get_metadata(self):
        """
        Lazy load metadata.
        """
        if self.__metadata is None:
            self.__metadata = Revision(-1, self).metadata
        return self.__metadata

    metadata = property(get_metadata)

    def get_revisions(self):
        """
        Lazy load the revisions.
        """
        if self.__revisions is None:
            self.__revisions = self.backend.list_revisions(self.name)
        return self.__revisions

    revisions = property(get_revisions)

    def get_current(self):
        """
        Lazy load the current revision no.
        """
        if self.__current is None:
            self.__current = self.backend.current_revision(self.name)
        return self.__current

    current = property(get_current)

    def get_acl(self):
        """
        Get the acl property.
        """
        if self.__acl is None:
            from MoinMoin.security import AccessControlList
            self.__acl = AccessControlList(self.backend.cfg, self[0].acl)
        return self.__acl

    acl = property(get_acl)

    def get_edit_lock(self):
        """
        Get the lock property.
        It is a tuple containing the timestamp of the lock and the user.
        """
        if self.__edit_lock is None:
            if EDIT_LOCK_TIMESTAMP in self.metadata and EDIT_LOCK_USER in self.metadata:
                self.__edit_lock = (True, long(self.metadata[EDIT_LOCK_TIMESTAMP]), self.metadata[EDIT_LOCK_USER])
            else:
                self.__edit_lock = False, 0, None
        return self.__edit_lock

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
        self.__edit_lock = None

    edit_lock = property(get_edit_lock, set_edit_lock)

    def get_lock(self):
        """
        Checks if the item is locked.
        """
        return self.__lock

    def set_lock(self, lock):
        """
        Set the item lock state.
        """
        if lock:
            self.backend.lock(self.name)
            self.reset()
        else:
            self.backend.unlock(self.name)
        self.__lock = lock

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

        self.reset()

    def reset(self):
        """
        Reset, you know what i mean?
        """
        self.__data = None
        self.__metadata  = None

        self.__acl = None
        self.__deleted = None
        self.__size = None

        for attr in ('mtime', 'action', 'addr', 'hostname', 'userid', 'extra', 'comment'):
            setattr(self, "__" + attr, None)

    def __getattribute__(self, name):
        """
        Get edit lock values.
        """
        if name in ('mtime', 'action', 'addr', 'hostname', 'userid', 'extra', 'comment'):
            if getattr(self, "__" + name) is None:
                setattr(self, "__" + name, self._get_value("edit_log_" + name, ""))
            return getattr(self, "__" + name)
        return object.__getattribute__(self, name)

    def get_metadata(self):
        """
        Lazy load metadata.
        """
        if self.__metadata is None:
            metadata = self.item.backend.get_metadata_backend(self.item.name, self.revno)
            if self.item.lock:
                self.__metadata = metadata
            else:
                self.__metadata = ReadonlyMetadata(metadata, LockingError, _("This item is currently readonly."))
        return self.__metadata

    metadata = property(get_metadata)

    def get_data(self):
        """
        Lazy load metadata.
        """
        if self.__data is None:
            data = self.item.backend.get_data_backend(self.item.name, self.revno)
            if self.item.lock:
                self.__data = data
            else:
                self.__data = ReadonlyData(data, LockingError, _("This item is currently readonly."))
        return self.__data

    data = property(get_data)

    def get_acl(self):
        """
        ACL Property.
        """
        if self.__acl is None:
            acl = self._get_value(ACL, [])
            if type(acl) != list:
                acl = [acl]
            self.__acl = acl
        return self.__acl

    def set_acl(self, value):
        """
        ACL Property.
        """
        self.metadata[ACL] = value
        self.__acl = None

    acl = property(get_acl, set_acl)

    def get_deleted(self):
        """
        Deleted Property.
        """
        if self.__deleted is None:
            self.__deleted = self._get_value(DELETED, False)
        return self.__deleted

    def set_deleted(self, value):
        """
        Deleted Property.
        """
        self.metadata[DELETED] = value
        self.__deleted = None

    deleted = property(get_deleted, set_deleted)

    def get_size(self):
        """
        Size Property.
        """
        if self.__size is None:
            size = self._get_value(SIZE, 0L)
            if not size:
                size = len(self.data.read())
                self.data.close()
            self.__size = size
        return self.__size

    size = property(get_size)

    def _get_value(self, key, default):
        """
        Returns a value from the metadata or the default if the value is not in the metadata.
        """
        try:
            value = self.metadata[key]
        except KeyError:
            value = default
        return value


class ReadonlyMetadata(MetadataBackend):
    """
    Readonly Metadata implementation.
    """

    def __init__(self, metadata, exception, message):
        """"
        Init stuff.
        """
        self._metadata = metadata
        self._exception = exception
        self._message = message

    def __contains__(self, key):
        """
        @see MoinMoin.storage.external.Metadata.__contains__
        """
        return key in self._metadata

    def __getitem__(self, key):
        """
        @see MoinMoin.storage.external.Metadata.__getitem__
        """
        return self._metadata[key]

    def __setitem__(self, key, value):
        """
        @see MoinMoin.storage.external.Metadata.__setitem__
        """
        raise self._exception(self._message)

    def __delitem__(self, key):
        """
        @see MoinMoin.storage.external.Metadata.__delitem__
        """
        raise self._exception(self._message)

    def keys(self):
        """
        @see MoinMoin.storage.external.Metadata.keys
        """
        return self._metadata.keys()

    def save(self):
        """
        @see MoinMoin.storage.external.Metadata.save
        """
        raise self._exception(self._message)


class WriteonlyMetadata(MetadataBackend):
    """
    Writeonly Metadata implementation.
    """

    def __init__(self, metadata, exception, message):
        """"
        Init stuff.
        """
        self._metadata = metadata
        self._exception = exception
        self._message = message

    def __contains__(self, key):
        """
        @see MoinMoin.storage.external.Metadata.__contains__
        """
        raise self._exception(self._message)

    def __getitem__(self, key):
        """
        @see MoinMoin.storage.external.Metadata.__getitem__
        """
        raise self._exception(self._message)

    def __setitem__(self, key, value):
        """
        @see MoinMoin.storage.external.Metadata.__setitem__
        """
        self._metadata[key] = value

    def __delitem__(self, key):
        """
        @see MoinMoin.storage.external.Metadata.__delitem__
        """
        del self._metadata[key]

    def keys(self):
        """
        @see MoinMoin.storage.external.Metadata.keys
        """
        raise self._exception(self._message)

    def save(self):
        """
        @see MoinMoin.storage.external.Metadata.save
        """
        self._metadata.save()


class ReadonlyData(DataBackend):
    """
    This class implements read only access to the DataBackend.
    """

    def __init__(self, data_backend, exception, message):
        """
        Init stuff.
        """
        self._data_backend = data_backend
        self._exception = exception
        self._message = message

    def read(self, size=None):
        """
        @see MoinMoin.storage.interfaces.DataBackend.read
        """
        return self._data_backend.read(size)

    def seek(self, offset):
        """
        @see MoinMoin.storage.interfaces.DataBackend.seek
        """
        self._data_backend.seek(offset)

    def tell(self):
        """
        @see MoinMoin.storage.interfaces.DataBackend.tell
        """
        return self._data_backend.tell()

    def write(self, data):
        """
        @see MoinMoin.storage.interfaces.DataBackend.write
        """
        raise self._exception(self._message)

    def close(self):
        """
        @see MoinMoin.storage.interfaces.DataBackend.close
        """
        self._data_backend.close()


class WriteonlyData(DataBackend):
    """
    This class implements write only access to the DataBackend.
    """

    def __init__(self, data_backend, exception, message):
        """
        Init stuff.
        """
        self._data_backend = data_backend
        self._exception = exception
        self._message = message

    def read(self, size=None):
        """
        @see MoinMoin.storage.interfaces.DataBackend.read
        """
        raise self._exception(self._message)

    def seek(self, offset):
        """
        @see MoinMoin.storage.interfaces.DataBackend.seek
        """
        raise self._exception(self._message)

    def tell(self):
        """
        @see MoinMoin.storage.interfaces.DataBackend.tell
        """
        raise self._exception(self._message)

    def write(self, data):
        """
        @see MoinMoin.storage.interfaces.DataBackend.write
        """
        self._data_backend.write(data)

    def close(self):
        """
        @see MoinMoin.storage.interfaces.DataBackend.close
        """
        self._data_backend.close()


_ = lambda x: x
