# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Mercurial backend for storage layer

    This package contains code for MoinMoin storage backend using a
    Mercurial (hg) distributed version control system. This backend provides
    several advantages compared to MoinMoin's default filesystem backend:
    - revisioning and concurrency issues handled using Mercurial's internal
      mechanisms
    - cloning of the page database, allowing easy backup, synchronization and
      forking of wikis

    As this code is based on API design newly developed for MoinMoin 1.8 storage
    branch, it helps assert consistency of design and shows how to use it in
    proper way.

    IMPORTANT:
    This backend is intended to run on revision 077f1e637cd8 of http://selenic.com/repo/hg
    mercurial development branch, along with patch for empty commits apllied:
    MoinMoin/storage/backends/research/repo_force_changes.diff

    QUICK INSTALLATION INSTRUCTIONS:
    hg clone -r 077f1e637cd8 http://selenic.com/repo/hg local_hg
    cd local_hg; make local
    patch -p1 < repo_force_changes.diff
    export PYTHONPATH=local_hg

    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""

from mercurial import hg, ui, context, util, commands
from mercurial.node import nullid, nullrev, short
from mercurial.repo import RepoError
from mercurial.revlog import LookupError
from mercurial.cmdutil import revrange
import cPickle as pickle
import StringIO
import tempfile
import weakref
import struct
import shutil
import random
import errno
import time
import md5
import os

from MoinMoin.Page import EDIT_LOG_USERID, EDIT_LOG_COMMENT
from MoinMoin.storage import Backend, Item, StoredRevision, NewRevision
from MoinMoin.storage.error import BackendError, NoSuchItemError, NoSuchRevisionError,\
                                   RevisionNumberMismatchError, ItemAlreadyExistsError,\
                                   RevisionAlreadyExistsError
PICKLE_ITEM_META = 1
PICKLE_REV_META = 0
RAND_MAX = 1024


class MercurialBackend(Backend):
    """Implements backend storage using mercurial version control system."""

    def __init__(self, path):
        """
        Create data directories and initialize mercurial repository.
        If direcrories or repository exists, reuse it.
        """
        self._path = os.path.abspath(path)
        self._rev_path = os.path.join(self._path, 'rev')
        self._meta_path = os.path.join(self._path, 'meta')
        self._cache_path = os.path.join(self._path, 'cache')
        self._name_db = os.path.join(self._rev_path, '.name-mapping')
        try:
            os.mkdir(self._path)
        except OSError, err:
            if err.errno == errno.EACCES:
                raise BackendError("No permisions on path: %s" % self._path)
            elif not os.path.isdir(self._path):
                raise BackendError("Invalid path: %s" % self._path)
        for path in (self._meta_path, self._rev_path, self._cache_path):
            try:
                os.mkdir(path)
            except OSError:
                pass

        self._ui = ui.ui(interactive=False, quiet=True)
        os.environ["HGMERGE"] = "internal:fail"
        os.environ["HGENCODING"] = "utf-8"
        try:
            self._repo = hg.repository(self._ui, self._rev_path, create=True)
        except RepoError:
            self._repo = hg.repository(self._ui, self._rev_path)
        self._repo._forcedchanges = True
        self._set_config()

        self._item_metadata_lockref = {}    # item lock references
        self._name_lockref = None           # global namedb lock reference
        self._lockref = None                # global repository lock reference

        if not os.path.exists(self._name_db):
            self._init_namedb()

    def has_item(self, itemname):
        """Return True if Item with given name exists."""
        return self._get_item_id(itemname) is not None

    def create_item(self, itemname):
        """
        Create Item with given name.
        Raise ItemAlreadyExistsError if Item already exists.
        Return Item object.
        """
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Wrong Item name type: %s" % (type(itemname)))
        if self.has_item(itemname):
            raise ItemAlreadyExistsError("Item with that name already exists: %s" % itemname)
        item = Item(self, itemname)
        item._id = None
        return item

    def get_item(self, itemname):
        """
        Return an Item with given name.
        Raise NoSuchItemError if Item does not exist.
        """
        item_id = self._get_item_id(itemname)
        if not item_id:
            raise NoSuchItemError('Item does not exist: %s' % itemname)
        item = Item(self, itemname)
        item._id = item_id
        return item

    def iteritems(self):
        """
        Return generator for iterating through collection of Items
        in repository.
        """
        name2id, id2name = self._read_name_db()
        for id, name in id2name.iteritems():
            item = Item(self, name)
            item._id = id
            yield item

    def history(self, reverse=True):
        """
        Return generator for iterating in given direction over Item Revisions
        with timestamp order preserved.
        Yields MercurialStoredRevision objects.
        """
        for changeset, ctxrev in self._iterate_changesets(reverse=reverse):
            item_id = changeset[3][0]
            revno = pickle.loads(changeset[5]["__revision"])
            tstamp = pickle.loads(changeset[5]["__timestamp"])
            name = self._get_item_name(item_id)
            item = Item(self, name)
            rev = MercurialStoredRevision(item, revno, tstamp)
            rev._item_id = item._id = item_id
            yield rev

    def _create_revision(self, item, revno):
        """Create new Item Revision. Return NewRevision object."""
        revs = self._list_revisions(item)
        if revs:
            if revno in revs:
                raise RevisionAlreadyExistsError("Item Revision already exists: %s" % revno)
            if revno != revs[-1] + 1:
                raise RevisionNumberMismatchError("Unable to create revision number %d. \
                    New Revision number must be next to latest Revision number." % revno)
        rev = NewRevision(item, revno)
        rev._data = StringIO.StringIO()
        rev._revno = revno
        rev._item_id = item._id
        return rev

    def _get_revision(self, item, revno):
        """
        Return given Revision of an Item. Raise NoSuchRevisionError
        if Revision does not exist.
        Return MercurialStoredRevision object.
        """
        has, last, changectx = self._has_revision(item, revno)
        if not has:
            raise NoSuchRevisionError("Item Revision does not exist: %s" % revno)
        if revno == -1:
            revno = last
        revision = MercurialStoredRevision(item, revno)
        revision._data = StringIO.StringIO(changectx.filectx(item._id).data())
        revision._item_id = item._id
        revision._metadata = None
        return revision

    def _get_revision_size(self, rev):
        """Return size of given Revision in bytes."""
        ftx = self._repo['tip'][rev._item_id].filectx(rev.revno)
        return ftx.size()

    def _get_revision_metadata(self, rev):
        """Return given Revision Metadata dictionary."""
        changectx = self._has_revision(rev.item, rev.revno)[2]
        metadata = {}
        for k, v in changectx.extra().iteritems():
            if k.startswith('moin_'):
                metadata[k.lstrip('moin_')] = pickle.loads(v)
            elif k.startswith('__'):
                metadata[k] = pickle.loads(v)
        return metadata

    def _get_revision_timestamp(self, rev):
        """Return given Revision timestamp"""
        if rev._metadata is None:
            return self._get_revision_metadata(rev)['__timestamp']
        return rev._metadata['__timestamp']

    def _write_revision_data(self, revision, data):
        """Write data to the given Revision."""
        revision._data.write(data)

    def _read_revision_data(self, revision, chunksize):
        """
        Read given amount of bytes of Revision data.
        By default, all data is read.
        """
        return revision._data.read(chunksize)

    def _seek_revision_data(self, revision, position, mode):
        """Set the Revisions cursor on the Revisions data."""
        revision._data.seek(position, mode)

    def _list_revisions(self, item):
        """
        Return a list of Item Revision numbers.
        """
        if not item._id:
            return []
        else:
            try:
                f = open(self._cachepath(item._id + ".cache"))
                revs = [int(revpair.split(':')[0]) for revpair in f.read().split(',') if revpair]
                f.close()
                revs.sort()
                return revs
            except EOFError:
                return []
            except IOError:
                revs = []
                for changeset in self._iterate_changesets(item_id=item._id):
                    revno = pickle.loads(changeset[5]['__revision'])
                    revs.append(revno)
                    if revno == 0:  # iterating from top
                        revs.reverse()
                        return revs
                return []

    def _rename_item(self, item, newname):
        """
        Rename given Item name to newname.
        Raise ItemAlreadyExistsError if destination exists.
        """
        lock = self._repolock()
        try:
            if self.has_item(newname):
                raise ItemAlreadyExistsError("Destination item already exists: %s" % newname)
            namemapping_list = []
            name2id, id2name = self._read_name_db()
            for id, name in id2name.iteritems():
                if id == item._id:
                    namemapping_list.append("%s %s" % (id, newname.encode('utf-8'), ))
                else:
                    namemapping_list.append("%s %s" % (id, name.encode('utf-8'), ))
            fd, fname = tempfile.mkstemp("-tmp", "namedb-", self._path)
            os.write(fd, "\n".join(namemapping_list) + "\n")
            os.close(fd)
            name_lock = self._namelock()
            try:
                util.rename(fname, self._name_db)
            finally:
                del name_lock
        finally:
            del lock

    def _get_item_metadata(self, item):
        """Load Item Metadata from file. Return metadata dictionary."""
        if item._id:
            try:
                f = open(self._metapath(item._id + ".meta"), "rb")
                item._metadata = pickle.load(f)
                f.close()
            except IOError, err:
                if err.errno != errno.ENOENT:
                    raise
                item._metadata = {}
        else:
            item._metadata = {}
        return item._metadata

    def _change_item_metadata(self, item):
        """Start Item Metadata transaction."""
        if item._id:
            item._lock = self._itemlock(item)

    def _publish_item_metadata(self, item):
        """Dump Item Metadata to file and finish transaction."""
        def write_meta_item(item_path, metadata):
            tmp_fd, tmp_fpath = tempfile.mkstemp("-meta", "tmp-", self._meta_path)
            f = os.fdopen(tmp_fd, 'wb')
            pickle.dump(item._metadata, f, protocol=PICKLE_ITEM_META)
            f.close()
            util.rename(tmp_fpath, item_path)

        if item._id:
            if item._metadata is None:
                pass
            elif not item._metadata:
                try:
                    os.remove(self._metapath("%s.meta" % item._id))
                except OSError:
                    pass
            else:
                write_meta_item(self._metapath("%s.meta" % item._id), item._metadata)
            del item._lock
        else:
            self._add_item(item)
            if item._metadata:
                write_meta_item(self._metapath("%s.meta" % item._id), item._metadata)


    def _commit_item(self, rev):
        """
        Commit given Item Revision to repository.
        If Revision already exists, raise RevisionAlreadyExistsError.
        Update Item cache file.
        """
        def getfilectx(repo, memctx, path):
            return context.memfilectx(path, data, False, False, False)

        if rev.timestamp is None:
            rev.timestamp = long(time.time())
        msg = rev.get(EDIT_LOG_COMMENT, "").encode("utf-8")
        user = rev.get(EDIT_LOG_USERID, "anonymous")
        data = rev._data.getvalue()

        meta = {'__timestamp': pickle.dumps(rev.timestamp, PICKLE_REV_META),
                '__revision': pickle.dumps(rev.revno, PICKLE_REV_META), }
        for k, v in rev.iteritems():
            meta["moin_%s" % k] = pickle.dumps(v, PICKLE_REV_META)

        lock = self._repolock()
        try:
            item = rev.item
            p1, p2 = self._repo['tip'].node(), nullid
            if not item._id:
                self._add_item(item)
            else:
                if rev.revno in self._list_revisions(item):
                    raise RevisionAlreadyExistsError("Item Revision already exists: %s" % rev.revno)

            ctx = context.memctx(self._repo, (p1, p2), msg, [], getfilectx, user, extra=meta)
            if rev.revno == 0:
                ctx._status[1] = [item._id]
            else:
                ctx._status[0] = [item._id]
            self._repo.commitctx(ctx)
            commands.update(self._ui, self._repo)

            tiprevno = self._repo['tip'].rev()
            f = open(self._cachepath("%s.cache" % item._id), 'a')
            if not f.tell() and not rev.revno == 0:
                self._recreate_cache(item, f)
            f.write("%d:%d," % (rev.revno, tiprevno, ))
            f.close()
        finally:
            del lock

    def _rollback_item(self, rev):
        pass  # generic rollback is sufficent

    def _has_revision(self, item, revno):
        """
        Check whether Item has given Revision.
        Return (True, last Revision number, repository changelog revision) tuple
        if found.
        Return (False, -1, None) tuple if Item does not have given Revision.
        """
        if not item._id:
            return False, -1, None
        try:
            f = open(self._cachepath(item._id + ".cache"))
            revpairs = [revpair for revpair in f.read().split(',') if revpair]
            f.close()
            if revpairs and revno == -1:
                revno = int(max(revpairs)[0])
            for rev, ctxrev in [pair.split(':') for pair in revpairs]:
                if int(rev) == revno:
                    return True, int(max(revpairs)[0]), self._repo[ctxrev]
            return False, -1, -1
        except IOError:
            for changeset, ctxrev in self._iterate_changesets(item_id=item._id):
                last_revno = pickle.loads(changeset[5]['__revision'])
                return revno <= last_revno, last_revno, self._repo[revno]
            return False, -1, None

    def _iterate_changesets(self, reverse=True, item_id=None):
        """
        Return generator fo iterating over repository changelog.
        Yields tuple consisting of changeset and changesets number in changelog.
        """
        changeset = util.cachefunc(lambda r: self._repo[r].changeset())

        def split_windows(start, end, windowsize=512):
            while start < end:
                yield start, min(windowsize, end-start)
                start += windowsize

        def wanted(changeset_revision):
            if not item_id:
                namedb_fname = os.path.split(self._name_db)[-1]
                return namedb_fname not in changeset(changeset_revision)[3]
            else:
                return item_id in changeset(changeset_revision)[3]

        start, end = -1, 0
        if not len(self._repo):
            change_revs = []
        else:
            if not reverse:
                start, end = end, start
            change_revs = revrange(self._repo, ['%d:%d' % (start, end, )])

        for i, window in split_windows(0, len(change_revs)):
            revs = [change_rev for change_rev in change_revs[i:i+window] if wanted(change_rev)]
            for revno in revs:
                yield changeset(revno), revno

    def _lock(self, lockpath, lockref):
        """Acquire weak reference to lock object."""
        if lockref and lockref():
            return lockref()
        lock = self._repo._lock(lockpath, True, None, None, '')
        lockref = weakref.ref(lock)
        return lock

    def _repolock(self):
        """Acquire global repository lock."""
        return self._lock(self._revpath("repo.lock"), self._lockref)

    def _namelock(self):
        """Acquire name-mapping lock."""
        return self._lock(os.path.join(self._path, "%s.lock" % self._name_db), self._name_lockref)

    def _itemlock(self, item):
        """Acquire Item Metadata lock."""
        if not self._item_metadata_lockref.has_key(item._id):
            self._item_metadata_lockref[item._id] = None
        return self._lock(self._metapath(item._id + ".lock"), self._item_metadata_lockref[item._id])

    def _revpath(self, filename):
        """Return absolute path to file within repository."""
        return os.path.join(self._rev_path, filename)

    def _metapath(self, filename):
        """Return absolute path to Item metadata file."""
        return os.path.join(self._meta_path, filename)

    def _cachepath(self, filename):
        """Return absolute path to Item cache file."""
        return os.path.join(self._cache_path, filename)

    def _init_namedb(self):
        """
        Initialize name-mapping within repository. This allows further
        name-mapping versioning.
        """
        f = open(self._name_db, 'w')
        f.close()
        namedb_fname = os.path.split(self._name_db)[-1]
        self._repo.add([namedb_fname])
        self._repo.commit(text='(init name-mapping)', user='storage', files=[namedb_fname])

    def _read_name_db(self):
        """
        Read contents of name-mapping file into memory. This is done within
        lock because of possible data corruption when renames occur.
        Return two dicts: name-id and id-name mappings.
        """
        lock = self._namelock()
        try:
            name2id, id2name = {}, {}
            f = open(self._name_db, 'r')
            for line in f.readlines():
                id, name = line.strip().split(' ', 1)
                name = name.decode('utf-8')
                id2name[id], name2id[name] = name, id
            f.close()
            return name2id, id2name
        finally:
            del lock

    def _get_item_id(self, item_name):
        """Get internal ID of Item by given name. Return None if no such exists."""
        name2id, id2name = self._read_name_db()
        return name2id.get(item_name, None)

    def _get_item_name(self, item_id):
        """Get name of Item by given ID. Return None if no such exists."""
        name2id, id2name = self._read_name_db()
        return id2name.get(item_id, None)

    def _add_item(self, item):
        """
        Add new Item to name-mapping database and create Item cache file.
        Assign internal ID to Item. This ID is computed hash from Item name,
        timestamp and random integer.
        """
        encoded_name = item.name.encode("utf-8")
        m = md5.new()
        m.update("%s%s%d" % (time.time(), encoded_name, random.randint(0, RAND_MAX)))
        item_id = m.hexdigest()

        name2id, id2name = self._read_name_db()
        for id, name in id2name.iteritems():
            if name == item.name:
                raise ItemAlreadyExistsError("Destination item already exists: %s" % item.name)
        name_lock = self._namelock()
        try:
            f = open(self._name_db, 'a')
            f.write("%s %s\n" % (item_id, encoded_name, ))
            f.close()
        finally:
            del name_lock
        f = open(self._cachepath("%s.cache" % item_id), 'w')  # create cache file
        f.close()
        item._id = item_id

    def _recreate_cache(self, item, cachefile):
        """
        Iterate through Item Revisions and create cache file
        to optimize further Revision lookups.
        """
        revpairs = []
        for changeset, ctxrev in self._iterate_changesets(item_id=item._id):
            revpairs.append((pickle.loads(changeset[5]['__revision']), ctxrev, ))
        revpairs.sort()
        cachefile.write("".join(["%d:%d," % (rev, ctxrev) for rev, ctx in revpairs]))

    def _set_config(self):
        """
        Set up configuration for repository within which Item Revisions are stored.
        This includes reposiory hooks to update name-mapping and enabling backup
        extension.
        """
        config = ("[hooks]",
                 "preoutgoing.namedb = python:MoinMoin.storage.backends.hg.commit_namedb",
                 "prechangegroup.namedb = python:MoinMoin.storage.backends.hg.commit_namedb",
                 "[extensions]",
                 "MoinMoin.storage.backends.hg = ",
                 "", )
        f = open(os.path.join(self._rev_path, '.hg', 'hgrc'), 'w')
        f.writelines("\n".join(config))
        f.close()

    #
    # extended API below - needed for drawing revision graph
    #

    def _get_revision_node(self, revision):
        """Return internal ID (short SHA1) of Revision"""
        for changeset, ctxrevno in self._iterate_changesets(item_id=revision._item_id):
            if pickle.loads(changeset[5]['__revision']) == revision.revno:
                return short(self._repo[ctxrevno].node())

    def _get_revision_parents(self, revision):
        """Return parent revision numbers of Revision."""
        rcache = {}
        for changeset, ctxrevno in self._iterate_changesets(item_id=revision._item_id):
            revno = pickle.loads(changeset[5]['__revision'])
            rcache[ctxrevno] = revno
            if  revno == revision.revno:
                parentctxrevs = [p for p in self._repo.changelog.parentrevs(ctxrevno) if p != nullrev]
        parents = []
        for p in parentctxrevs:
            try:
                parents.append(rcache[p])
            except KeyError:
                pass
        return parents


class MercurialStoredRevision(StoredRevision):
    def __init__(self, item, revno, timestamp=None, size=None):
        StoredRevision.__init__(self, item, revno, timestamp, size)

    def get_parents(self):
        return self._backend._get_revision_parents(self)

    def get_node(self):
        return self._backend._get_revision_node(self)

    #
    # repository hooks - managing name-mapping file commits on push/pull requests
    #

def commit_namedb(ui, repo, **kw):
    """
    Commit name-mapping file.
    Used to keep repositories in sync with name-mapping on pull/push/clone requests.
    """
    changes = [[], ['.name-mapping'], [], [], [], []]
    parent = repo['tip'].node()
    ctx = context.workingctx(repo, (parent, nullid), "(updated name-mapping)", "storage", changes=changes)
    repo._commitctx(ctx)

    #
    # repository commands (extensions)
    #

def backup(ui, source, dest=None, **opts):
    """Wrapper for hg clone command. Sync name-mapping file before cloning."""
    commit_namedb(ui, source)
    commands.clone(ui, source, dest, **opts)

from mercurial.commands import remoteopts
cmdtable = {"backup": (backup,
         [('U', 'noupdate', None, 'the backup will only contain a repository (no working copy)'),
          ('r', 'rev', [], 'a changeset you would like to have after cloning'),
          ('', 'pull', None, 'use pull protocol to copy metadata'),
          ('', 'uncompressed', None, 'use uncompressed transfer (fast over LAN)'),
         ] + remoteopts,
         'hg backup [OPTION]... SOURCE [DEST]'),
}
