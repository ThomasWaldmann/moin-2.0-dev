"""
    MoinMoin SQL storage version 1

    This is an example SQL storage backend. It is written mostly to point
    out problems in the storage code. Read the code in this file completely
    to understand, it's only a few hundred lines many of which comments.

    To test, create wikiconfig_local.py with the following contents:
    ---%<---
    import os
    from wikiconfig import LocalConfig
    from MoinMoin.storage.backends.sql1 import SQL1

    class Config(LocalConfig):
        caching_formats = []

        def __init__(self, siteid):
            dbfile = os.path.join(self.moinmoin_dir, 'wiki', 'moin.sqlite')
            # should be before LocalConfig.__init__ to avoid having that
            # instantiate filesystem backends
            self.data_backend = SQL1(self, dbfile)
            LocalConfig.__init__(self, siteid)
    --->%---

    and run:

    $ sqlite3 wiki/moin.sqlite < MoinMoin/storage/backends/sql1.sql

    to (re-)init the database.


    This is intentionally named 'SQL1' to indicate that a new version ought
    to be written that improves the database schema. Notable improvements
    to be made are:
     * Let somebody who has a clue about databases look at this backend,
       I can barely remember SQL syntax.
     * Do not store metadata key as string for every item but instead
       normalize that to have a 'metadata keys' table and just mapping
       the key ID from that table to the metadata value. That should save
       quite a lot of database space and make some queries more efficient.
     * Use BLOBs for data (and metadata values?)
     * Normalise revision data to not store duplicate BLOBs
     * Add indexes
     * Metadata objects should cache the value for positive and the fact
       that the key didn't exist for negative lookups to cut down on SQL
       statements. This, however, only works when the metadata may not be
       modified which is currently the case for revision metadata but not
       for item metadata. See the LOCKFREE file ("further considerations")
       for more info on how this is used and should be done.
     * ...?

    @copyright: 2008 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

# shouldn't be too tied to sqlite...
from pysqlite2 import dbapi2 as db

import UserDict
import time
from cPickle import loads, dumps
import weakref


# Do this up-front to exclude python 2.3
try:
    from threading import local as threadlocal
except ImportError:
    from dummy_threading import local as threadlocal

# Now detect whether threading is actually possible
try:
    import threading
    threadlocal = threadlocal()
except ImportError:
    threadlocal = None

logger = None
# Enable this instead to see how many redundant SQL queries are done
# due to the storage API design.
#
#import logging
#logger = logging.getLogger(__name__).info


from MoinMoin.search import term
from MoinMoin.storage.external import ACL
from MoinMoin.storage.error import LockingError
from MoinMoin.storage.interfaces import StorageBackend, DataBackend, MetadataBackend
from MoinMoin.storage.backends.common import _get_item_metadata_cache


# So much work just to log SQL statements and be able to make
# weak references to a connection. Are connections even closed
# automatically?
class LoggingConnection(object):
    def __init__(self, real):
        self.real = real
    def __hasattr__(self, name):
        return hasattr(self.real, name)
    def __getattr__(self, name):
        return getattr(self.real, name)
    # avoid overhead when no logging defined
    if logger:
        def cursor(self):
            class LoggingCursor(object):
                def __init__(self, real):
                    self.real = real
                def __iter__(self):
                    return self.real
                def __hasattr__(self, name):
                    return hasattr(self.real, name)
                def __getattr__(self, name):
                    return getattr(self.real, name)
                def execute(self, *args):
                    logger('%r' % (args, ))
                    return self.real.execute(*args)
            return LoggingCursor(self.real.cursor())


class SQL1(StorageBackend):
    name = "sql1"

    def __init__(self, cfg, dbname):
        StorageBackend.__init__(self)
        self.dbname = dbname

        # Eep. Generic code assumes _other is present? WTF?
        self._other = self

        # Eep. Generic code assumes access to config although
        # generally the backend is configured *within* the
        # config and can't actually access it, to do this the
        # user has to do an ugly workaround like this in the
        # example config file in the docstring above, see how
        # it needs to override the config's constructor!
        #
        # The need for this access is due to the ACL checking
        # design in the storage code, see LOCKFREE.
        self._cfg = cfg

        # Eep. See lock() method.
        self._locks = {}

    def get_conn(self):
        if threadlocal:
            # Python doesn't seem to clean out the thread-local
            # storage when a thread exits. Hence, let's keep only
            # a weak reference to the connection in the thread-
            # local storage and create a timer that, for 5 seconds,
            # keeps a strong reference. Once the timer exits, the
            # strong reference is removed and the connection freed.

            if hasattr(threadlocal, 'moin_sql1_connections'):
                # dereference weakref if there is one for us
                try:
                    conn = threadlocal.moin_sql1_connections[self]()
                except KeyError:
                    conn = None
            else:
                threadlocal.moin_sql1_connections = {}
                conn = None

            if not conn:
                conn = LoggingConnection(db.connect(self.dbname))
                threadlocal.moin_sql1_connections[self] = weakref.ref(conn)
                tmr = threading.Timer(5.0, lambda x: x, (conn, ))
                tmr.start()

            return conn
        else:
            # non-threading case, just cache a connection in self, no need to
            # expire it (either it will be reused or the process will end at
            # some point), no danger of accumulating lots of connections.
            if not hasattr(self, '_connection'):
                self._connection = LoggingConnection(db.connect(self.dbname))

            return self._connection

    conn = property(get_conn)

    def _get_item_path(self, name):
        # Eep. Used for caching, not good! Even if we disable
        # the text_html caching, pagelinks will still be stored
        # here!
        #
        # NB: don't add caching to the backend, use a separate
        #     cache manager class so that e.g. a server farm
        #     can access a common database but still do local
        #     caching for better performance and less database
        #     hitting. Mind that sessions are currently also
        #     stored in the cache and need to be shared across
        #     the server farm, all caching should be revisisted
        #     and changed if it needs to be global like the
        #     the session storage. Maybe a separate session
        #     storage should be configurable.
        #
        # This is also used for attachments. Those need to be
        # converted to real items.
        return "/tmp/moin-dummy/"

    def list_items(self, filter):
        # Not optimised right now.
        #
        # Some database magic is required to actually optimise this because
        # the metadata filter want to look at the item's metadata as well
        # as the *last* revision's! I tried implementing that in SQL but
        # haven't managed so far. Will be more efficient with the metadata
        # key normalisation mentioned at the top of the file.
        #
        # If this method was to return an iterator over Item objects, then
        # it would be possible to use the item ID here rather than the item
        # name and actually return a valid reference to the item, as it is
        # an item that is found via this method can be renamed after found
        # but before being accessed. This would, however, require larger
        # changes since everything wants to get a name list from this...
        cursor = self.conn.cursor()

        cursor.execute('SELECT itemname FROM items')

        for name, in cursor:
            filter.prepare()
            if not filter.evaluate(self, name, _get_item_metadata_cache(self, name)):
                continue
            yield name

    def has_item(self, name):
        # Eep. has_item() isn't really all that useful, a fraction of a second
        # later the item could have been renamed! Rename this function to
        # get_item() and have it return an actual item instance that contains
        # the itemid (or None, of course) so that renames won't matter.
        cursor = self.conn.cursor()
        cursor.execute('SELECT ID FROM items WHERE itemname = ?', (name, ))
        itemid = cursor.fetchone()
        # API braindamage. The only reason for the return value to be the
        # backend must have been a useless micro-optimisation for the special
        # case of the layered backend (see code there) which must be changed
        # anyway to support copy-on-write semantics in that backend. Hence,
        # this should be changed to return just a bool.
        return itemid and self or None

    def create_item(self, name):
        # Eep. What's this create_item thing good for? I think it'd be better
        # if this returned an Item() instance that could be modified and then
        # at the end *saved* rather than requiring remove_item() to be called
        # if the item turned out to be unwanted!
        # create_item is called when the editor is *invoked* is beyond me to
        # enable adding the edit-lock metadata to the item, but the subsequent
        # removal when the editor is canceled is rather unsafe (see BUGS),
        #
        # Note that all this is only required for edit-locking. If a solution
        # for edit-locks can be designed that works
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO items (itemname) VALUES (?)', (name, ))
        cursor.connection.commit()

    def remove_item(self, name):
        # Leaves the actual item data dangling, but IFF the API was done
        # properly this means it could actually be done concurrently with
        # read accesses to the item since the item ID is all that's needed
        # for the read access!
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM items WHERE itemname = ?', (name, ))
        cursor.connection.commit()

    def rename_item(self, name, newname):
        # Similar to remove_item except that nothing is left dangling,
        # if the API was done properly this wouldn't have to affect any
        # read operations.
        cursor = self.conn.cursor()
        cursor.execute('UPDATE items SET itemname = ? WHERE itemname = ?', (newname, name))
        cursor.connection.commit()

    def list_revisions(self, name):
        # If we were given an Item object we would already know
        # the itemid and would save one query as well as being
        # safe against concurrent renames.
        cursor = self.conn.cursor()
        cursor.execute('SELECT ID FROM items WHERE itemname = ?', (name, ))
        itemid = cursor.fetchone()[0]
        cursor.execute('SELECT revno FROM revisions WHERE itemid = ?', (itemid, ))
        revisions = list(cursor.fetchall() or [])
        revisions.sort()
        revisions.reverse()
        revisions = [x[0] for x in revisions]
        return revisions

    def current_revision(self, name):
        # If we were given an Item object we would already know
        # the itemid and would save one query as well as being
        # safe against concurrent renames.
        cursor = self.conn.cursor()
        cursor.execute('SELECT ID FROM items WHERE itemname = ?', (name, ))
        itemid = cursor.fetchone()[0]
        cursor.execute('SELECT revno FROM revisions WHERE itemid = ? ORDER BY -revno', (itemid, ))
        rev = cursor.fetchone()
        if rev:
            return rev[0]
        return 0

    def has_revision(self, name, revno):
        # If we were given an Item object we would already know
        # the itemid and would save one query as well as being
        # safe against concurrent renames.
        cursor = self.conn.cursor()
        cursor.execute('SELECT ID FROM items WHERE itemname = ?', (name, ))
        itemid = cursor.fetchone()[0]
        cursor.execute('SELECT revno FROM revisions WHERE itemid = ? AND revno = ?', (itemid, revno))
        return len(cursor.fetchall())

    def create_revision(self, name, revno):
        # If we were given an Item object we would already know
        # the itemid and would save one query as well as being
        # safe against concurrent renames.
        cursor = self.conn.cursor()
        cursor.execute('SELECT ID FROM items WHERE itemname = ?', (name, ))
        itemid = cursor.fetchone()[0]
        # Eep. The timestamp here should be given by the API explicitly!
        # Or are we required to store the EDIT_LOG_MTIME metadata instead,
        # in which case we could simply use a different query for news()
        # below? That doesn't quite seem to fit in with the API not knowing
        # about it so I'd much prefer if the timestamp was handed in here
        # or actually required to be updated on any change to the revision.
        cursor.execute('INSERT INTO revisions (itemid, revno, lastupdate) VALUES (?, ?, ?)', (itemid, revno, int(time.time())))
        cursor.connection.commit()

    def remove_revision(self, name, revno):
        # If we were given a Revision object we would already know
        # the revision's ID and would save one query as well as being
        # safe against concurrent item renames.
        #
        # Eep. Should remove all data as well.
        cursor = self.conn.cursor()
        cursor.execute('SELECT ID FROM items WHERE itemname = ?', (name, ))
        itemid = cursor.fetchone()[0]
        cursor.execute('DELETE from revisions WHERE itemid = ? AND revno = ?', (itemid, revno))
        cursor.connection.commit()

    def get_metadata_backend(self, name, revno):
        # If we were given a Revision object we would already know
        # the revision's ID/itemid and would save one query as well
        # as being safe against concurrent item renames. We would
        # then also pass the revision ID to the metadata object.
        cursor = self.conn.cursor()
        cursor.execute('SELECT ID FROM items WHERE itemname = ?', (name, ))
        itemid = cursor.fetchone()[0]
        if revno == -1:
            return SQL1ItemMetadata(self.get_conn, itemid)
        return SQL1RevisionMetadata(self.get_conn, itemid, revno)

    def get_data_backend(self, name, revno):
        # If we were given a Revision object we would already know
        # the revision's ID and would save one query as well as
        # being safe against concurrent item renames. We would
        # then also pass the revision ID to the data object.
        cursor = self.conn.cursor()
        cursor.execute('SELECT ID FROM items WHERE itemname = ?', (name, ))
        itemid = cursor.fetchone()[0]
        return SQL1Data(self.get_conn, itemid, revno)

    def lock(self, identifier, timeout=1, lifetime=60):
        # Eep. This is not a proper implementation, needs timeout and lifetime.
        #
        # But see BUGS file, I think locking should be done by a separate lock
        # manager 'backend'.
        #
        # Also, however, compare to the implementation in BaseFilesystemBackend
        # which needs to keep a lock cache. The correct way to implement this
        # would in my opinion be returning a lock object here that would have
        # an unlock() method (and a __del__ method to unlock and complain loudly
        # if it is destroyed without unlocking!) which would also avoid any
        # problems with the lock IDs. Then, no unlock() method would be needed
        # on the backend level (although the Lock() class could be generic and
        # call self.backend.unlock(self)), e.g.:
        #
        # class Lock(object):
        #     def __init__(self, backend, identifier, lockid):
        #         self.backend = backend
        #         self.identifier = identifier
        #         self.lockid = lockid
        #     def unlock(self):
        #         self.backend.unlock(self.lockid) # or self? or both?
        #     def __del__(self):
        #         logging.error("Lock %s (lockid = %r) not released!" % (self.identifier, self.lockid))
        #         self.unlock()
        #
        # Then, this method could be implemented as
        #   [...]
        #   lock = Lock(self, identifier, curs.fetchone()[0])
        #   cursor.connection.commit()
        #   return lock
        #
        # And unlock() would use the lockid instead of having to look into
        # the dict. At first, that might not seem like a big thing, but
        # when you consider the case where locks actually time out due to
        # their lifetime limitation, the picture is quite different.
        try:
            cursor = self.conn.cursor()
            cursor.execute('INSERT INTO locks (lockname) VALUES (?)', (identifier, ))
            cursor.connection.commit()
            self._locks[identifier] = cursor.lastrowid
        except db.IntegrityError:
            raise LockingError("lock exists")

    def unlock(self, identifier):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM locks WHERE ID = ?', (self._locks[identifier], ))
        cursor.connection.commit()

    def news(self, timestamp=0):
        # Eep. No documentation, but timestamp is in time.time() format,
        # i.e. seconds since epoch. We ignore any fractions of a second.
        # Also, docstring in interfaces.py gives wrong return tuple order...
        #
        # Since this is an iterator, it could return the actual Item()
        # instance instead of the item name as the last parameter, in
        # which case we could again optimise this a lot by loading the
        # item ID into the object so that subsequent accesses to the object
        # would not need to look up the item ID by item name first.
        #
        # Alternatively, a Revision() object could be returned instead
        # of the revno, itemname part of the tupe.
        timestamp = int(timestamp)
        cursor = self.conn.cursor()
        cursor.execute('SELECT revisions.lastupdate, revisions.revno, items.itemname'
                       ' FROM items, revisions'
                       ' WHERE revisions.itemid = items.ID AND revisions.lastupdate >= ?'
                       ' ORDER BY -revisions.lastupdate, -revisions.revno',
                       (timestamp, ))
        # cursor is iterable
        return cursor


class SQL1Data(DataBackend):
    # Eep. This should probably be implemented using the BLOB datatype.
    def __init__(self, get_conn, itemid, revno):
        self.get_conn = get_conn
        self.conn = property(get_conn)
        self.itemid = itemid
        self.revno = revno
        self._data = None
        cursor = self.get_conn().cursor()
        cursor.execute('SELECT ID FROM revisions WHERE itemid = ? AND revno = ?', (self.itemid, self.revno))
        self.revid = cursor.fetchone()[0]

    def _get_data(self):
        if self._data is None:
            cursor = self.get_conn().cursor()
            cursor.execute('SELECT data FROM revdata WHERE revid = ?', (self.revid, ))
            data = cursor.fetchone() or [u'']
            self._data = data[0]
        return self._data

    data = property(_get_data)

    # Eep! This API with seek and all that is definitely overkill!
    # Also, the filesystem backend code does something very strange
    # with separate read and write files. That doesn't fit in with
    # `tell' and `seek' since ... which one do they operate on?
    # I suggest to just kill the whole API and not implement seek/tell
    # at all.
    # For attachments it might be useful to be able to not read the
    # whole file into memory in which case progressive read/write
    # might make sense, but that remains to be seen.
    #
    # Alternatively, the parent class (DataBackend) could implement
    # all this read/write business with temporary files and just
    # tell this class when to update the database and give us a
    # file descriptor to read from for .write() so we can even give
    # that right to the database if it is running on the same host.
    # The filesystem backends would want to override such behaviour
    # to create the temporary file in a place safe for os.rename(),
    # but they still can if the parent class implements it.
    def read(self, size=None):
        assert not size
        return self.data

    def seek(self, offset):
        assert False

    def tell(self):
        assert False

    def write(self, data):
        self._data = data
        cursor = self.get_conn().cursor()
        cursor.execute('DELETE FROM revdata WHERE revid = ?', (self.revid, ))
        cursor.execute('INSERT INTO revdata (revid, data) VALUES (?, ?)', (self.revid, data))
        cursor.connection.commit()

    def close(self):
        # Eep. Do we need to implement a commit here?
        # If so, easy: we write to a separate database record and
        # then here change the IDs to link it to the right item,
        # then drop the old one.
        pass

# Eep. MetadataBackend should provide the dict mixin
class SQL1RevisionMetadata(UserDict.DictMixin, MetadataBackend):
    def __init__(self, get_conn, itemid, revno):
        MetadataBackend.__init__(self)
        self.get_conn = get_conn
        self.itemid = itemid
        self.revno = revno

    def __contains__(self, key):
        cursor = self.get_conn().cursor()
        cursor.execute('SELECT ID FROM revisions WHERE itemid = ? AND revno = ?', (self.itemid, self.revno))
        revid = cursor.fetchone()[0]
        cursor.execute('SELECT metakey FROM revmeta WHERE revid = ? AND metakey = ?', (revid, key))
        return bool(cursor.fetchone())

    def __getitem__(self, key):
        cursor = self.get_conn().cursor()
        cursor.execute('SELECT ID FROM revisions WHERE itemid = ? AND revno = ?', (self.itemid, self.revno))
        revid = cursor.fetchone()[0]
        cursor.execute('SELECT metavalue FROM revmeta WHERE revid = ? AND metakey = ?', (revid, key))
        try:
            return loads(str(cursor.fetchone()[0]))
        except:
            raise KeyError()

    def __setitem__(self, key, value):
        cursor = self.get_conn().cursor()
        cursor.execute('SELECT ID FROM revisions WHERE itemid = ? AND revno = ?', (self.itemid, self.revno))
        revid = cursor.fetchone()[0]
        cursor.execute('DELETE FROM revmeta WHERE revid=? AND metakey=?', (revid, key))
        value = dumps(value)
        cursor.execute('INSERT INTO revmeta (revid, metakey, metavalue) VALUES (?, ?, ?)', (revid, key, value))
        cursor.connection.commit()

    def __delitem__(self, key):
        cursor = self.get_conn().cursor()
        cursor.execute('SELECT ID FROM revisions WHERE itemid = ? AND revno = ?', (self.itemid, self.revno))
        revid = cursor.fetchone()[0]
        cursor.execute('DELETE FROM revmeta WHERE revid=? AND metakey=?', (revid, key))
        cursor.connection.commit()

    def keys(self):
        cursor = self.get_conn().cursor()
        cursor.execute('SELECT ID FROM revisions WHERE itemid = ? AND revno = ?', (self.itemid, self.revno))
        revid = cursor.fetchone()[0]
        cursor.execute('SELECT metakey FROM revmeta WHERE revid=?', (revid, ))
        return [v[0] for v in cursor.fetchall()]

    # Eep. Implement __iter__ and iteritems() more efficiently.

    def save(self):
        # Eep. Implementation updates on-the-fly instead of being lazy.
        # Laziness should be implemented in the base class!!
        pass

# Eep. MetadataBackend should provide the dict mixin
class SQL1ItemMetadata(UserDict.DictMixin, MetadataBackend):
    def __init__(self, get_conn, itemid):
        MetadataBackend.__init__(self)
        self.get_conn = get_conn
        self.itemid = itemid

    def __contains__(self, key):
        cursor = self.get_conn().cursor()
        cursor.execute('SELECT metakey FROM itemmeta WHERE itemid = ? AND metakey = ?', (self.itemid, key))
        return bool(cursor.fetchone())

    def __getitem__(self, key):
        cursor = self.get_conn().cursor()
        cursor.execute('SELECT metavalue FROM itemmeta WHERE itemid = ? AND metakey = ?', (self.itemid, key))
        try:
            return loads(str(cursor.fetchone()[0]))
        except:
            raise KeyError()

    def __setitem__(self, key, value):
        cursor = self.get_conn().cursor()
        cursor.execute('DELETE FROM itemmeta WHERE itemid=? AND metakey=?', (self.itemid, key))
        value = dumps(value)
        cursor.execute('INSERT INTO itemmeta (itemid, metakey, metavalue) VALUES (?, ?, ?)', (self.itemid, key, value))
        cursor.connection.commit()

    def __delitem__(self, key):
        cursor = self.get_conn().cursor()
        cursor.execute('DELETE FROM itemmeta WHERE itemid=? AND metakey=?', (self.itemid, key))
        cursor.connection.commit()

    def keys(self):
        cursor = self.get_conn().cursor()
        cursor.execute('SELECT metakey FROM itemmeta WHERE itemid = ?', (self.itemid, ))
        return [v[0] for v in cursor.fetchall()]

    # Eep. Implement __iter__ and iteritems() more efficiently.

    def save(self):
        # Eep. Implementation updates on-the-fly instead of being lazy.
        # Laziness should be implemented in the base class!!
        pass
