# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Mercurial backend for new storage layer

    This package contains code for backend based on Mercurial distributed
    version control system. This backend provides several advantages for
    normal filesystem backend like:
    - internal atomicity handling and revisioning
    - multiple concurrent editors without page edit-locks
    - data cloning

    As this code is based on new API design, it should prove consistency of this
    design and show how to use it in proper way.

    ---

    Fourth iteration of backend.

    Items with Revisions are stored in hg internal directory.
    Operations on Items are done in memory, utilizing new mercurial features:
    memchangectx and memfilectx, which allow easy manipulation of changesets
    without the need of working copy. Advantage is less I/O operations.

    Revision data before commit is also stored in memory using StringIO.
    While this good for small Items, bigger ones that don't fit into memory
    will fail.

    Revision metadata is stored in mercurial internally, using dictionary bound
    to each changeset: 'extra'. This gives cleaner code, and mercurial stores
    this in optimal way itself.

    Item Metadata is not versioned and stored in separate directory.

    This implementation does not identify Items internally by name. Instead Items
    have unique ID's which are currently MD5 hashes. Name-to-id translation is
    stored in cdb.
    Renames are done by relinking name with hash. Item does not move itself in hg.
    Thus 'hg rename' is not used, and renames won't be possible 'on console' without
    providing dedicated hg extensions.

    Dropping previous names implementation had few motivations:
    - Item names on filesystem, altough previously quoted and trimmed to conform
      limits - still needed some care when operating 'on console', so any way
      both implementations needed tools to translate names.
    - Rename history compatibilty not breaking current API. In 'hg rename', commit
      after rename was forced, and there was no possibilty to pass revision metadata
      (internationalized comment i.e.) without messing too much - either in API or
      masking such commits in hg.

    One downfall of this new implementation is total name obfusaction for 'console'
    editors. To address this problem few hg extensions should be provided:
    - hg wrename
    - hg wcommit
    - hg wmerge
    - hg wmanifest
    - hg wlog with template for viewing revision metadata
    All these extensions take real page name and translate to hash internally.

    When possible, no tricky things like revision hiding or manifest/index
    manipulation takes place in this backend. Items revisions are stored as
    file revisions. Revision metadata goes to changeset dict (changesets contain
    only one file).

    This backend uses development version of mercurial. Besides this there are
    few limitations to overcome:
    - file revision number is not increased when doing empty file commits
      (to be more precise, when nothing changes beetween commits: revdata and revmeta)
      (Johannes Berg insists this "shouldn't be disallowed arbitrarily", the term used
      to describe this backend behaviour: "multiple empty revisions in a row")
      (as long as revmeta is stored in changeset, empty revdata is sufficent to consider
      commit as empty, and this is the _real_ problem)
    - on empty commit file flags have to be manipulated to get file bound with changeset
      (and without this revmeta is disconnected with Revision it describes)
      (however this could be done)

    If we drop support for "multiple empty revisions in a row" and change implementation
    of revision metadata we could survive without patching hg. However other implementations
    of revmeta are not so neat as current one, and the patch is only three harmless lines ;)
    (MoinMoin/storage/backends/research/repo_force_changes.diff)

    Repository layout:
    - Item as files in rev/ with filename 'ID'. Revisions stored internally in .hg/
      Since we're doing memory commits there will be no files in this directory
      until manual 'hg update' from console.
    - Item Metadata stored in meta/ as 'ID.meta'
    - Item real names are stored loosely in data/ as 'ID.name'. This is for console users,
      and reverse mapping.
    - name-mapping db in data/name-mapping file

    data/
    +-- rev/
        +-- .hg/
        +-- 0f4eac723857aa118122c08f534fcf56  # this only if someone runs 'hg update'
        +-- ...
    +-- meta/
        +-- 0f4eac723857aa118122c08f534fcf56.meta
        +-- 4c4712a4141d261ec0ca8f9037950685.meta
        +-- ...
    +-- 0f4eac723857aa118122c08f534fcf56.name
    +-- 4c4712a4141d261ec0ca8f9037950685.name
    +-- ...
    +-- name-mapping

    IMPORTANT: This version of backend runs on newest development version of mercurial
    and small, additional patch for allowing multiple empty commits in a row
    patch: MoinMoin/storage/backends/research/repo_force_changes.diff

    HOW TO GET IT WORKING:
    1) hg clone -r 6773 http://selenic.com/repo/hg
        [newer revisions were not tested, do on your own risk]
    2) make local
    3) export PYTHONPATH=your_hg_devel_dir
    4) apply patch from MoinMoin/storage/backends/research/repo_force_changes.diff

    ---

    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""

from mercurial import hg, ui, context, util, commands, merge
from mercurial.node import nullid, nullrev, short
from mercurial.repo import RepoError
from mercurial.revlog import LookupError
from mercurial.cmdutil import revrange
import cPickle as pickle
import struct
import StringIO
import tempfile
import weakref
import shutil
import random
import md5
import os
import errno
import time


from MoinMoin.storage import Backend, Item, StoredRevision, NewRevision, EDIT_LOG_USERID, EDIT_LOG_COMMENT
from MoinMoin.storage.error import BackendError, NoSuchItemError,\
                                   NoSuchRevisionError,\
                                   RevisionNumberMismatchError,\
                                   ItemAlreadyExistsError, RevisionAlreadyExistsError

PICKLE_ITEM_META = 1
PICKLE_REV_META = 0
RAND_MAX = 1024


class MercurialBackend(Backend):
    """Implements backend storage using mercurial version control system."""

    def __init__(self, path):
        """
        Create backend data layout and initialize mercurial repository.
        If bakckend already exists, use structure and repository.
        """
        self._path = os.path.abspath(path)
        self._r_path = os.path.join(self._path, 'rev')
        self._u_path = os.path.join(self._path, 'meta')
        self._c_path = os.path.join(self._path, 'cache')
        self._name_db = os.path.join(self._r_path, '.name-mapping')
        self._ui = ui.ui(interactive=False, quiet=True)
        self._item_metadata_lock = {}
        self._lockref = None
        self._name_lockref = None
        os.environ["HGMERGE"] = "internal:fail"
        try:
            os.mkdir(self._path)
        except OSError, err:
            if err.errno == errno.EACCES:
                raise BackendError("No permisions on path: %s" % self._path)
            elif not os.path.isdir(self._path):
                raise BackendError("Invalid path: %s" % self._path)
        for path in (self._u_path, self._r_path, self._c_path):
            try:
                os.mkdir(path)
            except OSError:
                pass
        try:
            self._repo = hg.repository(self._ui, self._r_path, create=True)
        except RepoError:
            self._repo = hg.repository(self._ui, self._r_path)
        self._repo._forcedchanges = True
        self._set_config()

        if not os.path.exists(self._name_db):
            self._init_namedb()

    def _set_config(self):
        config = ("[hooks]",
                 "preoutgoing.namedb = python:MoinMoin.storage.backends.hg.commit_namedb",
                 "prechangegroup.namedb = python:MoinMoin.storage.backends.hg.commit_namedb",
                 "[extensions]",
                 "MoinMoin.storage.backends.hg = ",
                 "", )
        f = open(os.path.join(self._r_path, '.hg', 'hgrc'), 'w')
        f.writelines("\n".join(config))
        f.close()

    def has_item(self, itemname):
        """Return true if Item exists."""
        return self._get_item_id(itemname) is not None

    def create_item(self, itemname):
        """
        Create Item in repository. This Item hasn't got any Revisions yet. Unless
        you create_revision+commit or change_metadata+publish_metdata, Item acts
        like a proxy for storing filled data. This method returns Item object.
        """
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Wrong Item name type: %s" % (type(itemname)))  # XXX: should go to abstract
        if self.has_item(itemname):
            raise ItemAlreadyExistsError("Item with that name already exists: %s" % itemname)
        item = Item(self, itemname)
        item._id = None
        return item

    def get_item(self, itemname):
        """
        Return an Item with given name, else raise NoSuchItemError
        exception.
        """
        item_id = self._get_item_id(itemname)
        if not item_id:
            raise NoSuchItemError('Item does not exist: %s' % itemname)
        item = Item(self, itemname)
        item._id = item_id
        return item

    def iteritems(self):
        """
        Return generator for iterating through items collection
        in repository.
        """
        namedb = self._read_name_db()
        for line in namedb:
            id, name = line.split(' ', 1)
            item = Item(self, name.decode('utf-8'))
            item._id = id
            yield item

    def history(self, reverse=True):
        """History implementation reading the log file."""
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
        """Create new Item Revision."""
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
        """Returns given Revision of an Item."""
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
        """Get size of Revision."""
        ftx = self._repo['tip'][rev._item_id].filectx(rev.revno)
        return ftx.size()

    def _get_revision_metadata(self, rev):
        """Return Revision metadata dictionary."""
        changectx = self._has_revision(rev.item, rev.revno)[2]
        metadata = {}
        for k, v in changectx.extra().iteritems():
            if k.startswith('moin_'):
                metadata[k.lstrip('moin_')] = pickle.loads(v)
            elif k.startswith('__'):
                metadata[k] = pickle.loads(v)
        return metadata

    def _get_revision_timestamp(self, rev):
        """Return revision timestamp"""
        if rev._metadata is None:
            return self._get_revision_metadata(rev)['__timestamp']
        return rev._metadata['__timestamp']

    def _write_revision_data(self, revision, data):
        """Write data to the Revision."""
        revision._data.write(data)

    def _read_revision_data(self, revision, chunksize):
        """
        Called to read a given amount of bytes of a revisions data. By default, all
        data is read.
        """
        return revision._data.read(chunksize)

    def _seek_revision_data(self, revision, position, mode):
        """Set the revisions cursor on the revisions data."""
        revision._data.seek(position, mode)

    def _list_revisions(self, item):
        """
        Return a list of Item revision numbers.
        """
        if not item._id:
            return []
        else:
            try:
                f = open(self._cpath(item._id + ".cache"))
                revs = [int(revpair.split(':')[0]) for revpair in f.read().split(',') if revpair]
                f.close()
                revs.sort()
                return revs
            except EOFError:
                return []
            except IOError:
                revs = []
                changefn = util.cachefunc(lambda r: self._repo[r].changeset())
                for changeset in self._iterate_changesets(item_id=item._id):
                    revno = pickle.loads(changeset[5]['__revision'])
                    revs.append(revno)
                    if revno == 0:  # iterating from top
                        revs.reverse()
                        return revs
                return []

    def _rename_item(self, item, newname):
        """
        Renames given Item name to newname. Raises NoSuchItemError if source
        item is unreachable or ItemAlreadyExistsError if destination exists.
        """
        lock = self._repolock()
        try:
            if self.has_item(newname):
                raise ItemAlreadyExistsError("Destination item already exists: %s" % newname)

            encoded_name = newname.encode('utf-8')
            namedb, namelist = self._read_name_db(), []
            for line in namedb:
                id, name = line.split(' ', 1)
                if id == item._id:
                    namelist.append("%s %s" % (id, encoded_name, ))
                else:
                    namelist.append("%s %s" % (id, name, ))

            fd, fname = tempfile.mkstemp("-tmp", "namedb-", self._path)
            os.write(fd, "\n".join(namelist) + "\n")
            os.close(fd)

            name_lock = self._namelock()
            try:
                util.rename(fname, self._name_db)
            finally:
                del name_lock
        finally:
            del lock

    def _get_item_metadata(self, item):
        """Load Item metadata from file. Return dictionary."""
        if item._id:
            try:
                f = open(self._upath(item._id + ".meta"), "rb")
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
        """Start Item metadata transaction."""
        if item._id:
            item._lock = self._itemlock(item)

    def _publish_item_metadata(self, item):
        """Dump Item metadata to file and finish transaction."""
        def write_meta_item(item_path, metadata):
            tmp_fd, tmp_fpath = tempfile.mkstemp("-meta", "tmp-", self._u_path)
            f = os.fdopen(tmp_fd, 'wb')
            pickle.dump(item._metadata, f, protocol=PICKLE_ITEM_META)
            f.close()
            util.rename(tmp_fpath, item_path)

        if item._id:
            if item._metadata is None:
                pass
            elif not item._metadata:
                try:
                    os.remove(self._upath("%s.meta" % item._id))
                except OSError:
                    pass
            else:
                write_meta_item(self._upath("%s.meta" % item._id), item._metadata)
            del item._lock
        else:
            self._add_item(item)
            if item._metadata:
                write_meta_item(self._upath("%s.meta" % item._id), item._metadata)


    def _commit_item(self, rev):
        """Commit Item changes within transaction (Revision) to repository."""
        def getfilectx(repo, memctx, path):
            return context.memfilectx(path, data, False, False, False)

        item = rev.item
        if not item._id and self.has_item(item.name):
            raise ItemAlreadyExistsError("Item already exists: %s" % item.name)

        if rev.timestamp is None:
            rev.timestamp = long(time.time())
        msg = rev.get(EDIT_LOG_COMMENT, "").encode("utf-8")
        user = rev.get(EDIT_LOG_USERID, "anonymous")
        data = rev._data.getvalue()

        meta = {'__timestamp': pickle.dumps(rev.timestamp, PICKLE_REV_META),
                '__revision': pickle.dumps(rev.revno, PICKLE_REV_META)}
        for k, v in rev.iteritems():
            meta["moin_%s" % k] = pickle.dumps(v, PICKLE_REV_META)

        lock = self._repolock()
        try:
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
            f = open(self._cpath("%s.cache" % item._id), 'a')
            if not f.tell() and not rev.revno == 0:
                self._recreate_cache(item, f)
            f.write("%d:%d," % (rev.revno, tiprevno, ))
            f.close()
        finally:
            del lock

    def _rollback_item(self, rev):
        pass  # generic rollback is sufficent

    def _lock(self, lockpath, lockref):
        """"Generic lock helper"""
        if lockref and lockref():
            return lockref()
        lock = self._repo._lock(lockpath, True, None, None, '')
        lockref = weakref.ref(lock)
        return lock

    def _repolock(self):
        """Acquire global repository lock"""
        return self._lock(self._rpath("repo.lock"), self._lockref)

    def _namelock(self):
        """Acquire name mapping lock"""
        return self._lock(os.path.join(self._path, "%s.lock" % self._name_db), self._name_lockref)

    def _itemlock(self, item):
        """Acquire unrevisioned Item lock."""
        if not self._item_metadata_lock.has_key(item.name):
            self._item_metadata_lock[item.name] = None
        lpath = self._upath(item._id + ".lock")
        return self._lock(lpath, self._item_metadata_lock[item.name])

    def _rpath(self, filename):
        """Return absolute path to revisioned Item in repository."""
        return os.path.join(self._r_path, filename)

    def _upath(self, filename):
        """Return absolute path to unrevisioned Item in repository."""
        return os.path.join(self._u_path, filename)

    def _cpath(self, filename):
        return os.path.join(self._c_path, filename)

    def _read_name_db(self):
        lock = self._namelock()
        try:
            try:
                f = open(self._name_db, 'r')
                namedb = []
                for line in f.readlines():
                    namedb.append(line.strip())
                f.close()
                return namedb
            except IOError:
                return []
        finally:
            del lock

    def _get_item_id(self, item_name):
        """Get ID of item (or None if no such item exists)"""
        namedb = self._read_name_db()
        for line in namedb:
            id, name = line.split(' ', 1)
            if name == item_name.encode('utf-8'):
                return id

    def _get_item_name(self, item_id):
        """Get name of item (or None if no such item exists)"""
        namedb = self._read_name_db()
        for line in namedb:
            id, name = line.split(' ', 1)
            if id == item_id:
                return name.decode('utf-8')

    def _add_item(self, item):
        """Add new Item to name-mapping and create name file."""
        m = md5.new()
        m.update("%s%s%d" % (time.time(), item.name.encode("utf-8"), random.randint(0, RAND_MAX)))
        item_id = m.hexdigest()
        encoded_name = item.name.encode('utf-8')

        namedb = self._read_name_db()
        for line in namedb:
            id, name = line.split(' ', 1)
            if name == encoded_name:
                raise ItemAlreadyExistsError("Destination item already exists: %s" % item.name)

        name_lock = self._namelock()
        try:
            f = open(self._name_db, 'a')
            f.write("%s %s\n" % (item_id, encoded_name, ))
            f.close()
        finally:
            del name_lock

        f = open(self._cpath("%s.cache" % item_id), 'w')
        f.close()
        item._id = item_id

    def _has_revision(self, item, revno):
        if not item._id:
            return False, -1, None
        try:
            f = open(self._cpath(item._id + ".cache"))
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

    def _recreate_cache(self, item, cachefile):
        revpairs = []
        for changeset, ctxrev in self._iterate_changesets(item_id=item._id):
            revpairs.append((pickle.loads(changeset[5]['__revision']), ctxrev, ))
        revpairs.sort()
        cachefile.write("".join(["%d:%d," % (rev, ctxrev) for rev, ctx in revpairs]))

    def _init_namedb(self):
            f = open(self._name_db, 'w')
            f.close()
            namedb_fname = os.path.split(self._name_db)[-1]
            self._repo.add([namedb_fname])
            self._repo.commit(text='(init name-mapping)', user='storage', files=[namedb_fname])

    #
    # extended API below
    #

    def _get_revision_node(self, revision):
        """Return internal short SHA1 id of Revision"""
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
    changes = [[], ['.name-mapping'], [], [], [], []]
    parent = repo['tip'].node()
    ctx = context.workingctx(repo, (parent, nullid), "(updated name-mapping)", "storage", changes=changes)
    repo._commitctx(ctx)


    #
    # repository commands (extensions)
    #

def backup(ui, source, dest=None, **opts):
    commit_namedb(ui, source)
    commands.clone(ui, source, dest, **opts)

from mercurial.commands import remoteopts
cmdtable = {"backup": (backup,
         [('U', 'noupdate', None, 'the clone will only contain a repository (no working copy)'),
          ('r', 'rev', [], 'a changeset you would like to have after cloning'),
          ('', 'pull', None, 'use pull protocol to copy metadata'),
          ('', 'uncompressed', None, 'use uncompressed transfer (fast over LAN)'),
         ] + remoteopts,
         'hg backup [OPTION]... SOURCE [DEST]'),
}
