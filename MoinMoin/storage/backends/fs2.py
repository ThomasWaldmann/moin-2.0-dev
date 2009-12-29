"""
    MoinMoin - FS2 backend

    Features:
    * store metadata and data separately
    * use uuids for item storage names

    @copyright: 2008 MoinMoin:JohannesBerg ("fs2" is originally based on "fs" from JB),
                2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import os, struct, tempfile, random, errno, shutil, time
from uuid import uuid4 as make_uuid

import cPickle as pickle

try:
    import cdb
except ImportError:
    from MoinMoin.support import pycdb as cdb

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

class FS2Backend(Backend):
    """
    FS2 backend
    """
    def __init__(self, path, nfs=False):
        """
        Initialise filesystem backend, creating initial files and
        some internal structures.

        @param path: storage path
        @param nfs: set to True if operating on NFS to avoid using O_APPEND
                    semantics which break on NFS
        """
        self._path = path
        self._name_db = self._make_path('name-mapping')
        self._history = self._make_path('history')

        # if no name-mapping db yet, create an empty one
        # (under lock, re-tests existence too)
        if not os.path.exists(self._name_db):
            self._do_locked(self._name_db + '.lock', self._create_new_cdb, None)

        # create meta data and revision content data storage dir
        try:
            os.makedirs(self._make_path('data'))
        except:
            pass
        try:
            os.makedirs(self._make_path('meta'))
        except:
            pass

        # on NFS, append semantics are broken, so decorate the _addhistory
        # method with a lock
        if nfs:
            _addhistory = self._addhistory
            def locked_addhistory(args):
                itemid, revid, ts = args
                _addhistory(itemid, revid, ts)
            historylock = self._history + '.lock'
            self._addhistory = lambda itemid, revid, ts: self._do_locked(historylock, locked_addhistory, (itemid, revid, ts))

    def _make_path(self, *args):
        return os.path.join(self._path, *args)

    def _get_fs_path_data(self, rev):
        hash_name = 'sha1' # XXX request.cfg.hash_algorithm, no request here
        if rev._fs_metadata is None:
            self._get_revision_metadata(rev)
        data_hash = rev._fs_metadata[hash_name]
        return self._make_path('data', data_hash)

    def _create_new_cdb(self, arg):
        """
        Create new name-mapping if it doesn't exist yet,
        call this under the name-mapping.lock.
        """
        if not os.path.exists(self._name_db):
            maker = cdb.cdbmake(self._name_db, self._name_db + '.tmp')
            maker.finish()

    def history(self, reverse=True):
        """
        History implementation reading the log file.
        """
        try:
            historyfile = open(self._history, 'rb')
        except IOError, err:
            if err.errno != errno.ENOENT:
                raise
            return
        offs = 0
        if reverse:
            historyfile.seek(0, 2)
            offs = historyfile.tell() - 1
            # shouldn't happen, but let's be sure we don't get a partial record
            offs -= offs % 16
        while offs >= 0:
            if reverse:
                # seek to current position
                historyfile.seek(offs)
                # decrease current position by 16 to get to previous item
                offs -= 16

            # read history item
            rec = historyfile.read(16)
            if len(rec) < 16:
                break

            itemid, revno, tstamp = struct.unpack('!32sLQ', rec)
            itemid = str(itemid)
            try:
                inamef = open(self._make_path('meta', itemid, 'name'), 'rb')
                iname = inamef.read().decode('utf-8')
                inamef.close()
                # try to open the revision file just in case somebody
                # removed it manually
                mp = self._make_path('meta', itemid, 'rev.%d' % revno)
                revf = open(mp)
                revf.close()
            except IOError, err:
                if err.errno != errno.ENOENT:
                    raise
                # oops, no such file, item/revision removed manually?
                continue
            item = Item(self, iname)
            item._fs_item_id = itemid
            rev = StoredRevision(item, revno, tstamp)
            rev._fs_path_meta = mp
            rev._fs_file_meta = None
            rev._fs_file_data = None
            rev._fs_metadata = None
            yield rev

    def _addhistory(self, itemid, revid, ts):
        """
        Add a history item with current timestamp and the given data.

        @param itemid: item's ID, must be a decimal integer in a string
        @param revid: revision ID, must be an integer
        @param ts: timestamp
        """
        historyfile = open(self._history, 'ab')
        historyfile.write(struct.pack('!32sLQ', itemid, revid, ts))
        historyfile.close()

    def _get_item_id(self, itemname):
        """
        Get ID of item (or None if no such item exists)

        @param itemname: name of item (unicode)
        """
        c = cdb.init(self._name_db)
        return c.get(itemname.encode('utf-8'))

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
        c = cdb.init(self._name_db)
        r = c.each()
        while r:
            item = Item(self, r[0].decode('utf-8'))
            item._fs_item_id = r[1]
            yield item
            r = c.each()

    def _get_revision(self, item, revno):
        item_id = item._fs_item_id

        if revno == -1:
            revs = item.list_revisions()
            if not revs:
                raise NoSuchRevisionError("Item has no revisions.")
            revno = max(revs)

        mp = self._make_path('meta', item_id, 'rev.%d' % revno)
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
        prefix = 'rev.'
        ret = [int(i[len(prefix):]) for i in l if i.startswith(prefix)]
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
        fd, rev._fs_path_meta = tempfile.mkstemp('-meta', 'tmp-', self._path)
        rev._fs_file_meta = os.fdopen(fd, 'wb') # XXX keeps file open as long a rev exists
        fd, rev._fs_path_data = tempfile.mkstemp('-data', 'tmp-', self._path)
        rev._fs_file_data = os.fdopen(fd, 'wb') # XXX keeps file open as long a rev exists
        return rev

    def _destroy_revision(self, revision):
        if revision._fs_file_meta is not None:
            revision._fs_file_meta.close()
        if revision._fs_file_data is not None:
            revision._fs_file_data.close()
        try:
            os.unlink(revision._fs_path_meta)
            os.unlink(revision._fs_path_data)
        except OSError, err:
            if err.errno != errno.ENOENT:
                raise CouldNotDestroyError("Could not destroy revision #%d of item '%r' [errno: %d]" % (
                    revision.revno, revision.item.name, err.errno))
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
        nn = newname.encode('utf-8')
        npath = self._make_path('meta', item._fs_item_id, 'name')

        c = cdb.init(self._name_db)
        maker = cdb.cdbmake(self._name_db + '.ndb', self._name_db + '.tmp')
        r = c.each()
        while r:
            i, v = r
            if i == nn:
                raise ItemAlreadyExistsError("Target item '%r' already exists!" % newname)
            elif v == item._fs_item_id:
                maker.add(nn, v)
            else:
                maker.add(i, v)
            r = c.each()
        maker.finish()

        filesys.rename(self._name_db + '.ndb', self._name_db)
        nf = open(npath, mode='wb')
        nf.write(nn)
        nf.close()

    def _rename_item(self, item, newname):
        self._do_locked(self._make_path('name-mapping.lock'),
                        self._rename_item_locked, (item, newname))

    def _add_item_internally_locked(self, arg):
        """
        See _add_item_internally, this is just internal for locked operation.
        """
        item, revmeta, revdata, revdata_target, itemmeta = arg
        itemid = make_uuid().hex

        nn = item.name.encode('utf-8')

        c = cdb.init(self._name_db)
        maker = cdb.cdbmake(self._name_db + '.ndb', self._name_db + '.tmp')
        r = c.each()
        while r:
            i, v = r
            if i == nn:
                # Oops. This item already exists! Clean up and error out.
                maker.finish()
                os.unlink(self._name_db + '.ndb')
                if newrev is not None:
                    os.unlink(newrev)
                raise ItemAlreadyExistsError("Item '%r' already exists!" % item.name)
            else:
                maker.add(i, v)
            r = c.each()
        maker.add(nn, itemid)
        maker.finish()

        os.mkdir(self._make_path('meta', itemid))

        if revdata is not None:
            filesys.rename(revdata, revdata_target)

        if revmeta is not None:
            rp = self._make_path('meta', itemid, 'rev.%s' % 0)
            filesys.rename(revmeta, rp)

        if itemmeta:
            # only write item level metadata file if we have any
            meta = self._make_path('meta', itemid, 'meta')
            f = open(meta, 'wb')
            pickle.dump(itemmeta, f, protocol=PICKLEPROTOCOL)
            f.close()

        # write 'name' file of item
        npath = self._make_path('meta', itemid, 'name')
        nf = open(npath, mode='wb')
        nf.write(nn)
        nf.close()

        # make item retrievable (by putting the name-mapping in place)
        filesys.rename(self._name_db + '.ndb', self._name_db)

        item._fs_item_id = itemid

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

        hash_name = 'sha1' # XXX request.cfg.hash_algorithm, no request here
        data_hash = metadata[hash_name]

        pd = self._make_path('data', data_hash)
        if item._fs_item_id is None:
            self._add_item_internally(item, revmeta=rev._fs_path_meta, revdata=rev._fs_path_data, revdata_target=pd)
        else:
            try:
                filesys.rename_no_overwrite(rev._fs_path_data, pd, delete_old=True)
            except OSError, err:
                if err.errno != errno.EEXIST:
                    raise

            pm = self._make_path('meta', item._fs_item_id, 'rev.%d' % rev.revno)
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
        c = cdb.init(self._name_db)
        maker = cdb.cdbmake(self._name_db + '.ndb', self._name_db + '.tmp')
        r = c.each()
        while r:
            i, v = r
            if v != item._fs_item_id:
                maker.add(i, v)
            r = c.each()
        maker.finish()

        filesys.rename(self._name_db + '.ndb', self._name_db)
        path = self._make_path('meta', item._fs_item_id)
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
            lp = self._make_path('meta', item._fs_item_id, 'meta.lock')
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
                    os.unlink(self._make_path('meta', item._fs_item_id, 'meta'))
                except OSError, err:
                    if err.errno != errno.ENOENT:
                        raise
                    # ignore, there might not have been metadata
            else:
                tmp = self._make_path('meta', item._fs_item_id, 'meta.tmp')
                f = open(tmp, 'wb')
                pickle.dump(md, f, protocol=PICKLEPROTOCOL)
                f.close()

                filesys.rename(tmp, self._make_path('meta', item._fs_item_id, 'meta'))
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
            p = self._make_path('meta', item._fs_item_id, 'meta')
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

    def _tell_revision_data(self, revision):
        if rev._fs_file_data is None:
            if rev._fs_path_data is None:
                rev._fs_path_data = self._get_fs_path_data(rev)
            rev._fs_file_data = open(rev._fs_path_data, 'rb') # XXX keeps file open as long as rev exists

        return revision._fs_file_data.tell()

