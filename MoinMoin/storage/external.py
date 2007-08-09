"""
    MoinMoin external interfaces

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.

    TODO: acl checking
"""

import UserDict
import time

from MoinMoin import wikiutil
from MoinMoin.storage.backends.common import get_bool
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, BackendError, LockingError
from MoinMoin.storage.interfaces import DataBackend, MetadataBackend
from MoinMoin.support.python_compatibility import partial


ACL = "acl"

DELETED = "deleted"

SIZE = "size"

EDIT_LOCK_TIMESTAMP = "edit_lock_timestamp"
EDIT_LOCK_ADDR = "edit_lock_addr"
EDIT_LOCK_HOSTNAME = "edit_lock_hostname"
EDIT_LOCK_USERID = "edit_lock_userid"

EDIT_LOCK = [EDIT_LOCK_TIMESTAMP, EDIT_LOCK_ADDR, EDIT_LOCK_HOSTNAME, EDIT_LOCK_USERID]

EDIT_LOG_MTIME = "edit_log_mtime"
EDIT_LOG_ACTION = "edit_log_action"
EDIT_LOG_ADDR = "edit_log_addr"
EDIT_LOG_HOSTNAME = "edit_log_hostname"
EDIT_LOG_USERID = "edit_log_userid"
EDIT_LOG_EXTRA = "edit_log_extra"
EDIT_LOG_COMMENT = "edit_log_comment"

EDIT_LOG = [EDIT_LOG_MTIME, EDIT_LOG_ACTION, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME, EDIT_LOG_USERID, EDIT_LOG_EXTRA, EDIT_LOG_COMMENT]

READONLY_METADATA = [SIZE] + EDIT_LOCK + EDIT_LOG


class ItemCollection(UserDict.DictMixin, object):
    """
    The ItemCollection class realizes the access to the stored Items via the
    correct backend and maybe caching.
    """

    log_pos = None
    _item_cache = {}

    def __init__(self, backend, request=None):
        """
        Initializes the proper StorageBackend.
        """
        self._backend = backend
        self._request = request

        self._items = None
        self.timestamp = time.time()

    def __contains__(self, name):
        """
        Checks if an Item exists.
        """
        return self._backend.has_item(name)

    def __getitem__(self, name):
        """
        Loads an Item.
        """
        self.refresh()
        try:
            return self._item_cache[name]
        except KeyError:
            backend = self._backend.has_item(name)
            if backend:
                self._item_cache[name] = Item(name, backend, self._request)
                return self._item_cache[name]
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
            raise BackendError(_("Copy failed because name and newname are the same."))

        if not newname:
            raise BackendError(_("You cannot copy to an empty item name."))

        if newname in self.items:
            raise BackendError(_("Copy failed because an item with name %r already exists.") % newname)

        olditem = self[name]

        newitem = self.new_item(newname)
        newitem.lock = True

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

    def refresh(self):
        """
        Refresh item cache.
        """
        timestamp = time.time()
        news = self._backend.news(self.timestamp)
        for item in news:
            try:
                del self._item_cache[item[2]]
            except KeyError:
                pass
        self.timestamp = timestamp


class Item(UserDict.DictMixin, object):
    """
    The Item class represents a StorageItem. This Item has a name and revisions.
    An Item can be anything MoinMoin must save, e.g. Pages, Attachements or
    Users. A list of revision numbers is only loaded on access. Via Item[0]
    you can access the last revision. The specified Revision is only loaded on
    access as well. On every access the ACLs will be checked.
    """

    def __init__(self, name, backend, request):
        """
        Initializes the Item with the required parameters.
        """
        self.name = name

        self._backend = backend
        self._request = request

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
            self._acl = AccessControlList(self._backend._other._cfg, self[0].acl)
        return self._acl

    acl = property(get_acl)

    def get_edit_lock(self):
        """
        Get the lock property.
        It is a tuple containing the timestamp of the lock and the user.
        """
        if self._edit_lock is None:
            for key in EDIT_LOCK:
                if not key in self.metadata:
                    self._edit_lock = False, 0.0, "", "", ""
                    break
            else:
                self._edit_lock = (True, float(self.metadata[EDIT_LOCK_TIMESTAMP]), self.metadata[EDIT_LOCK_ADDR], self.metadata[EDIT_LOCK_HOSTNAME], self.metadata[EDIT_LOCK_USERID])
        return self._edit_lock

    def set_edit_lock(self, edit_lock):
        """
        Set the lock property to True or False.
        """
        self.lock = True
        if edit_lock:
            timestamp = time.time()
            addr = self._request.remote_addr
            hostname = wikiutil.get_hostname(self._request, addr)
            userid = self._request.user.valid and self._request.user.id or ''

            self.metadata[EDIT_LOCK_TIMESTAMP] = str(timestamp)
            self.metadata[EDIT_LOCK_ADDR] = addr
            self.metadata[EDIT_LOCK_HOSTNAME] = hostname
            self.metadata[EDIT_LOCK_USERID] = userid
        else:
            del self.metadata[EDIT_LOCK_TIMESTAMP]
            del self.metadata[EDIT_LOCK_ADDR]
            del self.metadata[EDIT_LOCK_HOSTNAME]
            del self.metadata[EDIT_LOCK_USERID]
        self.metadata.save()
        self.lock = False
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
        return get_bool(self.metadata.get(DELETED, False))

    def set_deleted(self, value):
        """
        Deleted Property.
        """
        if not value in [True, False]:
            raise ValueError(_("Invalid value for deleted, must be a boolean, is %r.") % value)
        self.metadata[DELETED] = str(value)

    deleted = property(get_deleted, set_deleted)

    def get_size(self):
        """
        Size Property.
        """
        size = long(self.metadata.get(SIZE, 0L))
        if not size:
            size = len(self.data.read())
            self.data.close()
        return size

    size = property(get_size)

    def __getattr__(self, name):
        """
        Get edit lock values.
        """
        if name in ('action', 'addr', 'hostname', 'userid', 'extra', 'comment'):
            return self.metadata.get("edit_log_" + name, "")
        elif name == 'mtime':
            return float(self.metadata.get("edit_log_" + name, 0.0))
        raise AttributeError(_("Revision class has no attribute %r.") % name)

    def save(self, action="SAVE", extra="", comment=""):
        """
        Saves the revision and sets new edit-log values.
        """
        # set edit-log
        if self._data is not None:
            timestamp = time.time()
            # TODO: just a hack, make this better
            if hasattr(self.item._request, "uid_override"):
                addr = ""
                hostname = self.item._request.uid_override
                userid = ""
                delattr(self.item._request, "uid_override")
            else:
                addr = self.item._request.remote_addr
                hostname = wikiutil.get_hostname(self.item._request, addr)
                userid = self.item._request.user.valid and self.item._request.user.id or ''
            self.metadata[EDIT_LOG_MTIME] = str(timestamp)
            self.metadata[EDIT_LOG_ACTION] = action
            self.metadata[EDIT_LOG_ADDR] = addr
            self.metadata[EDIT_LOG_HOSTNAME] = hostname
            self.metadata[EDIT_LOG_USERID] = userid
            self.metadata[EDIT_LOG_EXTRA] = extra
            self.metadata[EDIT_LOG_COMMENT] = wikiutil.clean_input(comment)
            self.data.close()
        if self._metadata is not None:
            self.metadata.save()


def _decorate(instance, obj, exception, message, forbid, forward):
    """
    Decorates a class with forwards or exceptions.
    """

    def _raise_exception(exception, message, *args, **kwargs):
        """
        Raise the exception.
        """
        raise exception(message)

    for method in forbid:
        setattr(instance, method, partial(_raise_exception, exception, message))
    for method in forward:
        setattr(instance, method, getattr(obj, method))


class ReadonlyMetadata(UserDict.DictMixin):
    """
    Readonly Metadata implementation.
    """

    __implements__ = MetadataBackend

    forbid = ['__setitem__', '__delitem__', 'save']
    forward = ['__getitem__', '__contains__', 'keys']

    def __init__(self, obj, exception, message):
        _decorate(self, obj, exception, message, self.forbid, self.forward)


class WriteonlyMetadata(UserDict.DictMixin):
    """
    Writeonly Metadata implementation.
    """

    __implements__ = MetadataBackend

    forbid = ['__getitem__', '__contains__', 'keys']
    forward = ['__setitem__', '__delitem__', 'save']

    def __init__(self, obj, exception, message):
        _decorate(self, obj, exception, message, self.forbid, self.forward)


class ReadonlyData(object):
    """
    This class implements read only access to the DataBackend.
    """

    __implements__ = DataBackend

    forbid = ['write']
    forward = ['read', 'seek', 'tell', 'close']

    def __init__(self, obj, exception, message):
        _decorate(self, obj, exception, message, self.forbid, self.forward)


class WriteonlyData(object):
    """
    This class implements write only access to the DataBackend.
    """

    __implements__ = DataBackend

    forbid = ['read', 'seek', 'tell', 'close']
    forward = ['write']

    def __init__(self, obj, exception, message):
        _decorate(self, obj, exception, message, self.forbid, self.forward)


_ = lambda x: x
