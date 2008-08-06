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

    Third iteration of backend.

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
from mercurial.node import nullid
from mercurial.repo import RepoError
from mercurial.revlog import LookupError
import cPickle as pickle
import struct
import StringIO
import tempfile
import weakref
import shutil
import random
import datetime
import md5
import os
import errno
import time

from MoinMoin import log
from MoinMoin.util import diff3
from MoinMoin.PageEditor import conflict_markers
from MoinMoin.storage import Backend, Item, StoredRevision, NewRevision
from MoinMoin.storage.error import BackendError, NoSuchItemError,\
                                   NoSuchRevisionError,\
                                   RevisionNumberMismatchError,\
                                   ItemAlreadyExistsError, RevisionAlreadyExistsError
try:
    import cdb
except ImportError:
    from MoinMoin.support import pycdb as cdb

PICKLEPROTOCOL = 1
RAND_MAX = 1024
logging = log.getLogger("MercurialBackend")


class MercurialBackend(Backend):
    """Implements backend storage using mercurial version control system."""

    def __init__(self, path, create=True):
        """
        Create backend data layout and initialize mercurial repository.
        Optionally can use already existing structure and repository.
        """
        self._path = os.path.abspath(path)
        self._news = os.path.join(self._path, 'news')
        self._r_path = os.path.join(self._path, 'rev')
        self._u_path = os.path.join(self._path, 'meta')
        self._name_db = os.path.join(self._path, 'name-mapping')
        self._ui = ui.ui(interactive=False, quiet=True)
        self._item_metadata_lock = {}
        self._lockref = None
        self._name_lockref = None

        if not os.path.isdir(self._path):
            raise BackendError("Invalid path: %s" % self._path)
        if create:
            for path in (self._u_path, self._r_path):
                try:
                    if os.listdir(path):
                        raise BackendError("Directory not empty: %s" % path)
                except OSError:
                    pass  # directory not existing
            for item in os.listdir(self._path):
                if (os.path.isdir(item) and item not in ('rev', 'meta') or
                        not os.path.isdir(os.path.join(self._path, item)) and item != "name-mapping"):
                    raise BackendError("Directory not empty: %s" % self._path)
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

        if not os.path.exists(self._name_db):
            lock = self._namelock()
            try:
                self._create_new_cdb()
            finally:
                del lock

        self._repo._forcedchanges = True

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
            raise TypeError("Wrong Item name type: %s" % (type(itemname)))
        # XXX: should go to abstract
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
        c = cdb.init(self._name_db)
        r = c.each()
        while r:
            item = Item(self, r[0])
            item._id = r[1]
            yield item
            r = c.each()

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
        ctx = self._repo[self._repo.changelog.tip()]
        #try:
        revs = self._list_revisions(item)
        if revno == -1 and revs:
            revno = max(revs)
        #fctx = ctx[item._id].filectx(revno)
        #except LookupError:
        if revno not in revs:
            raise NoSuchRevisionError("Item Revision does not exist: %s" % revno)
        # XXX: to rewrite for more optimal
        for item_rev, repo_rev in enumerate([revno_ for revno_ in iter(self._repo)
                                              if item._id in self._repo[revno_].files()]):
            if item_rev == revno:
                ctx = self._repo[repo_rev]
        revision = StoredRevision(item, revno)
        revision._data = StringIO.StringIO(ctx.filectx(item._id).data())
        revision._item_id = item._id
        revision._metadata = dict(((key.lstrip("moin_"), value) for key, value in ctx.extra().iteritems() 
                                   if key.startswith('moin_')))
        return revision
    
    def _get_revision_size(self, rev):
        tip = self._repo.changelog.tip()
        ftx = self._repo[tip][rev._item_id].filectx(rev.revno)
        return ftx.size()
        
    def _list_revisions(self, item):
        """
        Return a list of Item revision numbers.
        Retrieves only accessible rev numbers when internal indexfile
        inconsistency occurs.
        """
        if not item._id:
            return []
        else:                                                                            
            revs = []
            ctxs = [revno for revno in iter(self._repo) if item._id in self._repo[revno].files()]
            # XXX: extremely slow, but no solution to include <merges> in revs by now
            # XXX: consider cmdutil.walkchangerevs
            for revno in xrange(len(ctxs)):
                revs.append(revno)                                                                  
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
        lock = self._repolock()
        try:
            if self.has_item(newname):
                raise ItemAlreadyExistsError("Destination item already exists: %s" % newname)

            encoded_name = newname.encode('utf-8')
            name_path = os.path.join(self._path, '%s.name' % item._id)

            c = cdb.init(self._name_db)
            maker = cdb.cdbmake(self._name_db + '.ndb', self._name_db + '.tmp')
            r = c.each()
            while r:
                name, id = r
                if name == encoded_name:
                    raise ItemAlreadyExistsError("Destination item already exists: %s" % newname)
                elif id == item._id:
                    maker.add(encoded_name, id)
                else:
                    maker.add(name, id)
                r = c.each()
            maker.finish()
            util.rename(self._name_db + '.ndb', self._name_db)

            name_file = open(name_path, mode='wb')
            name_file.write(encoded_name)
            name_file.close()
            item._name = newname
        finally:
            del lock

    def _change_item_metadata(self, item):
        """Start Item metadata transaction."""
        if item._id:
            item._lock = self._itemlock(item)

    def _publish_item_metadata(self, item):
        """Dump Item metadata to file and finish transaction."""
        def write_meta_item(item_path, metadata):
            tmp_fd, tmp_fpath = tempfile.mkstemp("-meta", "tmp-", self._u_path)
            f = os.fdopen(tmp_fd, 'wb')
            pickle.dump(item._metadata, f, protocol=PICKLEPROTOCOL)
            f.close()
            util.rename(tmp_fpath, item_path)

        if item._id:
            if item._metadata is None:
                pass
            else:
                write_meta_item(self._upath("%s.meta" % item._id), item._metadata)
            del item._lock
        else:
            self._add_item(item)
            if item._metadata is None:
                item._metadata = {}
            write_meta_item(self._upath("%s.meta" % item._id), item._metadata)

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

    def _commit_item(self, item):
        """Commit Item changes within transaction (Revision) to repository."""
        rev = item._uncommitted_revision
        if not item._id and self.has_item(item.name):
            raise ItemAlreadyExistsError("Item already exists: %s" % item.name)

        if rev.timestamp is None:
            rev.timestamp = long(time.time())

        meta = dict(("moin_%s" % key, value) for key, value in rev.iteritems())
        meta['__timestamp'] = rev.timestamp
        lock = self._repolock()
        try:
            def getfilectx(repo, memctx, path):
                return context.memfilectx(path, data, False, False, False)

            msg = meta.get("moin_comment", "")
            user = meta.get("moin_editor", "anonymous")  # XXX: meta keys spec
            data = rev._data.getvalue()

            p1, p2 = self._repo.changelog.tip(), nullid
            if not item._id:
                self._add_item(item)                
            else:
                fname = [item._id]
                filelog = self._repo.file(item._id)
                n = filelog.node(rev.revno - 1)
                if rev.revno in self._list_revisions(item):
                    p1, p2 = self._repo[filelog.linkrev(n)].node(), nullid

            ctx = context.memctx(self._repo, (p1, p2), msg, [], getfilectx, user, extra=meta)
            if rev.revno == 0:
                ctx._status[1] = [item._id]
            else:
                ctx._status[0] = [item._id]
            self._repo.commitctx(ctx)
            
            if len(self._repo.heads()) > 1:  # policy: always merge with tip, 
                meta = {}                    # at most two heads in this block
                nodes = self._repo.changelog.nodesbetween([p1])[0]
                newest_node = self._repo[len(self._repo) - 1].node()
                for node in reversed(nodes):
                    if (node not in (p1, newest_node) and 
                                    item._id in self._repo.changectx(node).files()):
                        for n in (node, newest_node):                        
                            meta.update(self._repo.changectx(n).extra())
                        break                        
                
                merge.update(self._repo, newest_node, True, False, False)                       
                msg = "Merged %s" % item.name  # XXX: just for now                
                parent_data = self._get_revision(item, rev.revno - 1).read()
                other_data = self._get_revision(item, rev.revno).read()
                my_data = data                
                data = diff3.text_merge(parent_data, other_data, my_data, True, *conflict_markers)
                #print data            
                #self._repo.wwrite(item._id, data, "")
                #self._repo.commit(user=user, text=msg, files=[item._id], extra=meta)
                p1, p2 = self._repo.heads()
                ctx = context.memctx(self._repo, (p1, p2), msg, [item._id], getfilectx, user, extra=meta)
                self._repo._commitctx(ctx)            
            else:
                commands.update(self._ui, self._repo)
            self._addnews(item._id, rev.revno, rev.timestamp)
        finally:           
            del lock
            item._uncommitted_revision = None  # XXX: move to abstract

    def _rollback_item(self, item):
        """Reverts uncommited Item changes."""
        item._uncommitted_revision = None  # XXX: move to abstract

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
        # XXX: long item name
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

    def _get_revision_metadata(self, rev):
        """Return Revision metadata dictionary."""
        tip = self._repo.changelog.tip()
        fctx = self._repo[tip][rev.item_id].filectx(rev.revno)
        return dict(((key.lstrip("_"), value) for key, value in
                     fctx.changectx().extra().iteritems() if key.startswith('_')))

    def _create_new_cdb(self):
        """Create new name-mapping if it doesn't exist yet."""
        if not os.path.exists(self._name_db):
            maker = cdb.cdbmake(self._name_db, self._name_db + '.tmp')
            maker.finish()

    def _get_item_id(self, itemname):
        """Get ID of item (or None if no such item exists)"""
        c = cdb.init(self._name_db)
        return c.get(itemname.encode('utf-8'))

    def _add_item(self, item):
        """Add new Item to name-mapping and create name file."""
        m = md5.new()
        m.update("%s%s%d" % (datetime.datetime.now(), item.name.encode("utf-8"), random.randint(0, RAND_MAX)))
        item_id = m.hexdigest()
        # XXX: something shorter wanted ;)

        encoded_name = item.name.encode('utf-8')
        name_path = os.path.join(self._path, '%s.name' % item_id)

        c = cdb.init(self._name_db)
        maker = cdb.cdbmake(self._name_db + '.ndb', self._name_db + '.tmp')
        r = c.each()
        while r:
            name, id = r
            if name == encoded_name:
                maker.finish()
                os.unlink(self._name_db + '.ndb')
                raise ItemAlreadyExistsError("Destination item already exists: %s" % item.name)
            else:
                maker.add(name, id)
            r = c.each()
        maker.add(encoded_name, item_id)
        maker.finish()
        util.rename(self._name_db + '.ndb', self._name_db)

        name_file = open(name_path, mode='wb')
        name_file.write(encoded_name)
        name_file.close()
        item._id = item_id
        
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
        offs -= offs % 28
        tstamp = None
        while tstamp is None or tstamp >= timestamp and offs >= 0:
            # seek to current position
            newsfile.seek(offs)
            # read news item
            rec = newsfile.read(28)
            # decrease current position by 16 to get to previous item
            offs -= 28
            item_id, revno, tstamp = struct.unpack('!16sLQ', rec)
            try:
                inamef = open(os.path.join(self._path, '%s,name' % item_id), 'rb')
                iname = inamef.read().decode('utf-8')
                inamef.close()
            except IOError, err:
                if err.errno != errno.ENOENT:
                    raise
                # oops, no such file, item/revision removed manually?
                continue
            item = Item(self, iname)
            item._item_id = item_id
            rev = StoredRevision(item, revno, tstamp)
            yield rev

    def _addnews(self, item_id, revid, ts):
        """
        Add a news item with current timestamp and the given data.
        """
        newsfile = open(self._news, 'ab')
        newsfile.write(struct.pack('!16sLQ', item_id, revid, ts))
        newsfile.close()
