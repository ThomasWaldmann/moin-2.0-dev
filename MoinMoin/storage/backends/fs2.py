"""
    MoinMoin - FS2 backend

    Features:
    * store metadata and data separately
    * use uuids for item storage names
    * uses content hash addressing for revision data storage
    * use sqlalchemy/sqlite (not cdb/self-made DBs like fs does)

    @copyright: 2008 MoinMoin:JohannesBerg ("fs2" is originally based on "fs" from JB),
                2009-2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import os, tempfile, errno, shutil, time
from uuid import uuid4 as make_uuid

import cPickle as pickle

from sqlalchemy import create_engine, MetaData, Table, Column, String, Unicode, Integer
from sqlalchemy.exceptions import IntegrityError

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.util.lock import ExclusiveLock
from MoinMoin.util import filesys

from MoinMoin.storage import Backend, Item, StoredRevision, NewRevision
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, \
                                   ItemAlreadyExistsError, \
                                   RevisionAlreadyExistsError, RevisionNumberMismatchError, \
                                   CouldNotDestroyError

PICKLEPROTOCOL = 1

MAX_NAME_LEN = 500
HASH_NAME = 'sha1' # XXX use request.cfg.hash_algorithm
HASH_HEX_LEN = 40 # sha1 = 160 bit
UUID_LEN = len(make_uuid().hex)


class FS2Backend(Backend):
    """
    FS2 backend
    """
    def __init__(self, path):
        """
        Initialise filesystem backend, creating initial files and some internal structures.

        @param path: storage path
        """
        self._path = path

        # create <path>, meta data and revision content data storage subdirs
        meta_path = self._make_path('meta')
        data_path = self._make_path('data')
        for path in (self._path, meta_path, data_path):
            try:
                os.makedirs(path)
            except OSError, err:
                if err.errno != errno.EEXIST:
                    raise BackendError(str(err))

        engine = create_engine('sqlite:///%s' % self._make_path('index_history.db'), echo=False)
        metadata = MetaData()
        metadata.bind = engine

        # item_name -> item_id mapping
        self._name2id = Table('name2id', metadata,
                            Column('item_name', Unicode(MAX_NAME_LEN), primary_key=True),
                            Column('item_id', String(UUID_LEN), index=True, unique=True),
                        )
        # history (e.g. for RecentChanges)
        self._history = Table('history', metadata,
                            Column('id', Integer, primary_key=True),
                            Column('item_id', String(UUID_LEN)),
                            Column('rev_id', Integer),
                            Column('ts', Integer),
                        )

        metadata.create_all()

    def _make_path(self, *args):
        return os.path.join(self._path, *args)

    def _get_fs_path_data(self, rev):
        if rev._fs_metadata is None:
            self._get_revision_metadata(rev)
        data_hash = rev._fs_metadata[HASH_NAME]
        return self._make_path('data', data_hash)

    def history(self, reverse=True):
        """
        History implementation reading the history table.
        """
        history = self._history
        name2id = self._name2id
        results = history.select().order_by(history.id).execute()
        if reverse:
            results = reverse(results)
        for row in results:
            item_id, revno, ts = row
            assert isinstance(item_id, str)  # item_id = str(item_id)
            try:
                # try to open the revision file just in case somebody removed it manually
                mp = self._make_path('meta', item_id, '%d.rev' % revno)
                f = open(mp)
                f.close()
            except IOError, err:
                if err.errno != errno.ENOENT:
                    raise
                # oops, no such file, item/revision removed manually?
                continue
            item_name = self._get_item_name(item_id) # this is the current name, NOT the name at revno
            item = Item(self, item_name)
            item._fs_item_id = item_id
            rev = StoredRevision(item, revno, ts)
            rev._fs_path_meta = mp
            rev._fs_file_meta = None
            rev._fs_file_data = None
            rev._fs_metadata = None
            yield rev
        results.close()

    def _addhistory(self, itemid, revid, ts):
        """
        Add a history item with current timestamp and the given data.

        @param itemid: item's ID, string
        @param revid: revision ID, must be an integer
        @param ts: timestamp
        """
        history = self._history
        history.insert().values(item_id=itemid, rev_id=revid, timestamp=ts).execute()

    def _get_item_id(self, itemname):
        """
        Get ID of item (or None if no such item exists)

        @param itemname: name of item (unicode)
        """
        name2id = self._name2id
        results = name2id.select(name2id.c.item_name==itemname).execute()
        row = results.fetchone()
        results.close()
        if row is not None:
            item_id = row[name2id.c.item_id]
            item_id = str(item_id) # we get unicode
            return item_id

    def _get_item_name(self, itemid):
        """
        Get name of item (or None if no such item exists)

        @param itemid: id of item (str)
        """
        name2id = self._name2id
        results = name2id.select(name2id.c.item_id==itemid).execute()
        row = results.fetchone()
        results.close()
        if row is not None:
            item_name = row[name2id.c.item_name]
            return item_name

    def get_item(self, itemname):
        item_id = self._get_item_id(itemname)
        if item_id is None:
            raise NoSuchItemError("No such item '%r'." % itemname)

        item = Item(self, itemname)
        item._fs_item_id = item_id
        item._fs_metadata = None

        return item

    def has_item(self, itemname):
        return self._get_item_id(itemname) is not None

    def create_item(self, itemname):
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Item names must be of str/unicode type, not %s." % type(itemname))

        elif self.has_item(itemname):
            raise ItemAlreadyExistsError("An item '%r' already exists!" % itemname)

        item = Item(self, itemname)
        item._fs_item_id = None
        item._fs_metadata = {}

        return item

    def iteritems(self):
        name2id = self._name2id
        results = name2id.select().execute()
        for row in results:
            item_name = row[name2id.c.item_name]
            item_id = row[name2id.c.item_id]
            item_id = str(item_id) # we get unicode!
            item = Item(self, item_name)
            item._fs_item_id = item_id
            yield item
        results.close()

    def _get_revision(self, item, revno):
        item_id = item._fs_item_id

        if revno == -1:
            revs = item.list_revisions()
            if not revs:
                raise NoSuchRevisionError("Item has no revisions.")
            revno = max(revs)

        mp = self._make_path('meta', item_id, '%d.rev' % revno)
        if not os.path.exists(mp):
            raise NoSuchRevisionError("Item '%r' has no revision #%d." % (item.name, revno))

        rev = StoredRevision(item, revno)
        rev._fs_path_meta = mp
        rev._fs_path_data = None
        rev._fs_file_meta = None
        rev._fs_file_data = None
        rev._fs_metadata = None

        return rev

    def _list_revisions(self, item):
        if item._fs_item_id is None:
            return []
        p = self._make_path('meta', item._fs_item_id)
        l = os.listdir(p)
        suffix = '.rev'
        ret = [int(i[:-len(suffix)]) for i in l if i.endswith(suffix)]
        ret.sort()
        return ret

    def _create_revision(self, item, revno):
        if item._fs_item_id is None:
            revs = []
        else:
            revs = self._list_revisions(item)
        last_rev = max(-1, -1, *revs)

        if revno in revs:
            raise RevisionAlreadyExistsError("Item '%r' already has a revision #%d." % (item.name, revno))
        elif revno != last_rev + 1:
            raise RevisionNumberMismatchError("The latest revision of the item '%r' is #%d, thus you cannot create revision #%d. \
                                               The revision number must be latest_revision + 1." % (item.name, last_rev, revno))

        rev = NewRevision(item, revno)
        rev._revno = revno

        fd, rev._fs_path_meta = tempfile.mkstemp('.tmp', '', self._make_path('meta'))
        rev._fs_file_meta = os.fdopen(fd, 'wb') # XXX keeps file open as long a rev exists

        fd, rev._fs_path_data = tempfile.mkstemp('.tmp', '', self._make_path('data'))
        rev._fs_file_data = os.fdopen(fd, 'wb') # XXX keeps file open as long a rev exists
        return rev

    def _destroy_revision(self, rev):
        if rev._fs_file_meta is not None:
            rev._fs_file_meta.close()
        if rev._fs_file_data is not None:
            rev._fs_file_data.close()
        try:
            os.unlink(rev._fs_path_meta)
            os.unlink(rev._fs_path_data)
        except OSError, err:
            if err.errno != errno.ENOENT:
                raise CouldNotDestroyError("Could not destroy revision #%d of item '%r' [errno: %d]" % (
                    rev.revno, rev.item.name, err.errno))
            #else:
            #    someone else already killed this revision, we silently ignore this error

    def _do_locked(self, lockname, fn, arg):
        l = ExclusiveLock(lockname, 30)
        l.acquire(30)
        try:
            ret = fn(arg)
        finally:
            l.release()

        return ret

    def _rename_item_locked(self, arg):
        item, newname = arg
        item_id = item._fs_item_id

        name2id = self._name2id
        try:
            results = name2id.update().where(name2id.c.item_id==item_id).values(item_name=newname).execute()
        except IntegrityError:
            raise ItemAlreadyExistsError("Target item '%r' already exists!" % newname)

    def _rename_item(self, item, newname):
        self._do_locked(self._make_path('name-mapping.lock'),
                        self._rename_item_locked, (item, newname))

    def _add_item_internally_locked(self, arg):
        """
        See _add_item_internally, this is just internal for locked operation.
        """
        item, revmeta, revdata, revdata_target, itemmeta = arg
        item_id = make_uuid().hex
        item_name = item.name

        name2id = self._name2id
        try:
            results = name2id.insert().values(item_id=item_id, item_name=item_name).execute()
        except IntegrityError:
            raise ItemAlreadyExistsError("Item '%r' already exists!" % item_name)

        os.mkdir(self._make_path('meta', item_id))

        if revdata is not None:
            filesys.rename(revdata, revdata_target)

        if revmeta is not None:
            rp = self._make_path('meta', item_id, '%d.rev' % 0)
            filesys.rename(revmeta, rp)

        if itemmeta:
            # only write item level metadata file if we have any
            mp = self._make_path('meta', item_id, 'item')
            f = open(mp, 'wb')
            pickle.dump(itemmeta, f, protocol=PICKLEPROTOCOL)
            f.close()

        item._fs_item_id = item_id

    def _add_item_internally(self, item, revmeta=None, revdata=None, revdata_target=None, itemmeta=None):
        """
        This method adds a new item. It locks the name-mapping database to
        ensure putting the item into place and adding it to the name-mapping
        db is atomic.

        If the newrev or metadata arguments are given, then it also adds the
        revision or metadata to the item before making it discoverable.

        If the item's name already exists, it doesn't do anything but raise
        a ItemAlreadyExistsError; if the newrev was given the file is unlinked.

        @param revmeta: new revision's temporary meta file path
        @param revdata: new revision's temporary data file path
        @param itemmeta: item metadata dict
        """
        self._do_locked(self._make_path('name-mapping.lock'),
                        self._add_item_internally_locked, (item, revmeta, revdata, revdata_target, itemmeta))

    def _commit_item(self, rev):
        if rev.timestamp is None:
            rev.timestamp = long(time.time())

        item = rev.item
        metadata = {'__timestamp': rev.timestamp}
        metadata.update(rev)
        md = pickle.dumps(metadata, protocol=PICKLEPROTOCOL)

        rev._fs_file_meta.write(md)
        rev._fs_file_meta.close()

        data_hash = metadata[HASH_NAME]

        pd = self._make_path('data', data_hash)
        if item._fs_item_id is None:
            self._add_item_internally(item, revmeta=rev._fs_path_meta, revdata=rev._fs_path_data, revdata_target=pd)
        else:
            try:
                filesys.rename_no_overwrite(rev._fs_path_data, pd, delete_old=True)
            except OSError, err:
                if err.errno != errno.EEXIST:
                    raise

            pm = self._make_path('meta', item._fs_item_id, '%d.rev' % rev.revno)
            try:
                filesys.rename_no_overwrite(rev._fs_path_meta, pm, delete_old=True)
            except OSError, err:
                if err.errno != errno.EEXIST:
                    raise
                raise RevisionAlreadyExistsError("")

        self._addhistory(item._fs_item_id, rev.revno, rev.timestamp)

    def _rollback_item(self, rev):
        rev._fs_file_meta.close()
        rev._fs_file_data.close()
        os.unlink(rev._fs_path_meta)
        os.unlink(rev._fs_path_data)

    def _destroy_item_locked(self, item):
        item_id = item._fs_item_id

        name2id = self._name2id
        results = name2id.delete().where(name2id.c.item_id==item_id).execute()

        path = self._make_path('meta', item_id)
        try:
            shutil.rmtree(path)
        except OSError, err:
            raise CouldNotDestroyError("Could not destroy item '%r' [errno: %d]" % (
                item.name, err.errno))
        # XXX do refcount data files and if zero, kill it

    def _destroy_item(self, item):
        self._do_locked(self._make_path('name-mapping.lock'),
                        self._destroy_item_locked, item)

    def _change_item_metadata(self, item):
        if not item._fs_item_id is None:
            lp = self._make_path('meta', item._fs_item_id, 'item.lock')
            item._fs_metadata_lock = ExclusiveLock(lp, 30)
            item._fs_metadata_lock.acquire(30)

    def _publish_item_metadata(self, item):
        if item._fs_item_id is None:
            self._add_item_internally(item, itemmeta=item._fs_metadata)
        else:
            assert item._fs_metadata_lock.isLocked()
            md = item._fs_metadata
            if md is None:
                # metadata unchanged
                pass
            elif not md:
                # metadata now empty, just rm the metadata file
                try:
                    os.unlink(self._make_path('meta', item._fs_item_id, 'item'))
                except OSError, err:
                    if err.errno != errno.ENOENT:
                        raise
                    # ignore, there might not have been metadata
            else:
                tmp = self._make_path('meta', item._fs_item_id, 'item.tmp')
                f = open(tmp, 'wb')
                pickle.dump(md, f, protocol=PICKLEPROTOCOL)
                f.close()

                filesys.rename(tmp, self._make_path('meta', item._fs_item_id, 'item'))
            item._fs_metadata_lock.release()
            del item._fs_metadata_lock

    def _read_revision_data(self, rev, chunksize):
        if rev._fs_file_data is None:
            if rev._fs_path_data is None:
                rev._fs_path_data = self._get_fs_path_data(rev)
            rev._fs_file_data = open(rev._fs_path_data, 'rb') # XXX keeps file open as long as rev exists
        return rev._fs_file_data.read(chunksize)

    def _write_revision_data(self, rev, data):
        rev._fs_file_data.write(data)

    def _get_item_metadata(self, item):
        if item._fs_item_id is not None:
            p = self._make_path('meta', item._fs_item_id, 'item')
            try:
                f = open(p, 'rb')
                metadata = pickle.load(f)
                f.close()
            except IOError, err:
                if err.errno != errno.ENOENT:
                    raise
                # no such file means no metadata was stored
                metadata = {}
            item._fs_metadata = metadata
        return item._fs_metadata

    def _get_revision_metadata(self, rev):
        if rev._fs_file_meta is None:
            rev._fs_file_meta = open(rev._fs_path_meta, 'rb')
        try:
            rev._fs_metadata = pickle.load(rev._fs_file_meta)
        except EOFError:
            rev._fs_metadata = {}
        rev._fs_file_meta.close()
        rev._fs_file_meta = None
        return rev._fs_metadata

    def _get_revision_timestamp(self, rev):
        if rev._fs_metadata is None:
            self._get_revision_metadata(rev)
        return rev._fs_metadata['__timestamp']

    def _get_revision_size(self, rev):
        if rev._fs_path_data is None:
            rev._fs_path_data = self._get_fs_path_data(rev)
        return os.stat(rev._fs_path_data).st_size

    def _seek_revision_data(self, rev, position, mode):
        if rev._fs_file_data is None:
            if rev._fs_path_data is None:
                rev._fs_path_data = self._get_fs_path_data(rev)
            rev._fs_file_data = open(rev._fs_path_data, 'rb') # XXX keeps file open as long as rev exists
        rev._fs_file_data.seek(position, mode)

    def _tell_revision_data(self, rev):
        if rev._fs_file_data is None:
            if rev._fs_path_data is None:
                rev._fs_path_data = self._get_fs_path_data(rev)
            rev._fs_file_data = open(rev._fs_path_data, 'rb') # XXX keeps file open as long as rev exists

        return rev._fs_file_data.tell()

