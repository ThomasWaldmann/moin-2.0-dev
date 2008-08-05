"""
    MoinMoin - Backends - Storage API Definition.

    During GSoC 2007 Heinrich Wendel designed an API for the storage layer.
    As of GSoC 2008, this API is greatly improved, changed and integrated
    into the MoinMoin system.

    ---

    The storage API consists of the classes defined in this module. That is:
    Backend-, Item-, Revision-, NewRevision- and StoredRevision-classes.

    A concrete backend implements the abstract methods defined by the API,
    but also uses concrete methods that have already been defined in this module

    A Backend is a collection of Items. (Examples for backends would be SQL-,
    Mercurial- or a Filesystem backend. All of those are means to store data.)

    Items are, well, the units you store within those Backends, e.g. (in our
    context), Pages. An Item itself has Revisions and Metadata. For instance,
    you can use that to show a diff between two `versions` of a page.

    Metadata is data that describes other data. An Item has Metadata. A single
    Revision has Metadata as well. E.g. "Which user created this Revision?"
    would be something stored in the Metadata of a Revision, while "Who created
    this page in the first place?" would be answered by looking at the metadata
    of the first revision. Thus, an Item basically is a collection of Revisions
    which contain the content for the Item. The last Revision represents the most
    recent contents. An Item can have Metadata as well as Revisions.

    For normal operation, Revision data and metadata is immutable as soon as the
    revision is committed to the storage. Item metadata, on the other hand, as
    infrequently used as it may be, is mutable. Hence, it can only be modified
    under a read lock.

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

EDIT_LOG_MTIME = "edit_log_mtime"
EDIT_LOG_ACTION = "edit_log_action"
EDIT_LOG_ADDR = "edit_log_addr"
EDIT_LOG_HOSTNAME = "edit_log_hostname"
EDIT_LOG_USERID = "edit_log_userid"
EDIT_LOG_EXTRA = "edit_log_extra"
EDIT_LOG_COMMENT = "edit_log_comment"

EDIT_LOG = [EDIT_LOG_MTIME, EDIT_LOG_ACTION, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME, EDIT_LOG_USERID, EDIT_LOG_EXTRA, EDIT_LOG_COMMENT]


class Backend(object):
    """
    This class defines the storage API for moinmoin.
    It abstracts access to backends. If you want to write
    a specific backend, say a mercurial backend, you have
    to implement the methods below.
    """

    def search_item(self, searchterm):
        """
        Takes a searchterm and returns an iterator (maybe empty) over matching
        objects.
        """
        raise NotImplementedError()

    def get_item(self, itemname):
        """
        Returns Item object or raises Exception if that Item does not exist.
        """
        raise NotImplementedError()

    def has_item(self, itemname):
        """
        This method is added for convenience. With it you don't need to try get_item
        and catch an exception that may be thrown if the item doesn't exist yet.
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
        Creates an item with a given itemname. If that Item already exists,
        raise an Exception.
        """
        raise NotImplementedError()

    def iteritems(self):
        """
        Returns an iterator over all items available in this backend.
        (Like the dict method).
        """
        raise NotImplementedError()

    #
    # The below methods are defined for convenience.
    # If you need to write a backend it is sufficient
    # to implement the methods of this class. That
    # way you don't *have to* implement the other classes
    # like Item and Revision as well. Though, if you want
    # to do that you can do it as well.
    # Assuming my_item is instanceof(Item), when you call
    # my_item.create_revision(42), internally the
    # _create_revision() method of the items Backend is
    # invoked and the item passes itself as paramter.
    #

    def _get_revision(self, item, revno):
        """
        For a given Item and Revision number, return the corresponding Revision
        of that Item.
        Note: If you pass -1 as revno, this shall return the latest Revision of the Item.
        """
        raise NotImplementedError()

    def _list_revisions(self, item):
        """
        For a given Item, list all Revisions. Returns a list of ints representing
        the Revision numbers.
        """
        raise NotImplementedError()

    def _create_revision(self, item, revno):
        """
        Takes an Item object and creates a new Revision. Note that you need to pass
        a revision number for concurrency-reasons.
        """
        raise NotImplementedError()

    def _rename_item(self, item, newname):
        """
        Renames a given item. Raises Exception of the Item you are trying to rename
        does not exist or if the newname is already chosen by another Item.
        """
        raise NotImplementedError()

    def _commit_item(self, item):
        """
        Commits the changes that have been done to a given Item. That is, after you
        created a Revision on that Item and filled it with data you still need to
        commit() it. You don't need to pass what Revision you are committing because
        there is only one possible Revision to be committed for your /instance/ of
        the item and thus the Revision to be saved is memorized.
        """
        raise NotImplementedError()

    def _rollback_item(self, item):
        """
        This method is invoked when external events happen that cannot be handled in a
        sane way and thus the changes that have been made must be rolled back.
        """
        raise NotImplementedError()

    def _change_item_metadata(self, item):
        """
        This method is used to acquire a lock on an Item. This is necessary to prevent
        side-effects caused by concurrency.
        """
        raise NotImplementedError()

    def _publish_item_metadata(self, item):
        """
        This method tries to release a lock on the given Item.
        """
        raise NotImplementedError()

    def _read_revision_data(self, revision, chunksize):
        """
        Called to read a given amount of bytes of a revisions data. By default, all
        data is read.
        """
        raise NotImplementedError()

    def _write_revision_data(self, revision, data):
        """
        Called to read a given amount of bytes of a revisions data. By default, all
        data is read.
        """
        raise NotImplementedError()

    def _get_item_metadata(self, item):
        """
        Load metadata for a given item, return dict.
        """
        raise NotImplementedError()

    def _get_revision_metadata(self, revision):
        """
        Load metadata for a given Revision, returns dict.
        """
        raise NotImplementedError()

    def _seek_revision_data(self, revision, position, mode):
        """
        Set the revisions cursor on the revisions data.
        """
        raise NotImplementedError()


    # XXX Further internals of this class may follow


class Item(object, DictMixin):  # TODO Improve docstring
    """
    An Item object collects the information of an item (e.g. a page) that is
    stored in persistent storage. It has metadata and Revisions.
    An Item object is just a proxy to the information stored in the backend.
    It doesn't necessarily live very long.
    """
    def __init__(self, backend, itemname):
        """
        Initialize an Item. Memorize the backend to which it belongs.
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
        This, we need to define this method.
        """
        return self._name

    name = property(get_name, doc="This is the name of this Item. This attribute is read-only.")

    def __setitem__(self, key, value):
        """
        In order to acces the Items metadata you can use the well-known dict-like
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
        This method returns a list of all metadata-keys of this Item (i.e., a list of Strings.)
        That allows using pythons `for mdkey in itemobj: do_something`-syntax.
        """
        if self._metadata is None:
            self._metadata = self._backend._get_item_metadata(self)

        return filter(lambda x: not x.startswith('__'), self._metadata.keys())

    def change_metadata(self):
        """
        Acquire lock for the Items metadata. The actual locking is, by default,
        implemented on the backend-level.
        """
        if self._uncommitted_revision is not None:
            raise RuntimeError("You tried to change the metadata of the item %r but there are uncommitted Revisions on that Item. Commit first." % (self.name))

        if self._read_accessed:
            raise AccessError("Cannot lock after reading metadata")

        self._backend._change_item_metadata(self)
        self._locked = True

    def publish_metadata(self):
        """
        Release lock on the Item.
        """
        self._backend._publish_item_metadata(self)
        self._locked = False

    def get_revision(self, revno):
        """
        Fetches a given revision and returns it to the caller.
        Note: If you pass -1 as revno, this shall return the latest Revision of the Item.
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
        self._backend._rename_item(self, newname)

    def commit(self):
        """
        Commit the item. By default this uses the commit method the backend
        specifies internally.
        """
        assert self._uncommitted_revision is not None

        self._backend._commit_item(self)

    def rollback(self):
        """
        Invoke this method when external events happen that cannot be handled in a
        sane way and thus the changes that have been made must be rolled back.
        """
        self._backend._rollback_item(self)

    def create_revision(self, revno):
        """
        Create a new revision on the Item. By default this uses the
        create_revision method the backend specifies internally.
        """
        if self._locked:
            raise RuntimeError("You tried to create revision #%d on the item %r, but there is unpublished metadata on that Item. Publish first." % (revno, self.name))


        if self._uncommitted_revision is not None:
            if self._uncommitted_revision.revno != revno:
                raise RevisionNumberMismatchError("There already is an uncommitted Revision #%d on this Item that doesn't match the revno %d you specified." % (self._uncommitted_revision.revno, revno))

            else:
                return self._uncommitted_revision

        else:
            self._uncommitted_revision = self._backend._create_revision(self, revno)
            return self._uncommitted_revision


# the classes here are still not finished but will be (and polished) while the memorybackend and the tests
# are created


class Revision(object, DictMixin):
    """
    An object of this class represents a Revision of an Item. An Item can have
    several Revisions at a time, one being the most recent Revision.
    This is a principle that is similar to the concepts used in Version-Control-
    Systems.
    """

    def __init__(self, item, revno):
        """
        Initialize the Revision.
        """
        self._revno = revno

        self._item = item
        self._backend = item._backend
        self._metadata = None

    def get_revno(self):
        """
        Getter for the read-only revno-property.
        """
        return self._revno

    revno = property(get_revno, doc = "This property stores the revno of the Revision-object. Only read-only access is allowed.")

    def __getitem__(self, key):
        """
        Get the corresponding value to the key from the metadata dict.
        """
        if not isinstance(key, (unicode, str)):
            raise TypeError("key must be string type")

        if key.startswith('__'):
            raise KeyError(key)

        if self._metadata is None:
            self._metadata = self._backend._get_revision_metadata(self)

        return self._metadata[key]

    def keys(self):
        """
        This method returns a list of all metadata-keys of this Revision (i.e., a list of Strings.)
        That allows using pythons `for mdkey in revopbj: do_something`-syntax.
        """
        if self._metadata is None:
            self._metadata = self._backend._get_revision_metadata(self)

        return filter(lambda x: not x.startswith('__'), self._metadata.keys())

    def read_data(self, chunksize = -1):
        """
        Allows file-like read-operations. You can pass a chunksize and it will
        only read as many bytes at a time as you wish. The default, however, is
        to load the whole Revision data into memory, which may not be what you
        want.
        """
        return self._backend._read_revision_data(self, chunksize)

class StoredRevision(Revision):
    """
    This is the brother of NewRevision. It allows reading data from a Revision
    that has already been stored in persistant storage. It doesn't allow data-
    manipulation.
    """

    def __init__(self, item, revno):
        """
        Initialize the NewRevision
        """
        Revision.__init__(self, item, revno)

    def __setitem__(self):
        """
        Revision metadata cannot be altered, thus, we raise an Exception.
        """
        raise AttributeError("Metadata of already existing Revisions may not be altered.")

    def read(self, chunksize = -1):
        """
        Allows file-like read-operations. You can pass a chunksize and it will
        only read as many bytes at a time as you wish. The default, however, is
        to load the whole Revision data into memory, which may not be what you
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
    This is basically the same as Revision but with mutable metadata and data properties.
    """
    def __init__(self, item, revno):
        """
        Initialize the NewRevision
        """
        Revision.__init__(self, item, revno)
        self._metadata = {}

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

    def write(self, data):
        """
        Write `data` to the NewRevisions data attribute. This is the actual (binary)
        data, e.g. the binary representation of an image.
        """
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


