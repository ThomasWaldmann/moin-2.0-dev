"""
    MoinMoin - FS backend

    @copyright: 2008 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

import os, struct, tempfile, random, errno, shutil, time
import cPickle as pickle

try:
    import cdb
except ImportError:
    from MoinMoin.support import pycdb as cdb

from MoinMoin.util.lock import ExclusiveLock
from MoinMoin.storage import Backend, Item, StoredRevision, NewRevision
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, \
                                   ItemAlreadyExistsError, \
                                   RevisionAlreadyExistsError, RevisionNumberMismatchError

PICKLEPROTOCOL = 1

class FSBackend(Backend):
    """
    Basic filesystem backend, described at
    http://moinmo.in/JohannesBerg/FilesystemStorage
    """
    def __init__(self, path, nfs=False, reserved_metadata_space=508):
        """
        Initialise filesystem backend, creating initial files and
        some internal structures.

        @param path: storage path
        @param nfs: set to True if operating on NFS to avoid using O_APPEND
                    semantics which break on NFS
        @param reserved_metadata_space: space reserved for revision metadata
                                        initially, increase if you expect a
                                        lot of very long ACL strings or so.
                                        We need four additional bookkeeping bytes
                                        so the default of 508 means data starts
                                        at byte 512 in the file by default.
        """
        self._path = path
        self._name_db = os.path.join(path, 'name-mapping')
        self._news = os.path.join(path, 'news')
        self._itemspace = 128
        self._revmeta_reserved_space = reserved_metadata_space

        # if no name-mapping db yet, create an empty one
        # (under lock, re-tests existence too)
        if not os.path.exists(self._name_db):
            self._do_locked(self._name_db + '.lock', self._create_new_cdb, None)

        # on NFS, append semantics are broken, so decorate the _addnews
        # method with a lock
        if nfs:
            _addnews = self._addnews
            def locked_addnews(args):
                itemid, revid = args
                _addnews(itemid, revid)
            newslock = self._news + '.lock'
            self._addnews = lambda itemid, revid: self._do_locked(newslock, locked_addnews, (itemid, revid))

    def _create_new_cdb(self, arg):
        """
        Create new name-mapping if it doesn't exist yet,
        call this under the name-mapping.lock.
        """
        if not os.path.exists(self._name_db):
            maker = cdb.cdbmake(self._name_db, self._name_db + '.tmp')
            maker.finish()

    def news(self, timestamp=0):
        """
        News implementation reading the log file.
        """
        try:
            newsfile = open(self._news, 'rb')
        except IOError, err:
            if err.errno != errno.ENOENT:
                raise
            return
        newsfile.seek(0, 2)
        offs = newsfile.tell() - 1
        # shouldn't happen, but let's be sure we don't get a partial record
        offs -= offs % 16
        tstamp = None
        while tstamp is None or tstamp >= timestamp and offs >= 0:
            # seek to current position
            newsfile.seek(offs)
            # read news item
            rec = newsfile.read(16)
            # decrease current position by 16 to get to previous item
            offs -= 16
            itemid, revno, tstamp = struct.unpack('!LLQ', rec)
            itemid = str(itemid)
            try:
                inamef = open(os.path.join(self._path, itemid, 'name'), 'rb')
                iname = inamef.read().decode('utf-8')
                inamef.close()
                # try to open the revision file just in case somebody
                # removed it manually
                revf = open(os.path.join(self._path, itemid, 'rev.%d' % revno))
                revf.close()
            except IOError, err:
                if err.errno != errno.ENOENT:
                    raise
                # oops, no such file, item/revision removed manually?
                continue
            item = Item(self, iname)
            item._fs_item_id = itemid
            yield (Revision(item, revno), tstamp)

    def _addnews(self, itemid, revid):
        """
        Add a news item with current timestamp and the given data.

        @param itemid: item's ID, must be a decimal integer in a string
        @param revid: revision ID, must be an integer
        """
        itemid = long(itemid)
        newsfile = open(self._news, 'ab')
        newsfile.write(struct.pack('!LLQ', itemid, revid, long(time.time())))
        newsfile.close()

    def search_item(self, searchterm):
        # Very simple implementation because we have no indexing
        # or anything like that, and the name matches are already
        # quite optimised by default.
        for item in self.iteritems():
            searchterm.prepare()
            if searchterm.evaluate(item):
                yield item

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
            raise NoSuchItemError("No such item, %r" % (itemname))

        item = Item(self, itemname)
        item._fs_item_id = item_id
        item._fs_metadata = None

        return item

    def has_item(self, itemname):
        return self._get_item_id(itemname) is not None

    def create_item(self, itemname):
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Itemnames must have string type, not %s" % (type(itemname)))

        elif self.has_item(itemname):
            raise ItemAlreadyExistsError("An Item with the name %r already exists!" % (itemname))

        item = Item(self, itemname)
        item._fs_item_id = None
        item._fs_metadata = {}

        return item

    def iteritems(self):
        c = cdb.init(self._name_db)
        r = c.each()
        while r:
            item = Item(self, r[0])
            item._fs_item_id = r[1]
            yield item
            r = c.each()

    def _get_revision(self, item, revno):
        item_id = item._fs_item_id

        if revno == -1:
            revno = max(item.list_revisions())

        revpath = os.path.join(self._path, item_id, 'rev.%d' % revno)
        if not os.path.exists(revpath):
            raise NoSuchRevisionError("No Revision #%d on Item %s" % (revno, item.name))

        rev = StoredRevision(item, revno)
        rev._fs_revpath = revpath
        rev._fs_file = None

        return rev

    def _list_revisions(self, item):
        p = os.path.join(self._path, item._fs_item_id)
        l = os.listdir(p)
        ret = [int(i[4:]) for i in l if i.startswith('rev.')]
        ret.sort()
        return ret

    def _create_revision(self, item, revno):
        if item._fs_item_id is None:
            revs = []
        else:
            revs = self._list_revisions(item)
        last_rev = max(-1, -1, *revs)

        if revno in revs:
            raise RevisionAlreadyExistsError("A Revision with the number %d already exists on the item %r" % (revno, item.name))
        elif revno != last_rev + 1:
            raise RevisionNumberMismatchError("The latest revision is %d, thus you cannot create revision number %d. \
                                               The revision number must be latest_revision + 1." % (last_rev, revno))

        rev = NewRevision(item, revno)
        rev._revno = revno
        fd, rev._fs_revpath = tempfile.mkstemp('-rev', 'tmp-', self._path)
        rev._fs_file = os.fdopen(fd, 'wb')
        f = rev._fs_file
        f.write(struct.pack('!I', self._revmeta_reserved_space + 4))
        f.seek(self._revmeta_reserved_space + 4)

        return rev

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
        npath = os.path.join(self._path, item._fs_item_id, 'name')

        c = cdb.init(self._name_db)
        maker = cdb.cdbmake(self._name_db + '.ndb', self._name_db + '.tmp')
        r = c.each()
        while r:
            i, v = r
            if i == nn:
                raise ItemAlreadyExistsError("new name already exists!")
            elif v == item._fs_item_id:
                maker.add(nn, v)
            else:
                maker.add(i, v)
            r = c.each()
        maker.finish()
        # XXXX: doesn't work on windows
        os.rename(self._name_db + '.ndb', self._name_db)
        nf = open(npath, mode='wb')
        nf.write(nn)
        nf.close()

    def _rename_item(self, item, newname):
        if not isinstance(newname, (str, unicode)):
            raise TypeError("Itemnames must have string type, not %s" % (type(newname)))

        self._do_locked(os.path.join(self._path, 'name-mapping.lock'),
                        self._rename_item_locked, (item, newname))

        # XXXX: Item.rename could very well do this
        item._name = newname

    def _add_item_internally_locked(self, arg):
        """
        See _add_item_internally, this is just internal for locked operation.
        """
        item, newrev, metadata = arg
        cntr = 0
        done = False
        while not done:
            itemid = '%d' % random.randint(0, self._itemspace - 1)
            ipath = os.path.join(self._path, itemid)
            cntr += 1
            try:
                os.mkdir(ipath)
                done = True
            except OSError, err:
                if err.errno != errno.EEXIST:
                    raise
            if cntr > 2 and not done and self._itemspace <= 2**31:
                self._itemspace *= 2
                cntr = 0
            elif cntr > 20:
                # XXXX: UnexpectedBackendError() that propagates to user?
                raise Exception('item space full')

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
                os.rmdir(ipath)
                if newrev is not None:
                    os.unlink(newrev)
                raise ItemAlreadyExistsError("new name already exists!")
            else:
                maker.add(i, v)
            r = c.each()
        maker.add(nn, itemid)
        maker.finish()

        if newrev is not None:
            rp = os.path.join(self._path, itemid, 'rev.0')
            os.rename(newrev, rp)

        if metadata:
            # only write metadata file if we have any
            meta = os.path.join(self._path, itemid, 'meta')
            f = open(meta, 'wb')
            pickle.dump(metadata, f, protocol=PICKLEPROTOCOL)
            f.close()

        # write 'name' file of item
        npath = os.path.join(ipath, 'name')
        nf = open(npath, mode='wb')
        nf.write(nn)
        nf.close()

        # make item retrievable (by putting the name-mapping in place)
        # XXXX: doesn't work on windows
        os.rename(self._name_db + '.ndb', self._name_db)

        item._fs_item_id = itemid

    def _add_item_internally(self, item, newrev=None, metadata=None):
        """
        This method adds a new item. It locks the name-mapping database to
        ensure putting the item into place and adding it to the name-mapping
        db is atomic.

        If the newrev or metadata arguments are given, then it also adds the
        revision or metadata to the item before making it discoverable.

        If the item's name already exists, it doesn't do anything but raise
        a ItemAlreadyExistsError; if the newrev was given the file is unlinked.

        @param newrev: new revision's temporary file path
        @param metadata: item metadata dict
        """
        self._do_locked(os.path.join(self._path, 'name-mapping.lock'),
                        self._add_item_internally_locked, (item, newrev, metadata))

    def _commit_item(self, item):
        # XXXX: Item.commit could pass this in
        rev = item._uncommitted_revision

        metadata = {}
        metadata.update(rev)
        md = pickle.dumps(metadata, protocol=PICKLEPROTOCOL)

        hasdata = rev._fs_file.tell() > self._revmeta_reserved_space + 4

        if hasdata and len(md) > self._revmeta_reserved_space:
            oldrp = rev._fs_revpath
            oldf = rev._fs_file
            fd, rev._fs_revpath = tempfile.mkstemp('-rev', 'tmp-', self._path)
            rev._fs_file = os.fdopen(fd, 'wb')
            f = rev._fs_file
            f.write(struct.pack('!I', len(md) + 4))
            # write metadata
            f.write(md)
            # copy already written data
            oldf.seek(self._revmeta_reserved_space + 4)
            shutil.copyfileobj(oldf, f)
            oldf.close()
            os.unlink(oldrp)
        else:
            if not hasdata:
                rev._fs_file.seek(0)
                rev._fs_file.write(struct.pack('!L', len(md) + 4))
            else:
                rev._fs_file.seek(4)
            rev._fs_file.write(md)
            rev._fs_file.close()

        if item._fs_item_id is None:
            self._add_item_internally(item, newrev=rev._fs_revpath)
        else:
            rp = os.path.join(self._path, item._fs_item_id, 'rev.%d' % rev.revno)

            try:
                os.rename(rev._fs_revpath, rp)
            except OSError, err:
                os.unlink(rev._fs_revpath)
                if err.errno != errno.EEXIST:
                    raise
                raise RevisionAlreadyExistsError()

        self._addnews(item._fs_item_id, rev.revno)
        # XXXX: Item.commit could very well do this.
        item._uncommitted_revision = None

    def _rollback_item(self, item):
        # XXXX: Item.commit could pass this in.
        rev = item._uncommitted_revision

        rev._fs_file.close()
        os.unlink(rev._fs_revpath)

        # XXXX: Item.commit could very well do this.
        item._uncommitted_revision = None

    def _change_item_metadata(self, item):
        if not item._fs_item_id is None:
            lp = os.path.join(self._path, item._fs_item_id, 'meta.lock')
            item._fs_metadata_lock = ExclusiveLock(lp, 30)
            item._fs_metadata_lock.acquire(30)

    def _publish_item_metadata(self, item):
        if item._fs_item_id is None:
            self._add_item_internally(item, metadata=item._fs_metadata)
        else:
            assert item._fs_metadata_lock.isLocked()
            md = item._fs_metadata
            if md is None:
                # metadata unchanged
                pass
            elif not md:
                # metadata now empty, just rm the metadata file
                # XXXX: might not work on windows
                try:
                    os.unlink(os.path.join(self._path, item._fs_item_id, 'meta'))
                except IOError, err:
                    if err.errno != errno.ENOENT:
                        raise
                    # ignore, there might not have been metadata
            else:
                tmp = os.path.join(self._path, item._fs_item_id, 'meta.tmp')
                f = open(tmp, 'wb')
                pickle.dump(md, f, protocol=PICKLEPROTOCOL)
                f.close()
                # XXXX: doesn't work on windows
                os.rename(tmp, os.path.join(self._path, item._fs_item_id, 'meta'))
            item._fs_metadata_lock.release()
            del item._fs_metadata_lock

    def _read_revision_data(self, rev, chunksize):
        if rev._fs_file is None:
            f = open(rev._fs_revpath, 'rb')
            datastart = f.read(4)
            datastart = struct.unpack('!L', datastart)[0]
            f.seek(datastart)
            rev._fs_file = f
            rev._datastart = datastart

        if chunksize < 0:
            return rev._fs_file.read()
        return rev._fs_file.read(chunksize)

    def _write_revision_data(self, rev, data):
        rev._fs_file.write(data)

    def _get_item_metadata(self, item):
        if item._fs_item_id is not None:
            p = os.path.join(self._path, item._fs_item_id, 'meta')
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
        if rev._fs_file is None:
            f = open(rev._fs_revpath, 'rb')
            datastart = f.read(4)
            datastart = struct.unpack('!L', datastart)[0]
            pos = datastart
            rev._fs_file = f
            rev._datastart = datastart
        else:
            f = rev._fs_file
            pos = f.tell()
            f.seek(4)
        ret = pickle.load(f)
        f.seek(pos)
        return ret

    def _seek_revision_data(self, rev, position, mode):
        if mode == 2:
            rev._fs_file.seek(position, mode)
        else:
            rev._fs_file.seek(position + rev._datastart, mode)
