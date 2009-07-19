# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MercurialBackend

    This package contains code for MoinMoin storage backend using a
    Mercurial (hg) distributed version control system. This backend provides
    several advantages compared to MoinMoin's default filesystem backend:
    - revisioning and concurrency issues handled using Mercurial's internal
      mechanisms
    - cloning of the page database, allowing easy backup, synchronization and
      forking of wikis
    - offline, commandline edits with support of custom mercurial extensions
      for non-trivial tasks

    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""
import os
import time
import errno
import weakref
import tempfile
import StringIO
import itertools
import cPickle as pickle
from datetime import datetime

os.environ["HGENCODING"] = "utf-8" # must be set before importing mercurial
os.environ["HGMERGE"] = "internal:fail"

from mercurial import hg, ui, util, cmdutil, commands
from mercurial.node import short, nullid
from mercurial.revlog import LookupError

try:
    from mercurial.error import RepoError
except ImportError:
    from mercurial.repo import RepoError

try:
    import mercurial.match
except ImportError:
    pass

try:
    import cdb
except ImportError:
    from MoinMoin.support import pycdb as cdb

from MoinMoin.items import EDIT_LOG_USERID, EDIT_LOG_COMMENT
from MoinMoin.support.python_compatibility import hash_new
from MoinMoin.storage import Backend, Item, StoredRevision, NewRevision
from MoinMoin.storage.error import (BackendError, NoSuchItemError, NoSuchRevisionError,
                                   RevisionNumberMismatchError, ItemAlreadyExistsError,
                                   RevisionAlreadyExistsError)
WINDOW_SIZE = 256
PICKLE_ITEM_META = 1
META_PREFIX = '_meta_'

class MercurialBackend(Backend):
    """Implements backend storage using Mercurial VCS."""

    def __init__(self, path):
        """
        Create data directories and initialize mercurial repository.
        If direcrories or repository exists, reuse it. Create name-mapping.
        """
        self._path = os.path.abspath(path)
        self._rev_path = os.path.join(self._path, 'rev')
        self._meta_path = os.path.join(self._path, 'meta')
        self._meta_db = os.path.join(self._meta_path, 'name-mapping')
        try:
            self._ui = ui.ui(quiet=True, interactive=False)
        except:
            self._ui = ui.ui()
            self._ui.setconfig('ui', 'quiet', 'true')
            self._ui.setconfig('ui', 'interactive', 'false')
        for path in (self._path, self._rev_path, self._meta_path):
            try:
                os.mkdir(path)
            except OSError, err:
                if err == errno.EACCES:
                    raise BackendError("No permissions on path: %s" % self._path)
                elif not os.path.isdir(self._path):
                    raise BackendError("You passed invalid path: %s" % self._path)
        try:
            self._repo = hg.repository(self._ui, self._rev_path)
        except RepoError:
            self._repo = hg.repository(self._ui, self._rev_path, create=True)

        self._repo_lockref = None   # global repository lock reference
        self._item_lockrefs = {}    # item lock references
        self._create_cdb()

    def get_item(self, itemname):
        """
        Return an Item with given name.
        Raise NoSuchItemError if Item does not exist.
        """
        id = self._hash(itemname)
        try:
            self._repo.changectx('')[id]
        except LookupError:
            if not self._has_meta(id):
                raise NoSuchItemError('Item does not exist: %s' % itemname)
        item = Item(self, itemname)
        item._id = id
        return item

    def has_item(self, itemname):
        """Return True if Item with given name exists."""
        id = self._hash(itemname)
        return id in self._repo.changectx('') or self._has_meta(id)

    def create_item(self, itemname):
        """
        Create Item with given name.
        Raise ItemAlreadyExistsError if Item already exists.
        Return Item object.
        """
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Wrong Item name type: %s" % type(itemname))
        if self.has_item(itemname):
            raise ItemAlreadyExistsError("Item with that name already exists: %s" % itemname)
        item = Item(self, itemname)
        item._id = None
        return item

    def iteritems(self):
        """
        Return generator for iterating through collection of Items
        in repository.
        """
        def filter(id):
            return id.endswith(".rev") or self._has_meta(id)

        ctx = self._repo.changectx('')
        for id in itertools.ifilterfalse(filter, ctx):
            item = Item(self, self._name(id))
            item._id = id
            yield item
        c = cdb.init(self._meta_db)
        record = c.each()
        while record:
            item = Item(self, record[1])
            item._id = record[0]
            yield item
            record = c.each()

    def history(self, reverse=True):
        """
        Return generator for iterating in given direction over Item Revisions
        with timestamp order preserved.
        Yields MercurialStoredRevision objects.
        """
        for ctx in self._iter_changelog(reverse=reverse):
            meta = ctx.extra()
            revno = int(meta['_rev'])
            timestamp = ctx.date()[0]
            item = Item(self, meta['_name'])  # XXX: inaccurate after renames...
            rev = MercurialStoredRevision(item, revno, timestamp)
            rev._item_id = item._id = meta['_id']
            yield rev

    def _get_revision(self, item, revno):
        """
        Return given Revision of an Item. Raise NoSuchRevisionError
        if Revision does not exist.
        Return MercurialStoredRevision object.
        """
        revs = self._list_revisions(item)
        if revs and revno == -1:
            revno = max(revs)
        if revno not in revs:
            raise NoSuchRevisionError("Item Revision does not exist: %s" % revno)

        revision = MercurialStoredRevision(item, revno)
        revision._item_id = item._id
        revision._metadata = None
        revision._data = None
        return revision

    def _list_revisions(self, item):
        """Return a list of Item Revision numbers."""
        if not item._id:
            return []
        else:
            try:
                revfile = open(os.path.join(self._rev_path, "%s.rev" % item._id), 'r')
                revs = range(len(revfile.read().splitlines()))
                revfile.close()
                return revs
            except IOError:
                return []

    def _create_revision(self, item, revno):
        """Create new Item Revision. Return NewRevision object."""
        revs = self._list_revisions(item)
        if revno in revs:
                raise RevisionAlreadyExistsError("Item Revision already exists: %s" % revno)
        if revs and revno != revs[-1] + 1 or not revs and revno != 0:
                raise RevisionNumberMismatchError("Unable to create revision number %d. "
                    "New Revision number must be next to latest Revision number." % revno)
        rev = NewRevision(item, revno)
        rev._data = None
        rev._revno = revno
        rev._item_id = item._id
        rev._tmp_fpath = tempfile.mkstemp("-rev", "tmp-", dir=self._rev_path)[1]
        return rev

    def _rename_item(self, item, newname):
        """
        Rename given Item name to newname.
        Raise ItemAlreadyExistsError if destination exists.

        Also rename versioned cache file to follow new item name.
        """
        newid = self._hash(newname)
        try:
            lock = self._lock_repo()
            try:
                if self.has_item(newname):
                    raise ItemAlreadyExistsError("Destination item already exists: %s" % newname)

                self._repo.changectx('')[item._id]
                src = os.path.join(self._rev_path, item._id)
                dst = os.path.join(self._rev_path, newid)

                commands.rename(self._ui, self._repo, src, dst)
                commands.rename(self._ui, self._repo, "%s.rev" % src, "%s.rev" % dst)
                self._repo.commit(user='storage', text='(renamed %s to %s)' %
                                  (item.name.encode('utf-8'), newname.encode('utf-8')))
            finally:
                del lock
        except LookupError:
            pass
        if self._has_meta(item._id):
            lock = self._lock_item(item)
            try:
                src = os.path.join(self._meta_path, "%s.meta" % item._id)
                dst = os.path.join(self._meta_path, "%s.meta" % newid)
                try:
                    util.rename(src, dst)
                except OSError:
                    pass
                self._add_to_cdb(newid, newname, replace=item._id)
            finally:
                del lock
        item._id = newid

    def _commit_item(self, revision, second_parent=None):
        """
        Commit given Item Revision to repository.
        If Revision already exists, raise RevisionAlreadyExistsError.
        Update Item cache file.
        """
        item = revision.item
        lock = self._lock_repo()
        try:
            if not item._id:
                self._add_item(item)
            elif revision.revno in self._list_revisions(item):
                raise RevisionAlreadyExistsError("Item Revision already exists: %s" % revision.revno)

            util.rename(revision._tmp_fpath, os.path.join(self._rev_path, item._id))
            if revision.revno == 0:
                f = open(os.path.join(self._rev_path, "%s.rev" % item._id), 'w')
                f.close()
                self._repo.add([item._id, "%s.rev" % item._id])

            if revision.revno > 0:
                parents = [self._get_changectx(self._get_revision(item, revision.revno - 1)).node()]
                if second_parent:
                    parents.append(second_parent)
            else:
                parents = []
            meta = {"_rev": revision.revno,
                    "_name": item.name.encode("utf-8"),
                    "_id": item._id,
                    "_parents": " ".join(parents)}
            for k, v in revision.iteritems():
                meta["%s%s" % (META_PREFIX, k)] = pickle.dumps(v)
            if not revision.timestamp:
                revision.timestamp = long(time.time())
            date = datetime.fromtimestamp(revision.timestamp).isoformat(sep=' ')
            user = (revision.get(EDIT_LOG_USERID) or "anonymous").encode("utf-8")
            msg = (revision.get(EDIT_LOG_COMMENT) or "...").encode("utf-8")  # stable hg does not allow empty comments

            try:
                match = mercurial.match.exact(self._rev_path, '', [item._id])
                self._repo.commit(match=match, text=msg, user=user, date=date, extra=meta, force=True)
            except NameError:
                self._repo.commit(files=[item._id], text=msg, user=user, date=date, extra=meta, force=True)
            self._add_revision(item, revision)
        finally:
            del lock

    def _rollback_item(self, revision):
        pass

    def _change_item_metadata(self, item):
        """Start Item Metadata transaction."""
        if item._id:
            item._lock = self._lock_item(item)

    def _publish_item_metadata(self, item):
        """Dump Item Metadata to file and finish transaction."""
        def write_meta_item(meta_path, metadata):
            fd, fpath = tempfile.mkstemp("-meta", "tmp-", self._meta_path)
            f = os.fdopen(fd, 'wb')
            pickle.dump(metadata, f, protocol=PICKLE_ITEM_META)
            f.close()
            util.rename(fpath, meta_path)

        if item._id:
            if item._metadata is None:
                pass
            elif not item._metadata:
                try:
                    os.remove(os.path.join(self._meta_path, "%s.meta" % item._id))
                except OSError:
                    pass
            else:
                write_meta_item(os.path.join(self._meta_path, "%s.meta" % item._id), item._metadata)
            del item._lock
        else:
            self._add_item(item)
            self._add_to_cdb(item._id, item.name)
            if item._metadata:
                write_meta_item(os.path.join(self._meta_path, "%s.meta" % item._id), item._metadata)

    def _read_revision_data(self, revision, chunksize):
        """
        Read given amount of bytes of Revision data.
        By default, all data is read.

        If last revision, read from working copy.
        """
        if revision._data is None:
            if revision.revno == max(self._list_revisions(revision.item)): # latest revision, data in working copy
                # XXX: lock this file for writing on read
                #      question is, when will it be unlocked?
                revision._data = open(os.path.join(self._rev_path, revision._item_id), 'r')
                # XXX: keeps file open as long as revision exists
            else:
                revision._data = StringIO.StringIO(self._get_filectx(revision).data())
        return revision._data.read(chunksize)

    def _write_revision_data(self, revision, data):
        """Write data to the given Revision."""
        f = open(revision._tmp_fpath, 'a')   # we can open file in create_revision and pass it
        f.write(data)                        # here but this would lead to problems as in FSBackend
        f.close()                            # with too many opened files

    def _get_item_metadata(self, item):
        """Load Item Metadata from file. Return metadata dictionary."""
        if item._id:
            try:
                f = open(os.path.join(self._meta_path, "%s.meta" % item._id), "rb")
                item._metadata = pickle.load(f)
                f.close()
            except IOError:
                item._metadata = {}
        else:
            item._metadata = {}
        return item._metadata

    def _get_revision_metadata(self, revision):
        """Return given Revision Metadata dictionary."""
        extra = self._get_changectx(revision).extra()
        metadata = {}
        for k, v in extra.iteritems():
            if k.startswith(META_PREFIX):
                metadata[k[len(META_PREFIX):]] = pickle.loads(v)
        return metadata

    def _get_revision_timestamp(self, revision):
        """Return given Revision timestamp"""
        return self._get_filectx(revision).date()[0]

    def _get_revision_size(self, revision):
        """Return size of given Revision in bytes."""
        return self._get_filectx(revision).size()

    def _seek_revision_data(self, revision, position, mode):
        """Set the Revisions cursor on the Revisions data."""
        revision._data.seek(position, mode)

    def _hash(self, itemname):
        """Compute Item ID from given name."""
        return hash_new('md5', itemname.encode('utf-8')).hexdigest()

    def _name(self, itemid):
        """Resolve Item name by given ID."""
        try:
            fctx = self._repo.changectx('')[itemid].filectx(0)
            return fctx.changectx().extra()['_name']
        except LookupError:
            c = cdb.init(self._meta_db)
            return c.get(itemid)

    def _iter_changelog(self, reverse=True, id=None, start_rev=None):
        """
        Return generator fo iterating over repository changelog.
        Yields Changecontext object.
        """
        def split_windows(start, end, windowsize=WINDOW_SIZE):
            while start < end:
                yield start, min(windowsize, end-start)
                start += windowsize

        def wanted(changerev):
            ctx = self._repo.changectx(changerev)
            try:
                ctxid = ctx.extra()['_id']
                return not id or ctxid == id
            except KeyError:
                return False

        start, end = start_rev or -1, 0
        try:
            size = len(self._repo.changelog)
        except TypeError:
            size = self._repo.changelog.count()
        if not size:
            change_revs = []
        else:
            if not reverse:
                start, end = end, start
            change_revs = cmdutil.revrange(self._repo, ['%d:%d' % (start, end, )])

        for i, window in split_windows(0, len(change_revs)):
            revs = [changerev for changerev in change_revs[i:i+window] if wanted(changerev)]
            for revno in revs:
                yield self._repo.changectx(revno)

    def _get_filectx(self, revision):
        """
        Get Filecontext object corresponding to given Revision.
        Retrieve necessary information from cache file.
        """
        try:
            revfile = open(os.path.join(self._rev_path, "%s.rev" % revision._item_id), 'r')
            revs = revfile.read().splitlines()
            revs.sort()
            revno, node, id, filenode = revs[revision.revno].split()
            return self._repo.filectx(id, fileid=filenode)
        except IOError:
            return None

    def _get_changectx(self, revision):
        """
        Get Changecontext object corresponding to given Revision.
        Retrieve necessary information from cache file.
        """
        try:
            revfile = open(os.path.join(self._rev_path, "%s.rev" % revision._item_id), 'r')
            revs = revfile.read().splitlines()
            revs.sort()
            ctxrev = revs[revision.revno].split()[1]
            return self._repo.changectx(ctxrev)
        except IOError:
            return {}

    def _lock(self, lockpath, lockref):
        """Acquire weak reference to lock object."""
        if lockref and lockref():
            return lockref()
        lock = self._repo._lock(lockpath, wait=True, releasefn=None, acquirefn=None, desc='')
        lockref = weakref.ref(lock)
        return lock

    def _lock_repo(self):
        """Acquire global repository lock."""
        path = os.path.join(self._rev_path, "repo.lock")
        return self._lock(path, self._repo_lockref)

    def _lock_item(self, item):
        """Acquire Item Metadata lock."""
        path = os.path.join(self._rev_path, "%s.lock" % item._id)
        return self._lock(path, self._item_lockrefs.setdefault(item._id, None))

    def _add_item(self, item):
        """Assign ID to given Item. Raise ItemAlreadyExistsError if Item exists."""
        if self.has_item(item.name):
            raise ItemAlreadyExistsError("Destination item already exists: %s" % item.name)
        item._id = self._hash(item.name)

    def _add_revision(self, item, revision):
        """Add Item Revision to cache file to speed up further lookups."""
        ctx = self._repo.changectx('')
        revfile = open(os.path.join(self._rev_path, "%s.rev" % item._id), 'a')
        revfile.write("%d %s %s %s\n" % (revision.revno, short(ctx.node()),
                                         item._id, short(ctx.filectx(item._id).filenode()), ))
        revfile.close()
        try:
            match = mercurial.match.exact(self._rev_path, '', ['%s.rev' % item._id])
            self._repo.commit(match=match, text="(cache append)", user="storage")
        except NameError:
            self._repo.commit(files=['%s.rev' % item._id], text="(cache append)", user="storage")

    def _has_meta(self, itemid):
        """Return True if Item with given ID has Metadata. Otherwise return None."""
        c = cdb.init(self._meta_db)
        return c.get(itemid)

    def _add_to_cdb(self, itemid, itemname, replace=None):
        """Add Item Metadata file to name-mapping."""
        c = cdb.init(self._meta_db)
        maker = cdb.cdbmake("%s.ndb" % self._meta_db, "%s.tmp" % self._meta_db)
        record = c.each()
        while record:
            id, name = record
            if id == itemid:
                maker.finish()
                os.unlink(self._meta_db + '.ndb')
                raise ItemAlreadyExistsError("Destination item already exists: %s" % itemname)
            elif id == replace:
                pass
            else:
                maker.add(id, name)
            record = c.each()
        maker.add(itemid, itemname.encode('utf-8'))
        maker.finish()
        util.rename("%s.ndb" % self._meta_db, self._meta_db)

    def _create_cdb(self):
        """Create name-mapping file for storing Item Metadata files mappings."""
        if not os.path.exists(self._meta_db):
            maker = cdb.cdbmake(self._meta_db, "%s.tmp" % self._meta_db)
            maker.finish()

    #
    # extended API below - needed for drawing revision graph
    #

    def _get_revision_node(self, revision):
        """
        Return tuple consisting of (SHA1, short SHA1) changeset (node) IDs
        corresponding to given Revision.
        """
        try:
            revfile = open(os.path.join(self._rev_path, "%s.rev" % revision._item_id), 'r')
            revs = revfile.read().splitlines()
            revs.sort()
            node = revs[revision.revno].split()[1]
            return node, short(node)
        except IOError:
            return nullid, short(nullid)

    def _get_revision_parents(self, revision):
        """Return parent revision numbers of Revision."""
        def get_revision(node):
            return self._repo.changectx(node).extra()['_rev']

        parents = self._get_changectx(revision).extra()['_parents'].split()
        return [get_revision(node) for node in parents]


class MercurialStoredRevision(StoredRevision):

    def __init__(self, item, revno, timestamp=None, size=None):
        StoredRevision.__init__(self, item, revno, timestamp, size)

    def get_parents(self):
        return self._backend._get_revision_parents(self)

    def get_node(self):
        return self._backend._get_revision_node(self)

