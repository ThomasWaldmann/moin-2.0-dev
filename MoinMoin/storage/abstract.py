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
    has Metadata as well. E.g. "Which user altered this Page?"
    would be something stored in the Metadata of a Revision,
    while "Who created this page in the first place?" would
    be something stored in the Metadata of the first Revision.
    Thus, an Item basically is a collection of Revisions which
    contain the content for the Item. The last Revision represents
    the most recent contents. An Item can have Metadata as well 
    as Revisions.

    ---

    @copyright: 2008 MoinMoin:ChristopherDenter,
                2008 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

class Backend(object):
    """
    This class defines the new storage API for moinmoin.
    It abstracts access to backends. If you want to write
    a specific backend, say a mercurial backend, you have
    to implement the methods below.
    """

    def search_item(self, searchterm):
        """
        Takes a searchterm and returns an iterator
        (maybe empty) over matching objects.
        """
        raise NotImplementedError

    def get_item(self, itemname):
        """
        Returns Item object or raises Exception
        if that Item does not exist.
        """
        raise NotImplementedError

    def create_item(self, itemname):
        """
        Creates an item with a given itemname.
        If that Item already exists, raise an
        Exception.
        """
        raise NotImplementedError

    def iteritems(self):
        """
        Returns an iterator over all items
        available in this backend. (Like the dict method).
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
        For a given Item and Revision number,
        return the corresponding Revision of
        that Item.
        """
        raise NotImplementedError

    def _list_revisions(self, item):
        """
        For a given Item, list all Revisions.
        Returns a list of ints representing
        the Revision numbers.
        """
        raise NotImplementedError

    def _create_revision(self, item, revno):
        """
        Takes an Item object and creates a new
        Revision. Note that you need to pass
        a revision number for concurrency-reasons.
        """
        raise NotImplementedError

    def _rename_item(self, item, newname):
        """
        Renames a given item.
        Raises Exception of the Item
        you are trying to rename does not
        exist or if the newname is already
        chosen by another Item.
        """
        raise NotImplementedError

    def _commit_item(self, item):
        """
        Commits the changes that have been
        done to a given Item. That is,
        after you created a Revision on
        that Item and filled it with data
        you still need to commit() it.
        You don't need to pass what Revision
        you are committing because there is only
        one possible Revision to be committed
        for your /instance/ of the item and
        thus the Revision to be saved is memorized.
        """
        raise NotImplementedError

    def _rollback_item(self, item):
        """
        This method is invoked when external
        events happen that cannot be handled in a
        sane way and thus the changes that have
        been made must be rolled back.
        """
        raise NotImplementedError


    # XXX Further internals of this class may follow

