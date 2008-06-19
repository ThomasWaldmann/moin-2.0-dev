"""
    MoinMoin - Backends

    This package contains code for the backends of the new storage layer.
    During GSoC 2007 Heinrich Wendel designed an API for the new storage layer.
    As of GSoC 2008, this will become an improved API for the storage layer.

    ---

    A Backend is a collection of Items.
    Examples for backends would be SQL-, Mercurial- or
    a Filesystem backend. All of those are means to
    store data. Items are, well, the units you store
    within those Backends, e.g. (in our context), Pages.
    An Item itself has Revisions and Metadata.
    For instance, you can use that to show a diff between
    two `versions` of a page. Metadata is data that describes
    other data. An Item has Metadata. A single Revision
    has Metadata as well. E.g. "Which user created this Revision?"
    would be something stored in the Metadata of a Revision,
    while "Who created this page in the first place?" would
    be answered by looking at the metadata of the first revision.
    Thus, an Item basically is a collection of Revisions which
    contain the content for the Item. The last Revision represents
    the most recent contents. An Item can have Metadata as well
    as Revisions.

    For normal operation, Revision data and metadata is immutable as
    soon as the revision is committed to the storage. Item metadata,
    on the other hand, as infrequently used as it may be, is mutable.
    Hence, it can only be modified under a read lock.

    ---

    @copyright: 2008 MoinMoin:ChristopherDenter,
                2008 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

from UserDict import DictMixin

class Backend(object):
    """
    This class defines the new storage API for moinmoin.
    It abstracts access to backends. If you want to write
    a specific backend, say a mercurial backend, you have
    to implement the methods below.
    """

    def search_item(self, searchterm):
        """
        Takes a searchterm and returns an iterator (maybe empty) over matching
        objects.
        """
        raise NotImplementedError

    def get_item(self, itemname):
        """
        Returns Item object or raises Exception if that Item does not exist.
        """
        raise NotImplementedError

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

        except KeyError:
            return False

    def create_item(self, itemname):
        """
        Creates an item with a given itemname. If that Item already exists,
        raise an Exception.
        """
        raise NotImplementedError

    def iteritems(self):
        """
        Returns an iterator over all items available in this backend.
        (Like the dict method).
        """
        raise NotImplementedError

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
        """
        raise NotImplementedError

    def _list_revisions(self, item):
        """
        For a given Item, list all Revisions. Returns a list of ints representing
        the Revision numbers.
        """
        raise NotImplementedError

    def _create_revision(self, item, revno):
        """
        Takes an Item object and creates a new Revision. Note that you need to pass
        a revision number for concurrency-reasons.
        """
        raise NotImplementedError

    def _rename_item(self, item, newname):
        """
        Renames a given item. Raises Exception of the Item you are trying to rename
        does not exist or if the newname is already chosen by another Item.
        """
        raise NotImplementedError

    def _commit_item(self, item):
        """
        Commits the changes that have been done to a given Item. That is, after you
        created a Revision on that Item and filled it with data you still need to
        commit() it. You don't need to pass what Revision you are committing because
        there is only one possible Revision to be committed for your /instance/ of 
        the item and thus the Revision to be saved is memorized.
        """
        raise NotImplementedError

    def _rollback_item(self, item):
        """
        This method is invoked when external events happen that cannot be handled in a
        sane way and thus the changes that have been made must be rolled back.
        """
        raise NotImplementedError

    def _lock_item_metadata(self, item):
        """
        This method is used to acquire a lock on an Item. This is necessary to prevent
        side-effects caused by concurrency.
        """
        raise NotImplementedError

    def _unlock_item_metadata(self, item):
        """
        This method tries to release a lock on the given Item.
        """
        raise NotImplementedError

    def _read_revision_data(self, revision, chunksize):
        """
        Called to read a given amount of bytes of a revisions data. By default, all
        data is read.
        """
        raise NotImplementedError

    def _get_item_metadata(self, item):
        """
        Load metadata for a given item, return dict.
        """
        raise NotImplementedError


    # XXX Further internals of this class may follow


class Item(object, DictMixin):                      # TODO Improve docstring
    """
    An Item object collects the information of an item (e.g. a page) that is
    stored in persistent storage. It has metadata and Revisions.
    """
    def __init__(self, backend, itemname):
        """
        Initialize an Item. Memorize the backend to which it belongs.
        """
        self._backend = backend
        self._name = itemname

        self._locked = False
        self._read_accessed = False
        self._metadata = None          # Will be loaded lazily upon first real access.


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
        of the tuple must be a string (or unicode) object.
        You must acquire a lock before writing to the Items metadata in order to
        prevent side-effects.
        """
        if not self._locked:
            raise AttributeError, "Cannot write to unlocked metadata"

        if not isinstance(key, (str, unicode)):
            raise TypeError, "Key must be string type"

        if not value_type_is_valid(value):
            raise TypeError, "Value must be string, int, long, float, bool, complex or a nested tuple of the former"

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
            raise TypeError, "key must be string type"

        if self._metadata is None:
            self._metadata = self._backend._get_item_metadata(self)

        return self._metadata[key]

    def _lock(self):
        """
        Acquire lock for the Items metadata. The actual locking is, by default,
        implemented on the backend-level.
        """
        if self._read_accessed:
            raise Exception, "Cannot lock after reading metadata"

        self._backend._lock_item_metadata()
        self._locked = True

    def _unlock(self):
        """
        Release lock on the Item.
        """
        self._backend._unlock_item_metadata()
        self._locked = False

    def get_revision(self, revno):
        """
        Fetches a given revision and returns it to the caller.
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
        self._backend._commit_item(self)

    def create_revision(self, revno):
        """
        Create a new revision on the Item. By default this uses the
        create_revision method the backend specifies internally.
        """
        return self._backend._create_revision(self, revno)


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
        self.revno = revno

        self._item = item
        self._backend = item._backend
        self._data = None
        self._metadata = {}                             # TODO We will load it lazily

    def __setitem__(self):
        """
        Revision metadata cannot be altered, thus, we raise an Exception.
        """
        raise AttributeError, "Metadata of already existing Revisions may not be altered."

    def __getitem__(self, key):
        """
        Get the corresponding value to the key from the metadata dict.
        """
        if not isinstance(key, (unicode, str)):
            raise TypeError, "key must be string type"

        return self._metadata[key]

    def read_data(self, chunksize = -1):
        """
        Allows file-like read-operations. You can pass a chunksize and it will
        only read as many bytes at a time as you wish. The default, however, is
        to load the whole Revision data into memory, which may not be what you
        want.
        """
        return self._backend._read_revision_data(self, chunksize)


class NewRevision(Revision):
    """
    This is basically the same as Revision but with mutable metadata and data properties.
    """
    def __init__(self, item, revno):
        """
        Initialize the NewRevision
        """
        Revision.__init__(self, item, revno)

    def __setitem__(self, key, value):
        """
        Internal method used for dict-like access to the NewRevisions metadata-dict.
        """
        if not isinstance(key, (str, unicode)):
            raise TypeError, "Key must be string type"

        if not value_type_is_valid(value):
            raise TypeError, "Value must be string, int, long, float, bool, complex or a nested tuple of the former"

        self._metadata[key] = value

    def __getitem__(self, key):
        """
        Get the value to a given key from the NewRevisions metadata-dict.
        """
        if not isinstance(key, (unicode, str)):
            raise TypeError, "key must be string type"

        return self._metadata[key]

    def write_data(self, data):
        """
        Write `data` to the NewRevisions data attribute. This is the actual (binary)
        data, e.g. the binary representation of an image.
        """
        pass            # TODO: How do we best implement this?



# Little helper function:
def value_type_is_valid(value):
    """
    For metadata-values, we allow only immutable types, namely:
    str, unicode, bool, int, long, float, complex and tuple.
    Since tuples can contain other types, we need to check the
    types recursively.
    """
    if isinstance(value, (str, int, long, float, complex)):
        return True

    elif isinstance(value, tuple):
        for element in tuple:
            if not value_type_is_valid(element):
                return False

        else:
            return True


