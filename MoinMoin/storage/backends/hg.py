# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Mercurial backend for new storage layer

    This package contains code for backend based on Mercurial distributed
    version control system. This backend provides several advantages for
    normal filesystem backend like internal atomicity handling, multiple
    concurrent editors without page edit locking or data cloning.

    As this code is based on new API design, it should prove consistency of this
    design and show how to use it in proper way.

    ---

    Second iteration of backend.

    Items with Revisions are stored in hg internal directory.
    Operations on Items are done in memory utilizing new mercurial features:
    memchangectx and memfilectx, which allow easy manipulation of changesets
    without the need of working copy.

    Items with Metadata are not versioned and stored in separate directory.

    Revision metadata is stored in mercurial internally, using dictionary binded
    with each changeset: 'extra'. This gives cleaner code, and mercurial stores
    this in optimal way itself.

    Still, development version of mercurial has some limitations to overcome:
    - file revision number is not increased when doing empty file commits
    - on empty commit file flags have to be manipulated to get file linked with
      changeset
    This affects:
    - we cannot support so called 'multiple empty revisions in a row',
      there is no possibility to commit (file) revision which hasnt changed since
      last time
    - as 'extra' dict is property of changeset, without increasing filerevs we're not
      able to link rev meta and rev data
    - revision metadata ('extra' dict) change is not stored in/as revision data,
      thus committing revision metadata changes is like commiting empty changesets

    To address this blockers, patch was applied on mercurial development version
    (see below).

    Repository layout hasnt changed much. Even though versioned items are stored now
    internally in .hg/, one can get rev/ directory populated on hg update as this
    is simply working copy directory.

    data/
    +-- rev/
        +-- .hg/
      ( +-- items_with_revs )  # this only if someone runs 'hg update'
    +-- meta/
        +-- items_without_revs


    IMPORTANT: This version of backend runs on newest development version of mercurial
    and small, additional patch for allowing multiple empty commits in a row
    patch: MoinMoin/storage/backends/research/repo_force_changes.diff

    ---

    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""
# XXX: update wiki and describe design/problems

from mercurial import hg, ui, context, node, util
from mercurial.repo import RepoError
from mercurial.revlog import LookupError
import StringIO
import cPickle as pickle
import tempfile
import weakref
import statvfs
import shutil
import md5
import os

from MoinMoin.wikiutil import quoteWikinameFS, unquoteWikiname
from MoinMoin.storage import Backend, Item, StoredRevision, NewRevision
from MoinMoin.storage.error import BackendError, NoSuchItemError,\
                                   NoSuchRevisionError,\
                                   RevisionNumberMismatchError,\
                                   ItemAlreadyExistsError, RevisionAlreadyExistsError
PICKLEPROTOCOL = 1

class MercurialBackend(Backend):
    """Implements backend storage using mercurial version control system."""

    def __init__(self, path, create=True):
        """
        Create backend data layout and initialize mercurial repository.
        Optionally can use already existing structure and repository.
        """
        self._path = os.path.abspath(path)
        self._r_path = os.path.join(self._path, 'rev')
        self._u_path = os.path.join(self._path, 'meta')
        self._ui = ui.ui(interactive=False, quiet=True)
        self._item_metadata_lock = {}
        self._lockref = None
        if not os.path.isdir(self._path):
            raise BackendError("Invalid path: %s" % self._path)
        if create:
            for path in (self._u_path, self._r_path):
                try:
                    if os.listdir(path):
                        raise BackendError("Directory not empty: %s" % path)
                except OSError:
                    pass  # directory not existing
        try:
            self._repo = hg.repository(self._ui, self._r_path, create)
        except RepoError:
            if create:
                raise BackendError("Repository exists at path: %s" % self._r_path)
            else:
                raise BackendError("Repository does not exist at path: %s" % self._r_path)
        try:
            os.mkdir(self._u_path)
        except OSError:
            if not os.path.isdir(self._u_path):
                if create:
                    shutil.rmtree(self._r_path)  # rollback
                raise BackendError("Unable to create directory: %s" % self._path)
        # XXX: does it work on windows?
        self._max_fname_length = os.statvfs(self._path)[statvfs.F_NAMEMAX]
        self._repo._forcedchanges = True  # XXX: this comes from patch

    def has_item(self, itemname):
        """Check whether Item with given name exists."""
        name = self._quote(itemname)
        return name in self._tipctx() or self._has_meta(itemname)

    def create_item(self, itemname):
        """
        Create Item in repository. This Item hasn't got any Revisions yet. Unless
        you create_revision+commit or change_metadata+publish_metdata, Item acts
        like a proxy for storing filled data. This method returns Item object.
        """
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Wrong Item name type: %s" % (type(itemname)))
        # XXX: should go to abstract
        if self.has_item(itemname):
            raise ItemAlreadyExistsError("Item with that name already exists: %s" % itemname)
        item = Item(self, itemname)
        item._exists = False
        return item

    def get_item(self, itemname):
        """
        Return an Item with given name, else raise NoSuchItemError
        exception.
        """
        if not self.has_item(itemname):
            raise NoSuchItemError('Item does not exist: %s' % itemname)
        item = Item(self, itemname)
        item._exists = True
        return item

    def search_item(self, searchterm):
        """Returns generator for iterating over matched items by searchterm."""
        for item in self.iteritems():
            searchterm.prepare()
            if searchterm.evaluate(item):
                yield item

    def iteritems(self):
        """
        Return generator for iterating through items collection
        in repository.
        """
        itemlist = [name for name in iter(self._tipctx())] + os.listdir(self._u_path)
        for itemname in itemlist:
            yield Item(self, itemname)

    def _create_revision(self, item, revno):
        """Create new Item Revision."""
        revs = item.list_revisions()
        if revs:
            if revno in revs:
                raise RevisionAlreadyExistsError("Item Revision already exists: %s" % revno)
            if revno != revs[-1] + 1:
                raise RevisionNumberMismatchError("Unable to create revision number %d. \
                    New Revision number must be next to latest Revision number." % revno)
        rev = NewRevision(item, revno)
        rev._data = StringIO.StringIO()
        rev._revno = revno
        return rev

    def _get_revision(self, item, revno):
        """Returns given Revision of an Item."""
        ctx = self._repo[self._repo.changelog.tip()]
        name = self._quote(item.name)
        try:
            revs = item.list_revisions()
            if revno == -1 and revs:
                revno = max(revs)
            fctx = ctx[name].filectx(revno)
        except LookupError:
            raise NoSuchRevisionError("Item Revision does not exist: %s" % revno)

        revision = StoredRevision(item, revno)
        revision._data = StringIO.StringIO(fctx.data())
        def manglekeys(dict):
            newdict = {}
            for k in (key for key in dict.iterkeys() if key.startswith("_")):
                newdict[k[1:]] = dict[k]
            return newdict

        revision._metadata = manglekeys(ctx.extra())
        return revision

    def _list_revisions(self, item):
        """
        Return a list of Item revision numbers.
        Retrieves only accessible rev numbers when internal indexfile
        inconsistency occurs.
        """
        filelog = self._repo.file(self._quote(item.name))
        cl_count = len(self._repo)
        revs = []
        for revno in xrange(len(filelog)):
            try:
                assert filelog.linkrev(filelog.node(revno)) < cl_count, \
                    "Revision number out of bounds, repository inconsistency!"
                revs.append(revno)
            except (IndexError, AssertionError):  # malformed index file
                pass  # XXX: should we log inconsistency?
        return revs

    def _write_revision_data(self, revision, data):
        """Write data to the Revision."""
        revision._data.write(data)

    def _read_revision_data(self, revision, chunksize):
        """
        Called to read a given amount of bytes of a revisions data. By default, all
        data is read.
        """
        if chunksize < 0:
            return revision._data.read()
        return revision._data.read(chunksize)

    def _seek_revision_data(self, revision, position, mode):
        """Set the revisions cursor on the revisions data."""
        revision._data.seek(position, mode)

    def _rename_item(self, item, newname):
        """
        Renames given Item name to newname. Raises NoSuchItemError if source
        item is unreachable or ItemAlreadyExistsError if destination exists.
        """
        if not isinstance(newname, (str, unicode)):
            raise TypeError("Wrong Item destination name type: %s" % (type(newname)))
        # XXX: again, to the abstract
        if not self.has_item(item.name):
            raise NoSuchItemError('Source item does not exist: %s' % item.name)

        lock = self._repolock()
        try:
            if self.has_item(newname):
                raise ItemAlreadyExistsError("Destination item already exists: %s" % newname)
            files = [self._quote(item.name), self._quote(newname)]
            if self._has_meta(item.name):
                util.rename(self._upath(files[0]), self._upath(files[1]))
            else:
                def getfilectx(repo, memctx, path):
                    if path == files[1]:
                        copies = files[0]
                    else:
                        copies = None
                    return context.memfilectx(path, '', False, False, copies)

                msg = "Renamed %s to: %s" % (item.name.encode('utf-8'), newname.encode('utf-8'))
                editor = ""  # XXX: get from upper layer here
                p1, p2 = self._repo.changelog.tip(), node.nullid
                ctx = context.memctx(self._repo, (p1, p2), msg, [], getfilectx, user=editor)
                ctx._status[2] = [files[0]]
                ctx._status[1] = [files[1]]
                self._repo.commitctx(ctx)

            item._name = newname
        finally:
            del lock

    def _change_item_metadata(self, item):
        """Start Item metadata transaction."""
        if item._exists:
            item._lock = self._itemlock(item)

    def _publish_item_metadata(self, item):
        """Dump Item metadata to file and finish transaction."""
        meta_item_path = self._upath(self._quote(item.name))

        def write_meta_item(itempath, metadata):
            tmpfd, tmpfpath = tempfile.mkstemp("-meta", "tmp-", self._u_path)
            f = os.fdopen(tmpfd, 'wb')
            pickle.dump(item._metadata, f, protocol=PICKLEPROTOCOL)
            f.close()
            util.rename(tmpfpath, itempath)

        if item._exists:
            if item._metadata is None:
                pass
            else:
                write_meta_item(meta_item_path, item._metadata)
            print "delete lock"
            del item._lock
        else:
            if self.has_item(item.name):
                raise ItemAlreadyExistsError("Item already exists: %s" % item.name)
            if item._metadata is None:
                item._metadata = {}
            write_meta_item(meta_item_path, item._metadata)
            item._exists = True

    def _get_item_metadata(self, item):
        """Load Item metadata from file. Return dictionary."""
        quoted_name = self._quote(item.name)
        if os.path.exists(self._upath(quoted_name)):
            f = open(self._upath(quoted_name), "rb")
            item._metadata = pickle.load(f)
            f.close()
        else:
            item._metadata = {}
        return item._metadata

    def _commit_item(self, item):
        """Commit Item changes within transaction (Revision) to repository."""
        rev = item._uncommitted_revision
        def manglekeys(dict):
            newdict = {}
            for key in dict.iterkeys():
                newdict["_%s" % key] = dict[key]
            return newdict

        meta = manglekeys(dict(rev))
        name = self._quote(item.name)
        lock = self._repolock()
        try:
            has_item = self.has_item(item.name)
            if has_item:
                if rev.revno == 0:
                    raise ItemAlreadyExistsError("Item already exists: %s" % item.name)
                elif rev.revno in item.list_revisions():
                    raise RevisionAlreadyExistsError("Revision already exists: %d" % rev.revno)
            msg = meta.get("comment", "")
            user = meta.get("editor", "anonymous")  # XXX: meta keys review
            data = rev._data.getvalue()
            file = [name]

            def getfilectx(repo, memctx, path):
                return context.memfilectx(path, data, False, False, False)

            p1, p2 = self._repo.changelog.tip(), node.nullid
            ctx = context.memctx(self._repo, (p1, p2), msg, file, getfilectx, user, extra=meta)
            if not has_item:
                ctx._status[1], ctx._status[0] = ctx._status[0], ctx._status[1]
            self._repo.commitctx(ctx)
            item._exists = True
        finally:
            del lock
            item._uncommitted_revision = None  # XXX: move to abstract

    def _rollback_item(self, item):
        """Reverts uncommited Item changes."""
        item._uncommitted_revision = None  # XXX: move to abstract

    def _trim(self, name):
        """Trim given name to fit in maximum supported length on filesystem."""
        # see http://www.moinmo.in/PawelPacana/MercurialBackend#Mercurialbehaviour
        if len(name) > ((self._max_fname_length - 2) // 2):
            m = md5.new()
            m.update(name)
            hashed = m.hexdigest()
            return "%s-%s" % (name[:(self._max_fname_length - len(hashed) - 3) // 2], hashed)
        else:
            return name

    def _lock(self, lockpath, lockref):
        if lockref and lockref():
            return lockref()
        lock = self._repo._lock(lockpath, True, None, None, '')
        lockref = weakref.ref(lock)
        return lock

    def _repolock(self):
        """Acquire global repository lock"""
        return self._lock(self._rpath("repo.lock"), self._lockref)

    def _itemlock(self, item):
        """Acquire unrevisioned Item lock."""
        # XXX: long item name
        if not self._item_metadata_lock.has_key(item.name):
            self._item_metadata_lock[item.name] = None
        lpath = self._upath(self._quote(item.name + ".lock"))
        return self._lock(lpath, self._item_metadata_lock[item.name])

    def _tipctx(self):
        """Return newest changeset in repository."""
        return self._repo[self._repo.changelog.tip()]

    def _has_meta(self, itemname):
        """Check if unversioned item with supplied name exists."""
        return os.path.exists(self._upath(self._quote(itemname)))

    def _rpath(self, filename):
        """Return absolute path to revisioned Item in repository."""
        return os.path.join(self._r_path, filename)

    def _upath(self, filename):
        """Return absolute path to unrevisioned Item in repository."""
        return os.path.join(self._u_path, filename)

    def _quote(self, name):
        """Return safely quoted name."""
        if not isinstance(name, unicode):
            name = unicode(name, 'utf-8')
        return self._trim(quoteWikinameFS(name))

    def _unquote(self, quoted):
        """Return unquoted, real name."""
        return unquoteWikiname(quoted)

