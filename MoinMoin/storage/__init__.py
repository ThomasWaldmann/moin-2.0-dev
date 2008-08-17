# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Backends - Storage API Definition.

    The storage API consists of the classes defined in this module. That is:
    Backend, Item, Revision, NewRevision and StoredRevision.

    A concrete backend implements the abstract methods defined by the API,
    but also uses concrete methods that have already been defined in this
    module.
    A backend is a collection of items. (Examples for backends include SQL,
    mercurial or filesystem. All of those are means to store data.)

    Items are, well, the units you store within those backends, e.g. (in our
    context) pages or attachments. An item itself has revisions and metadata.
    For instance, you can use that to show a diff between two `versions` of a
    page, where the page "Foo" is represented by an item and the two versions
    are represented by two revisions on that item.

    Metadata is data that describes other data. An item has metadata. A single
    revision has metadata as well. E.g. "Which user created this revision?"
    would be something stored in the metadata of a revision, while "Who created
    this page in the first place?" would be answered by looking at the metadata
    of the first revision. Thus, an item basically is a collection of revisions
    which contain the content for the item. The last revision represents the most
    recent contents. A stored item can have metadata or revisions, or both.

    For normal operation, revision data and metadata is immutable as soon as the
    revision is committed to storage (by calling the commit() method on the item
    that holds the revision), thus making it a StoredRevision.
    Item metadata, on the other hand, as infrequently used as it may be, is mutable.
    Hence, it can only be modified under a read lock.

    ---

    @copyright: 2008 MoinMoin:ChristopherDenter,
                2008 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

from UserDict import DictMixin
from MoinMoin.storage.error import RevisionNumberMismatchError, AccessError, \
                                   NoSuchItemError


# TODO Move these constants to appropriate locations. They are not related to
# TODO storage on this layer whatsoever. E.g. user-storage doesn't use them at
# TODO all. Just keeping them here for convenience for now.
ACL = "acl"

# special meta-data whose presence indicates that the item is deleted
DELETED = "deleted"

SIZE = "size"

EDIT_LOG_ACTION = "edit_log_action"
EDIT_LOG_ADDR = "edit_log_addr"
EDIT_LOG_HOSTNAME = "edit_log_hostname"
EDIT_LOG_USERID = "edit_log_userid"
EDIT_LOG_EXTRA = "edit_log_extra"
EDIT_LOG_COMMENT = "edit_log_comment"

EDIT_LOG = [EDIT_LOG_ACTION, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME, EDIT_LOG_USERID, EDIT_LOG_EXTRA, EDIT_LOG_COMMENT]


class Backend(object):
    """
    This class abstracts access to backends. If you want to write a specific
    backend, say a mercurial backend, you have to implement the methods below.
    A backend knows of its items and can perform several item related operations
    such as search_item, get_item, create_item, etc.
    """
    #
    # If you need to write a backend it is sufficient
    # to implement the methods of this class. That
    # way you don't *have to* implement the other classes
    # like Item and Revision as well. Though, if you want
    # to, you can do it as well.
    # Assuming my_item is instanceof(Item), when you call
    # my_item.create_revision(42), internally the
    # _create_revision() method of the items backend is
    # invoked and the item passes itself as parameter.
    #
    def search_item(self, searchterm):
        """
        Takes a MoinMoin search term and returns an iterator (maybe empty) over
        matching item objects (NOT item names!).

        @type searchterm: MoinMoin search term
        @param searchterm: The term for which to search.
        @rtype: iterator of item objects
        """
        # Very simple implementation because we have no indexing
        # or anything like that. If you want to optimize this, override it.
        # Needs self.iteritems.
        for item in self.iteritems():
            searchterm.prepare()
            if searchterm.evaluate(item):
                yield item

    def get_item(self, itemname):
        """
        Returns item object or raises Exception if that item does not exist.

        @type itemname: unicode
        @param itemname: The name of the item we want to get.
        @rtype: item object
        @raise NoSuchItemError: No item with name 'itemname' is known to this backend.
        """
        raise NotImplementedError()

    def has_item(self, itemname):
        """
        This method is added for convenience. With it you don't need to try get_item
        and catch an exception that may be thrown if the item doesn't exist yet.

        @type itemname: unicode
        @param itemname: The name of the item of which we want to know whether it exists.
        @rtype: bool
        """
        # XXX Is there a more beautiful way to approach this?
        # XXX This is going to cause nasty lockups if get_item itself tries to use this method. URGH!
        # XXX Thus, you should aim to override this dummy behaviour!
        try:
            self.get_item(itemname)
            return True
        except NoSuchItemError:
            return False

    def create_item(self, itemname):
        """
        Creates an item with a given itemname. If that item already exists,
        raise an exception.

        @type itemname: unicode
        @param itemname: Name of the item we want to create.
        @rtype: item object
        @raise ItemAlreadyExistsError: The item you were trying to create already exists.
        """
        raise NotImplementedError()

    def iteritems(self):
        """
        Returns an iterator over all items available in this backend.
        (Like the dict method).

        @rtype: iterator of item objects
        """
        raise NotImplementedError()

    def history(self, reverse=True):
        """
        Returns an iterator over ALL revisions of ALL items stored in the
        backend.

        If reverse is True (default), give history in reverse revision
        timestamp order, otherwise in revision timestamp order.

        Note: some functionality (e.g. completely cloning one storage into
              another) requires that the iterator goes over really every
              revision we have).

        @type reverse: bool
        @param reverse: Indicate whether the iterator should go in reverse order.
        @rtype: iterator of revision objects
        """
        # generic and slow history implementation
        revs = []
        for item in self.iteritems():
            for revno in item.list_revisions():
                rev = item.get_revision(revno)
                revs.append((rev.timestamp, rev.revno, item.name, ))
        revs.sort() # from oldest to newest
        if reverse:
            revs.reverse()
        for ts, revno, name in revs:
            item = self.get_item(name)
            yield item.get_revision(revno)

    def _get_revision(self, item, revno):
        """
        For a given item and revision number, return the corresponding revision
        of that item.
        Note: If you pass -1 as revno, this shall return the latest revision of the item.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @type revno: int
        @param revno: Indicate which revision is wanted precisely. If revno is
        -1, return the most recent revision.
        @rtype: Object of class Revision
        @raise NoSuchRevisionError: No revision with that revno was found on item.
        """
        raise NotImplementedError()

    def _list_revisions(self, item):
        """
        For a given item, return a list containing all revision numbers (as ints)
        of the revisions the item has. The list must be ordered, starting with
        the first revision-number.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @return: list of ints (possibly empty)
        """
        raise NotImplementedError()

    def _create_revision(self, item, revno):
        """
        Takes an item object and creates a new revision. Note that you need to pass
        a revision number for concurrency-reasons. If this is the first revision
        you create on the item, the revno must be 0. The revnos then must be
        subsequent.
        The newly created revision-object is returned to the caller.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @type revno: int
        @param revno: Indicate which revision we want to create.
        @precondition: item.get_revision(-1).revno == revno - 1
        @return: Object of class Revision.
        @raise RevisionAlreadyExistsError: Raised if a revision with that number
        already exists on item.
        @raise RevisionNumberMismatchError: Raised if precondition is not
        fulfilled.
        """
        raise NotImplementedError()

    def _rename_item(self, item, newname):
        """
        Renames a given item. Raises Exception if the item you are trying to rename
        does not exist or if the newname is already chosen by another item.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @type newname: string
        @param newname: Name of item after this operation has succeeded.
        @precondition: self.has_item(newname) == False
        @postcondition: self.has_item(newname) == True
        @raises ItemAlreadyExistsError: Raised if an item with name 'newname'
        already exists.
        @raises AssertionError: Precondition not fulfilled. (Item not yet
        committed to storage)
        @return: None
        """
        raise NotImplementedError()

    def _commit_item(self, item):
        """
        Commits the changes that have been done to a given item. That is, after you
        created a revision on that item and filled it with data you still need to
        commit() it. You don't need to pass what revision you are committing because
        there is only one possible revision to be committed for your /instance/ of
        the item and thus the revision to be saved is memorized by the item.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @return: None
        """
        raise NotImplementedError()

    def _rollback_item(self, item):
        """
        This method is invoked when external events happen that cannot be handled in a
        sane way and thus the changes that have been made must be rolled back.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @return: None
        """
        raise NotImplementedError()

    def _change_item_metadata(self, item):
        """
        This method is used to acquire a lock on an item. This is necessary to prevent
        side-effects caused by concurrency.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @precondition: item not already locked
        @return: None
        """
        raise NotImplementedError()

    def _publish_item_metadata(self, item):
        """
        This method tries to release a lock on the given item and put the newly
        added Metadata of the item to storage.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @raise AssertionError: item was not locked
        @return: None
        """
        raise NotImplementedError()

    def _read_revision_data(self, revision, chunksize):
        """
        Called to read a given amount of bytes of a revisions data. By default, all
        data is read.

        @type revision: Object of class StoredRevision.
        @param revision: The revision on which we want to operate.
        @type chunksize: int
        @param chunksize: amount of bytes to be read at a time
        @return: string
        """
        raise NotImplementedError()

    def _write_revision_data(self, revision, data):
        """
        When this method is called, the passed data is written to the revisions data.

        @type revision: Object of class NewRevision.
        @param revision: The revision on which we want to operate.
        @type data: str
        @param data: The data to be written on the revision.
        @return: None
        """
        raise NotImplementedError()

    def _get_item_metadata(self, item):
        """
        Load metadata for a given item, return dict.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @return: dict of metadata key / value pairs.
        """
        raise NotImplementedError()

    def _get_revision_metadata(self, revision):
        """
        Load metadata for a given revision, returns dict.

        @type revision: Object of a subclass of Revision.
        @param revision: The revision on which we want to operate.
        @return: dict of metadata key / value pairs.
        """
        raise NotImplementedError()

    def _get_revision_timestamp(self, revision):
        """
        Lazily load the revision's timestamp. If accessing it
        is cheap, it can be given as a parameter to StoredRevision
        instantiation instead.
        Return the timestamp (a long).

        @type revision: Object of a subclass of Revision.
        @param revision: The revision on which we want to operate.
        @return: long
        """
        raise NotImplementedError()

    def _get_revision_size(self, revision):
        """
        Lazily access the revision's data size. This needs not be
        implemented if all StoredRevision objects are instantiated
        with the size= keyword parameter.

        @type revision: Object of a subclass of Revision.
        @param revision: The revision on which we want to operate.
        @return: int
        """
        raise NotImplementedError()

    def _seek_revision_data(self, revision, position, mode):
        """
        Set the revisions cursor on the revisions data.

        @type revision: Object of StoredRevision.
        @param revision: The revision on which we want to operate.
        @type position: int
        @param position: Indicates where to position the cursor
        @type mode: int
        @param mode: 0 for absolute positioning, 1 to seek relatively to the
        current position, 2 to seek relative to the files end.
        @return: None
        """
        raise NotImplementedError()


class Item(object, DictMixin):
    """
    An item object collects the information of an item (e.g. a page) that is
    stored in persistent storage. It has metadata and revisions.
    An item object is just a proxy to the information stored in the backend.
    It doesn't necessarily live very long.
    """
    def __init__(self, backend, itemname):
        """
        Initialize an item. Memorize the backend to which it belongs.
        """
        self._backend = backend
        self._name = itemname
        self._locked = False
        self._read_accessed = False
        self._metadata = None  # Will be loaded lazily upon first real access.
        self._uncommitted_revision = None

    def get_name(self):
        """
        name is a read-only property of this class.
        """
        return self._name

    name = property(get_name, doc="This is the name of this item. This attribute is read-only.")

    def __setitem__(self, key, value):
        """
        In order to acces the items metadata you can use the well-known dict-like
        semantics python-dictionaries offer. If you want to set a value,
        my_item["key"] = "value" will do the trick. Note that keys must be of the
        type string (or unicode).
        Values must be of the type str, unicode or tuple, in which case every element
        of the tuple must be a string, unicode or tuple object.
        You must wrap write-accesses to metadata in change_metadata/publish_metadata
        calls.
        Keys starting with two underscores are reserved and cannot be used.
        """
        if not self._locked:
            raise AttributeError("Cannot write to unlocked metadata")
        if not isinstance(key, (str, unicode)):
            raise TypeError("Key must be string type")
        if key.startswith('__'):
            raise TypeError("Key must not begin with two underscores")
        if not value_type_is_valid(value):
            raise TypeError("Value must be string, unicode, int, long, float, bool, complex or a nested tuple thereof.")
        if self._metadata is None:
            self._metadata = self._backend._get_item_metadata(self)
        self._metadata[key] = value

    def __delitem__(self, key):
        """
        Delete an item metadata key.
        """
        if not self._locked:
            raise AttributeError("Cannot write to unlocked metadata")
        if key.startswith('__'):
            raise KeyError(key)
        if self._metadata is None:
            self._metadata = self._backend._get_item_metadata(self)
        del self._metadata[key]

    def __getitem__(self, key):
        """
        See __setitem__.__doc__ -- You may use my_item["key"] to get the corresponding
        metadata-value. Note however, that the key you pass must be of type str or unicode.
        """
        self._read_accessed = True
        if not isinstance(key, (unicode, str)):
            raise TypeError("key must be string type")
        if key.startswith('__'):
            raise KeyError(key)
        if self._metadata is None:
            self._metadata = self._backend._get_item_metadata(self)

        return self._metadata[key]

    def keys(self):
        """
        This method returns a list of all metadata-keys of this item (i.e., a list of Strings.)
        That allows using pythons `for mdkey in itemobj: do_something`-syntax.
        """
        if self._metadata is None:
            self._metadata = self._backend._get_item_metadata(self)

        return filter(lambda x: not x.startswith('__'), self._metadata.keys())

    def change_metadata(self):
        """
        Acquire lock for the items metadata. The actual locking is, by default,
        implemented on the backend-level.
        """
        if self._uncommitted_revision is not None:
            raise RuntimeError("You tried to change the metadata of the item %r but there are uncommitted revisions on that item. Commit first." % (self.name))
        if self._read_accessed:
            raise AccessError("Cannot lock after reading metadata")

        self._backend._change_item_metadata(self)
        self._locked = True

    def publish_metadata(self):
        """
        Release lock on the item.
        """
        if not self._locked:
            raise AccessError("cannot publish without change_metadata")
        self._backend._publish_item_metadata(self)
        self._read_accessed = False
        self._locked = False

    def get_revision(self, revno):
        """
        Fetches a given revision and returns it to the caller.
        Note: If you pass -1 as revno, this shall return the latest revision of the item.
        """
        return self._backend._get_revision(self, revno)

    def list_revisions(self):
        """
        Returns a list of ints representing the revisions this item has.
        """
        return self._backend._list_revisions(self)

    def rename(self, newname):
        """
        Rename the item. By default this uses the rename method the backend
        specifies internally.
        """
        if not isinstance(newname, (str, unicode)):
            raise TypeError("Item names must have string type, not %s" % (type(newname)))

        self._backend._rename_item(self, newname)
        self._name = newname

    def commit(self):
        """
        Commit the item. By default this uses the commit method the backend
        specifies internally.
        """
        assert self._uncommitted_revision is not None
        self._backend._commit_item(self._uncommitted_revision)
        self._uncommitted_revision = None

    def rollback(self):
        """
        Invoke this method when external events happen that cannot be handled in a
        sane way and thus the changes that have been made must be rolled back.
        """
        self._backend._rollback_item(self._uncommitted_revision)
        self._uncommitted_revision = None

    def create_revision(self, revno):
        """
        Create a new revision on the item. By default this uses the
        create_revision method the backend specifies internally.
        """
        if self._locked:
            raise RuntimeError("You tried to create revision #%d on the item %r, but there is unpublished metadata on that item. Publish first." % (revno, self.name))

        if self._uncommitted_revision is not None:
            if self._uncommitted_revision.revno != revno:
                raise RevisionNumberMismatchError("There already is an uncommitted revision #%d on this item that doesn't match the revno %d you specified." % (self._uncommitted_revision.revno, revno))

            else:
                return self._uncommitted_revision

        else:
            self._uncommitted_revision = self._backend._create_revision(self, revno)
            return self._uncommitted_revision


class Revision(object, DictMixin):
    """
    An object of this class represents a revision of an item. An item can have
    several revisions at a time, one being the most recent revision.
    This is a principle that is similar to the concepts used in Version-Control-
    Systems.

    Each revision object has a creation timestamp in the 'timestamp' property
    that defaults to None for newly created revisions in which case it will be
    assigned at commit() time. It is writable for use by converter backends,
    care must be taken in that case to create monotonous timestamps!
    This timestamp is also retrieved via the backend's history() method.
    """

    def __init__(self, item, revno, timestamp):
        """
        Initialize the revision.
        """
        self._revno = revno

        self._item = item
        self._backend = item._backend
        self._metadata = None
        self._timestamp = timestamp

    def _get_item(self):
        return self._item

    item = property(_get_item)

    def get_revno(self):
        """
        Getter for the read-only revno-property.
        """
        return self._revno

    revno = property(get_revno, doc = "This property stores the revno of the revision-object. Only read-only access is allowed.")

    def _load_metadata(self):
        self._metadata = self._backend._get_revision_metadata(self)

    def __getitem__(self, key):
        """
        Get the corresponding value to the key from the metadata dict.
        """
        if not isinstance(key, (unicode, str)):
            raise TypeError("key must be string type")

        if key.startswith('__'):
            raise KeyError(key)

        if self._metadata is None:
            self._load_metadata()

        return self._metadata[key]

    def keys(self):
        """
        This method returns a list of all metadata-keys of this revision (i.e., a list of Strings.)
        That allows using pythons `for mdkey in revopbj: do_something`-syntax.
        """
        if self._metadata is None:
            self._load_metadata()

        return filter(lambda x: not x.startswith('__'), self._metadata.keys())

    def read_data(self, chunksize = -1):
        """
        Allows file-like read-operations. You can pass a chunksize and it will
        only read as many bytes at a time as you wish. The default, however, is
        to load the whole revision data into memory, which may not be what you
        want.
        """
        return self._backend._read_revision_data(self, chunksize)


class StoredRevision(Revision):
    """
    This is the brother of NewRevision. It allows reading data from a revision
    that has already been stored in persistant storage. It doesn't allow data-
    manipulation.
    """

    def __init__(self, item, revno, timestamp=None, size=None):
        """
        Initialize the NewRevision
        """
        Revision.__init__(self, item, revno, timestamp)
        self._size = size

    def _get_ts(self):
        if self._timestamp is None:
            self._timestamp = self._backend._get_revision_timestamp(self)
        return self._timestamp

    timestamp = property(_get_ts, doc="This property returns the creation timestamp of the revision")

    def _get_size(self):
        if self._size is None:
            self._size = self._backend._get_revision_size(self)
            assert self._size is not None

        return self._size

    size = property(_get_size, doc="Size of revision's data")

    def __setitem__(self):
        """
        revision metadata cannot be altered, thus, we raise an Exception.
        """
        raise AttributeError("Metadata of already existing revisions may not be altered.")

    def read(self, chunksize = -1):
        """
        Allows file-like read-operations. You can pass a chunksize and it will
        only read as many bytes at a time as you wish. The default, however, is
        to load the whole revision data into memory, which may not be what you
        want.
        """
        return self._backend._read_revision_data(self, chunksize)

    def seek(self, position, mode=0):
        """
        Set the current position for reading the revisions data.
        The mode argument is optional and defaults to 0 (absolute file
        positioning); other values are 1 (seek relative to the current
        position) and 2 (seek relative to the file's end).
        There is no return value.
        (docstring stolen from StringIO.StringIO().seek.__doc__)
        """
        self._backend._seek_revision_data(self, position, mode)


class NewRevision(Revision):
    """
    This is basically the same as revision but with mutable metadata and data properties.
    """
    def __init__(self, item, revno):
        """
        Initialize the NewRevision
        """
        Revision.__init__(self, item, revno, None)
        self._metadata = {}
        self._size = 0

    def _get_ts(self):
        return self._timestamp

    def _set_ts(self, ts):
        ts = long(ts)
        self._timestamp = ts

    timestamp = property(_get_ts, _set_ts, doc="This property accesses the creation timestamp of the revision")

    def _get_size(self):
        return self._size

    size = property(_get_size, doc="Size of data written so far")

    def __setitem__(self, key, value):
        """
        Internal method used for dict-like access to the NewRevisions metadata-dict.
        Keys starting with two underscores are reserved and cannot be used.
        """
        if not isinstance(key, (str, unicode)):
            raise TypeError("Key must be string type")

        if key.startswith('__'):
            raise TypeError("Key must not begin with two underscores")

        if not value_type_is_valid(value):
            raise TypeError("Value must be string, int, long, float, bool, complex or a nested tuple of the former")

        self._metadata[key] = value

    def __delitem__(self, key):
        if key.startswith('__'):
            raise KeyError(key)

        del self._metadata[key]

    def write(self, data):
        """
        Write `data` to the NewRevisions data attribute. This is the actual (binary)
        data, e.g. the binary representation of an image.
        """
        self._size += len(data)
        self._backend._write_revision_data(self, data)


# Little helper function:
def value_type_is_valid(value):
    """
    For metadata-values, we allow only immutable types, namely:
    str, unicode, bool, int, long, float, complex and tuple.
    Since tuples can contain other types, we need to check the
    types recursively.
    """
    if isinstance(value, (str, unicode, int, long, float, complex)):
        return True
    elif isinstance(value, tuple):
        for element in value:
            if not value_type_is_valid(element):
                return False
        else:
            return True


