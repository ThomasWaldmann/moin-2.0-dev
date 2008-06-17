"""
This represents a simple Backend that stores all data in memory.
This is mainly done for testing and documentation / demonstration purposes.
Thus, this backend IS NOT designed for concurrent use.

DO NOT (even for the smallest glimpse of a second) consider to use this backend
for any production site that needs persistant storage.
(Assuming you got no infinite stream of power-supply.)
"""

from MoinMoin.storage import Backend, Item, Revision, NewRevision

class MemoryBackend(Backend):
    """
    Implementation of the MemoryBackend.
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
            raise KeyError, "No such item, %r" % (itemname)

        elif self.has_item(itemname):
            item_id = self._itemmap[itemname]
            item = Item(self, itemname)
            item._metadata = self._item_metadata[item_id]               # TODO: This is anything but lazy

    def has_item(self, itemname):
        """
        Overriding the default has_item-method because we can simply look the name
        up in our nice dictionary.
        """
        if itemname in self._itemmap:
            return True

        else:
            return False

    def create_item(self, itemname):
        """
        Creates an item with a given itemname. If that Item already exists,
        raise an Exception.
        """
        if not isinstance(itemname, str):
            raise KeyError, "Itemnames must be of type str, not %s" % (str(type(itemname)))

        elif self.has_item(itemname):
            raise KeyError, "An Item with the name %r already exists!" % (itemname)

        else:
            self._itemmap[itemname] = self._last_itemid
            self._item_metadata[self._last_itemid] = {"item_id" : self._last_itemid}
            self._item_revisions[self._last_itemid] = {self._last_itemid : {}}                  # The Item has just been created, thus there are no Revisions

            item = Item(self, itemname)
            item._metadata = self._item_metadata[self._last_itemid]

            self._last_itemid += 1

            return item

    def iteritems(self):
        """
        Returns an iterator over all items available in this backend.
        (Like the dict method).
        """
        return self._items.iteritems()

    def _get_revision(self, item, revno):
        """
        For a given Item and Revision number, return the corresponding Revision
        of that Item.
        """
        item_id = item["item_id"]

        if revno not in self._item_revisions[item_id]:
            raise KeyError, "No Revision #%d on Item %s" % (revno, item._name)

        else:
            revision = Revision(item, revno)
            revision._data = self._item_revisions[item_id][revno][0]
            revision_metadata = self._item_revisions[item_id][revno][1]

            return revision

    def _list_revisions(self, item):
        """
        For a given Item, list all Revisions. Returns a list of ints representing
        the Revision numbers.
        """
        item_id = item["item_id"]

        return self._item_revisions[item_id].keys()

    def _create_revision(self, item, revno):
        """
        Takes an Item object and creates a new Revision. Note that you need to pass
        a revision number for concurrency-reasons.
        """
        item_id = item["item_id"]
        try:
            last_rev = max(self.item_revisions[item_id].iterkeys())

        except ValueError:                  # Maybe the Item has no Revisions yet
            last_rev = -1                   # In that case we want to start with -1+1 = 0

        if revno in self.item_revisions:
            raise KeyError, "A Revision with the number %d already exists on the item %r" % (revno, item._name)

        elif revno != last_rev + 1:
            raise KeyError, "The latest revision is %d, thus you cannot create revision number %d. \
                             The revision number must be latest_revision + 1." % (last_rev, revno)

        else:
            new_revision = NewRevision(item, revno)
            new_revision["revision_id"] = revno

            return new_revision

    def _rename_item(self, item, newname):
        """
        Renames a given item. Raises Exception if the Item you are trying to rename
        does not exist or if the newname is already chosen by another Item.
        """
        if newname in self._itemmap:
            raise KeyError, "Cannot rename Item %s to %s since there already is an Item with that name." % (item._name, newname)

        elif item["item_id"] not in self._itemmap.values():
            raise KeyError, "The Item you are trying to rename doesn't exist any longer."

        elif not isinstance(newname, str):
            raise KeyError, "Itemnames must be of type str, not %s" % (str(type(newname)))

        else:
            copy_me = self._itemmap[item._name] # U
            self._itemmap[newname] = copy_me    # G
            del self._itemmap[item._name]       # L
            item._name = newname                # Y?

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


