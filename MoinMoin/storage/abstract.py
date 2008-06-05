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

    def create_item(self, itemname):
        """
        Creates an item with a given itemname. If that Item already exists,
        raise an Exception.
        """
        return Item(self, itemname)

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
        self._backend       = backend
        self._name          = itemname
        self._locked        = False
        self._read_accessed = False
        self._metadata      = None          # XXX Will be loaded lazily upon first real access.

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

        if not isinstance(value, (str, tuple, unicode)):
            raise TypeError, "Value must be string or tuple of strings"

        if isinstance(value, tuple):
            for v in value:
                if not isinstance(value, (str, unicode)):
                    raise TypeError, "Value must be string or tuple of strings"

        self._metadata[key] = value

    def __getitem__(self, key):
        """
        See __setitem__.__doc__ -- You may use my_item["key"] to get the corresponding
        metadata-value. Note however, that the key you pass must be of type str or unicode.
        """
        self._read_accessed = True

        if not isinstance(key, (unicode, str)):
            raise TypeError, "key must be string type"

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
        Rename the item. By default this uses the commit method the backend
        specifies internally.
        """
        self._backend._commit_item(self)

    def create_revision(self, revno):
        """
        Create a new revision on the Item. By default this uses the
        create_revision method the backend specifies internally.
        """
        return self._backend._create_revision(self, revno)

