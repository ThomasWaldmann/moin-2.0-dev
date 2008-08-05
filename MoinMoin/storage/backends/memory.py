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

import StringIO
from threading import Lock
import time

from MoinMoin.storage import Backend, Item, StoredRevision, NewRevision
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, \
                                   ItemAlreadyExistsError, \
                                   RevisionAlreadyExistsError, RevisionNumberMismatchError


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

        self._item_metadata_lock = {}       # {id : Lockobject}

    def search_item(self, searchterm):
        """
        Takes a searchterm and returns an iterator (maybe empty) over matching
        objects.
        """
        # This is a very very very stupid algorithm
        for item in self.iteritems():
            searchterm.prepare()
            if searchterm.evaluate(item):
                yield item


    def get_item(self, itemname):
        """
        Returns Item object or raises Exception if that Item does not exist.
        """
        if not self.has_item(itemname):
            raise NoSuchItemError("No such item, %r" % (itemname))

        item = Item(self, itemname)
        item._item_id = self._itemmap[itemname]

        if not item._item_id in self._item_metadata:  # Maybe somebody already got an instance of this Item and thus there already is a Lock for that Item.
            self._item_metadata_lock[item._item_id] = Lock()

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
            raise TypeError("Itemnames must have string type, not %s" % (type(itemname)))

        elif self.has_item(itemname):
            raise ItemAlreadyExistsError("An Item with the name %r already exists!" % (itemname))

        item = Item(self, itemname)
        item._item_id = None

        return item

    def iteritems(self):
        """
        Returns an iterator over all items available in this backend.
        """
        for itemname in self._itemmap.keys():
            yield self.get_item(itemname)

    def _get_revision(self, item, revno):
        """
        For a given Item and Revision number, return the corresponding Revision
        of that Item.
        """
        item_id = item._item_id
        revisions = item.list_revisions()

        if revno == -1 and revisions:
            revno = max(item.list_revisions())

        if revno not in self._item_revisions[item_id]:
            raise NoSuchRevisionError("No Revision #%d on Item %s - Available revisions: %r" % (revno, item.name, revisions))

        data = self._item_revisions[item_id][revno][0]
        metadata = self._item_revisions[item_id][revno][1]

        revision = StoredRevision(item, revno, timestamp=metadata['__timestamp'], size=len(data))
        revision._data = StringIO.StringIO(data)

        revision._metadata = metadata

        return revision

    def _list_revisions(self, item):
        """
        For a given Item, list all Revisions. Returns a list of ints representing
        the Revision numbers.
        """
        try:
            return self._item_revisions[item._item_id].keys()
        except KeyError:
            return []

    def _create_revision(self, item, revno):
        """
        Takes an Item object and creates a new Revision. Note that you need to pass
        a revision number for concurrency-reasons.
        """
        try:
            last_rev = max(self._item_revisions[item._item_id].iterkeys())

        except (ValueError, KeyError):
            last_rev = -1

        try:
            if revno in self._item_revisions[item._item_id]:
                raise RevisionAlreadyExistsError("A Revision with the number %d already exists on the item %r" % (revno, item.name))

            elif revno != last_rev + 1:
                raise RevisionNumberMismatchError("The latest revision is %d, thus you cannot create revision number %d. \
                                                   The revision number must be latest_revision + 1." % (last_rev, revno))

        except KeyError:
            pass  # First if-clause will raise an Exception if the Item has just
                  # been created (and not committed), because there is no entry in self._item_revisions yet. Thus, silenced.

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
            raise ItemAlreadyExistsError("Cannot rename Item %s to %s since there already is an Item with that name." % (item.name, newname))

        elif not isinstance(newname, (str, unicode)):
            raise TypeError("Itemnames must have string type, not %s" % (type(newname)))

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

    def _add_item_internally(self, item):
        """
        Given an item, store it in persistently and initialize it. Please note
        that this method takes care of the internal counter we use to give each
        Item a unique ID.
        """
        item._item_id = self._last_itemid
        self._itemmap[item.name] = item._item_id
        self._item_metadata[item._item_id] = {}
        self._item_revisions[item._item_id] = {}  # no revisions yet

        self._item_metadata_lock[item._item_id] = Lock()

        self._last_itemid += 1

    def _commit_item(self, item):
        """
        Commits the changes that have been done to a given Item. That is, after you
        created a Revision on that Item and filled it with data you still need to
        commit() it. You don't need to pass what Revision you are committing because
        there is only one possible Revision to be committed for your /instance/ of
        the item and thus the Revision to be saved is memorized in the items
        _uncommitted_revision attribute.
        """
        revision = item._uncommitted_revision

        if item._item_id is None:
            if self.has_item(item.name):
                raise ItemAlreadyExistsError("You tried to commit an Item with the name %r, but there already is an Item with that name." % item.name)
            self._add_item_internally(item)

        elif self.has_item(item.name) and (revision.revno in self._item_revisions[item._item_id]):
            item._uncommitted_revision = None  # Discussion-Log: http://moinmo.in/MoinMoinChat/Logs/moin-dev/2008-06-20 around 17:27
            raise RevisionAlreadyExistsError("A Revision with the number %d already exists on the Item %r!" % (revision.revno, item.name))

        revision._data.seek(0)

        if revision.timestamp is None:
            revision.timestamp = long(time.time())

        if revision._metadata is None:
            revision._metadata = {}
        revision._metadata['__timestamp'] = revision.timestamp
        self._item_revisions[item._item_id][revision.revno] = (revision._data.getvalue(), revision._metadata.copy())

        item._uncommitted_revision = None

    def _rollback_item(self, item):
        """
        This method is invoked when external events happen that cannot be handled in a
        sane way and thus the changes that have been made must be rolled back.
        """
        # Since we have no temporary files or other things to deal with in this backend,
        # we can just set the items uncommitted revision to None and go on with our life.
        item._uncommitted_revision = None

    def _change_item_metadata(self, item):
        """
        This method is used to acquire a lock on an Item. This is necessary to prevent
        side-effects caused by concurrency.
        """
        if item._item_id is None:
            # If this is the case it means that we operate on an Item that has not been
            # committed yet and thus we should not use a Lock in persistant storage.
            pass
        else:
            self._item_metadata_lock[item._item_id].acquire()

    def _publish_item_metadata(self, item):
        """
        This method tries to release a lock on the given Item.
        """
        if item._item_id is None:
            # not committed yet, no locking, store item
            self._add_item_internally(item)
        else:
            self._item_metadata_lock[item._item_id].release()

        if item._metadata is not None:
            self._item_metadata[item._item_id] = item._metadata.copy()
        else:
            self._item_metadata[item._item_id] = {}

    def _read_revision_data(self, revision, chunksize):
        """
        Called to read a given amount of bytes of a revisions data. By default, all
        data is read.
        """
        if chunksize < 0:
            return revision._data.read()

        return revision._data.read(chunksize)

    def _write_revision_data(self, revision, data):
        """
        Write $data to the revisions data.
        """
        revision._data.write(data)

    def _get_item_metadata(self, item):
        """
        Load metadata for a given item, return dict.
        """
        try:
            return dict(self._item_metadata[item._item_id])

        except KeyError:  # The Item we are operating on has not been committed yet.
            return dict()

    def _get_revision_metadata(self, revision):
        """
        Load metadata for a given Revision, returns dict.
        """
        item = revision._item

        return self._item_revisions[item._item_id][revision.revno][1]

    def _seek_revision_data(self, revision, position, mode):
        """
        Set the revisions cursor on the revisions data.
        """
        revision._data.seek(position, mode)
