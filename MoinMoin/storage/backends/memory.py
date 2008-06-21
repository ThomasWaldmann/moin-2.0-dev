"""
    MoinMoin - MemoryBackend

    This represents a simple Backend that stores all data in memory.
    This is mainly done for testing and documentation / demonstration purposes.
    Thus, this backend IS NOT designed for concurrent use.

    DO NOT (even for the smallest glimpse of a second) consider to use this backend
    for any production site that needs persistant storage.
    (Assuming you got no infinite stream of power-supply.)

    ---

    @copyright: 2008 MoinMoin:ChristopherDenter,
                2008 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.

"""

from MoinMoin.storage import Backend, Item, Revision, NewRevision
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, \
                                   ItemAlreadyExistsError, \
                                   RevisionAlreadyExistsError, RevisionNumberMismatchError

import StringIO


class MemoryBackend(Backend):
    """
    Implementation of the MemoryBackend. All data is kept in attributes of this
    class. As soon as the MemoryBackend-object goes out of scope, your data is LOST.
    """
    def __init__(self):
        """
        Initialize this Backend.
        """
        self._last_itemid = 0

        self._itemmap = {}                  # {itemname : itemid}   // names may change...
        self._item_metadata = {}            # {id : {metadata}}
        self._item_revisions = {}           # {id : {revision_id : (revision_data, {revision_metadata})}} 

    def search_item(self, searchterm):
        """
        Takes a searchterm and returns an iterator (maybe empty) over matching
        objects.
        """
        # This is a very very very stupid search algorithm
        # FIXME 19:14 < johill> dennda: you misunderstood what a search term is meant to be
        #       19:14 < johill> dennda: look at MoinMoin/search/term.py (but feel free to put low on your todo list right now)
        matches = []

        for itemname in self._itemmap:
            if searchterm.lower() in itemname.lower():
                matches.append(itemname)

        return iter(matches)

    def get_item(self, itemname):
        """
        Returns Item object or raises Exception if that Item does not exist.
        """
        if not self.has_item(itemname):
            raise NoSuchItemError, "No such item, %r" % (itemname)

        item = Item(self, itemname)
        item._item_id = self._itemmap[itemname]

        return item

    def has_item(self, itemname):
        """
        Overriding the default has_item-method because we can simply look the name
        up in our nice dictionary.
        """
        return itemname in self._itemmap

    def create_item(self, itemname):
        """
        Creates an item with a given itemname. If that Item already exists,
        raise an Exception.
        """
        if not isinstance(itemname, (str, unicode)):
            raise TypeError, "Itemnames must have string type, not %s" % (str(type(itemname)))

        elif self.has_item(itemname):
            raise ItemAlreadyExistsError, "An Item with the name %r already exists!" % (itemname)

        else:
            self._itemmap[itemname] = self._last_itemid
            self._item_metadata[self._last_itemid] = {}
            self._item_revisions[self._last_itemid] = {} # no revisions yet

            item = Item(self, itemname)
            item._item_id = self._last_itemid

            self._last_itemid += 1

            return item

    def iteritems(self):
        """
        Returns an iterator over all items available in this backend.
        Returns each item and the corresponding item_id in a tuple of the
        form: (item, item_id).
        """
        return self._itemmap.iteritems()

    def _get_item_metadata(self, item):
        return self._item_metadata[item._item_id]

    def _get_revision(self, item, revno):
        """
        For a given Item and Revision number, return the corresponding Revision
        of that Item.
        """
        item_id = item._item_id

        if revno not in self._item_revisions[item_id]:
            raise NoSuchRevisionError, "No Revision #%d on Item %s" % (revno, item.name)

        else:
            revision = Revision(item, revno)
            revision._data = StringIO.StringIO()
            revision._data.write(self._item_revisions[item_id][revno][0])

            revision_metadata = self._item_revisions[item_id][revno][1]


            return revision

    def _list_revisions(self, item):
        """
        For a given Item, list all Revisions. Returns a list of ints representing
        the Revision numbers.
        """
        return self._item_revisions[item._item_id].keys()

    def _create_revision(self, item, revno):
        """
        Takes an Item object and creates a new Revision. Note that you need to pass
        a revision number for concurrency-reasons.
        """
        try:
            last_rev = max(self._item_revisions[item._item_id].iterkeys())

        except ValueError:
            last_rev = -1

        if revno in self._item_revisions[item._item_id]:
            raise RevisionAlreadyExistsError, "A Revision with the number %d already exists on the item %r" % (revno, item.name)

        elif revno != last_rev + 1:
            raise RevisionNumberMismatchError, "The latest revision is %d, thus you cannot create revision number %d. \
                                                The revision number must be latest_revision + 1." % (last_rev, revno)

        else:
            new_revision = NewRevision(item, revno)
            new_revision._revno = revno
            new_revision._data = StringIO.StringIO()

            return new_revision

    def _rename_item(self, item, newname):
        """
        Renames a given item. Raises Exception if the Item you are trying to rename
        does not exist or if the newname is already chosen by another Item.
        """
        if newname in self._itemmap:
            raise ItemAlreadyExistsError, "Cannot rename Item %s to %s since there already is an Item with that name." % (item.name, newname)

        elif not isinstance(newname, (str, unicode)):
            raise TypeError, "Itemnames must have string type, not %s" % (str(type(newname)))

        else:
            name = None

            for itemname, itemid in self._itemmap.iteritems():
                if itemid == item._item_id:
                    name = itemname
                    break

            assert name is not None

            copy_me = self._itemmap[name]
            self._itemmap[newname] = copy_me
            del self._itemmap[name]
            item._name = newname

    def _commit_item(self, item):
        """
        Commits the changes that have been done to a given Item. That is, after you
        created a Revision on that Item and filled it with data you still need to
        commit() it. You don't need to pass what Revision you are committing because
        there is only one possible Revision to be committed for your /instance/ of
        the item and thus the Revision to be saved is memorized.
        """
        revision = item._uncommitted_revision

        if revision.revno in self._item_revisions[item._item_id]:
            item._uncommitted_revision = None                       # Discussion-Log: http://moinmo.in/MoinMoinChat/Logs/moin-dev/2008-06-20 around 17:27
            raise RevisionAlreadyExistsError, "You tried to commit revision #%d on the Item %s, but that Item already has a Revision with that number!" % (revision.revno, item.name)

        else:
            self._item_revisions[item._item_id][revision.revno] = (revision._data.getvalue(), revision._metadata)

            item._uncommitted_revision = None

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
        item = revision._item

        try:
            stored_data = self._item_revisions[item._item_id][revision.revno][0]

        except KeyError:
            return None             # There is no committed data yet.

        else:
            revision._data = StringIO.StringIO()

            if chunksize <= 0:
                revision._data.write(stored_data)
                return revision._data.getvalue()

            else:
                partial_data = stored_data.read(chunksize)
                revision._data.write(partial_data)
                return partial_data

    def _write_revision_data(self, revision, data):
        """
        Write $data to the revisions data.
        """
        revision._data.write(data)


# will be removed as soon as tests are written
if __name__ == "__main__":
    mb = MemoryBackend()
    foo = mb.create_item("foo")
    rev = foo.create_revision(0)
    assert foo._uncommitted_revision is not None
    rev.write_data("asd")
    assert rev._data.getvalue() == "asd"
    foo.commit()
    assert mb._item_revisions[foo._item_id][rev.revno][0] == "asd"
    assert rev.read_data() == "asd"
    print mb._item_revisions
    print "finished"
