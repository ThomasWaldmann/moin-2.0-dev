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
#import statvfs
import shutil
import random
import datetime
import md5
import os
import errno

try:
    import cdb
except ImportError:
    from MoinMoin.support import pycdb as cdb
    
from MoinMoin.wikiutil import quoteWikinameFS, unquoteWikiname
from MoinMoin.storage import Backend, Item, StoredRevision, NewRevision
from MoinMoin.storage.error import BackendError, NoSuchItemError,\
                                   NoSuchRevisionError,\
                                   RevisionNumberMismatchError,\
                                   ItemAlreadyExistsError, RevisionAlreadyExistsError
from MoinMoin import log
logging = log.getLogger("MercurialBackend")
                                                                      
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
#    def has_item(self, itemname):
#        """Check whether Item with given name exists."""
#        name = self._quote(itemname)
#        return name in self._tipctx() or self._has_meta(itemname)
#                                                                               
    
    def has_item(self, itemname):
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
        c = cdb.init(self._name_db)
        r = c.each()
        while r:
            item = Item(self, r[0])
            item._id = r[1]
            yield item
            r = c.each()

#                                                                               
#    def iteritems(self):
#        """
#        Return generator for iterating through items collection
#        in repository.
#        """
#        itemlist = [name for name in iter(self._tipctx())] + os.listdir(self._u_path)
#        for itemname in itemlist:
#            yield Item(self, itemname)
#                                                                               

    def _create_revision(self, item, revno):
        """Create new Item Revision."""
        revs = self._list_revisions(item)
        if revs:
            if revno in revs:
                raise RevisionAlreadyExistsError("Item Revision already exists: %s" % revno)
            if revno != revs[-1] + 1:
                raise RevisionNumberMismatchError("Unable to create revision number %d. \
                    New Revision number must be next to latest Revision number." % revno)
            # XXX: this check will go out as soon as merging is implemented higher ;)
            # this will also need explicitly pointing parent revision in commit
        rev = NewRevision(item, revno)
        rev._data = StringIO.StringIO()
        rev._revno = revno
        return rev

    def _get_revision(self, item, revno):
        """Returns given Revision of an Item."""
        ctx = self._repo[self._repo.changelog.tip()]                                                                                                                                                                          
        try:
            revs = self._list_revisions(item)
            if revno == -1 and revs:
                revno = max(revs)
            fctx = ctx[item._id].filectx(revno)
        except LookupError:
            raise NoSuchRevisionError("Item Revision does not exist: %s" % revno)

        revision = StoredRevision(item, revno)
        revision._data = StringIO.StringIO(fctx.data())                                                        
        
        revision._metadata = dict(((key.lstrip("_"), value) for key, value in 
                                   fctx.changectx().extra().iteritems() if key.startswith('_')))
        return revision

    def _list_revisions(self, item):
        """
        Return a list of Item revision numbers.
        Retrieves only accessible rev numbers when internal indexfile
        inconsistency occurs.
        """
        # revs = []
        #self._repo[self._repo.changelog.tip()]
        if not item._id:
            return [] 
        else:
            #return [revno for revno in xrange(len(self._repo.file(item._id)))]

            filelog = self._repo.file(item._id)
            cl_count = len(self._repo)
        
            revs = []
            for revno in xrange(len(filelog)):
                try:
                    assert filelog.linkrev(filelog.node(revno)) < cl_count        
                    revs.append(revno)        
                except (IndexError, AssertionError):  # malformed index file
                    logging.warn("Revision number out of bounds. Index file inconsistency: %s" % 
                                                                        self._rpath(filelog.indexfile))
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
#                                                                               
#        if not self.has_item(item.name):
#            raise NoSuchItemError('Source item does not exist: %s' % item.name)
#                                                                               
        lock = self._repolock()
        try:
            if self.has_item(newname):
                raise ItemAlreadyExistsError("Destination item already exists: %s" % newname)
#                     

            nn = newname.encode('utf-8')
            #npath = os.path.join(self._upath, item._id + '.name')
    
            c = cdb.init(self._name_db)
            maker = cdb.cdbmake(self._name_db + '.ndb', self._name_db + '.tmp')
            r = c.each()
            while r:
                i, v = r
                if i == nn:
                    raise ItemAlreadyExistsError("new name already exists!")
                elif v == item._id:
                    maker.add(nn, v)
                else:
                    maker.add(i, v)
                r = c.each()
            maker.finish()
            # XXXX: doesn't work on windows
            os.rename(self._name_db + '.ndb', self._name_db)
#                                                                               
#            nf = open(npath, mode='wb')
#            nf.write(nn)
#            nf.close()
#                                                                               


                                                          
#            files = [self._quote(item.name), self._quote(newname)]
#            if self._has_meta(item.name):                
#                util.rename(self._upath(files[0]), self._upath(files[1]))
#            else:
#                def getfilectx(repo, memctx, path):
#                    if path == files[1]:
#                        copies = files[0]
#                    else:
#                        copies = None
#                    return context.memfilectx(path, '', False, False, copies)
# 
#                msg = "Renamed %s to: %s" % (item.name.encode('utf-8'), newname.encode('utf-8'))
#                editor = ""  
#                # XXX: get from upper layer here
#                # this is however more complicated to achieve
#                # in normal situation like create_revision - commit
#                # we could pass this as revision metadata
#                # has_item(old_item) must be False after rename,
#                # which is true after hg rename, hg commit
#                # but produces commit too early from higher level
#                # code point of view
#                p1, p2 = self._repo.changelog.tip(), node.nullid
#                ctx = context.memctx(self._repo, (p1, p2), msg, [], getfilectx, user=editor)
#                ctx._status[2] = [files[0]]
#                ctx._status[1] = [files[1]]
#                self._repo.commitctx(ctx)
#                                                                               

            item._name = newname
        finally:
            del lock

    def _change_item_metadata(self, item):
        """Start Item metadata transaction."""
        if item._id: 
            item._lock = self._itemlock(item)

    def _publish_item_metadata(self, item):
        """Dump Item metadata to file and finish transaction."""
        #meta_item_path = self._upath(self._quote(item.name))
        
        def write_meta_item(itempath, metadata):
            tmpfd, tmpfpath = tempfile.mkstemp("-meta", "tmp-", self._u_path)
            f = os.fdopen(tmpfd, 'wb')
            pickle.dump(item._metadata, f, protocol=PICKLEPROTOCOL)
            f.close()
            util.rename(tmpfpath, itempath)   
                 
        if item._id:
            if item._metadata is None:
                pass               
            else:
                write_meta_item(self._upath("%s.meta" % item._id), item._metadata)               
            del item._lock
        else:
            self._add_item_internally(item)
            #if self.has_item(item.name):
            #    raise ItemAlreadyExistsError("Item already exists: %s" % item.name)
                # TODO: this is a bit misleading
                # first - its used on concurrent creates when
                # no locks are involved yet, to fail latter publish
                # whats worse - its also used to prevent mixed commit/publish
                # see test_item_create_existing_mixed_2
                # thus it has to check has_item not only has_meta
                # but is completely harmless if item exists
                # this should be simplified sometime, however tests
                # are passing and there are more important things to do by now  
            if item._metadata is None:
                item._metadata = {}
            write_meta_item(self._upath("%s.meta" % item._id), item._metadata)       

    def _get_item_metadata(self, item):
        """Load Item metadata from file. Return dictionary."""
        #quoted_name = self._quote(item.name)
        if item._id:            
            try:
                f = open(self._upath(item._id + ".meta"), "rb")
                item._metadata = pickle.load(f)
                f.close()
            except IOError, err:
                if err.errno != errno.ENOENT:
                    raise
                # no such file means no metadata was stored
                item._metadata = {}            
        else:
            item._metadata = {}
        return item._metadata

    def _commit_item(self, item):
        """Commit Item changes within transaction (Revision) to repository."""
        rev = item._uncommitted_revision                
        if not item._id and self.has_item(item.name):
            raise ItemAlreadyExistsError("Item already exists: %s" % item.name)
        # XXX: XXX
               
        meta = dict(("_%s" % key, value) for key, value in rev.iteritems())
        #name = self._quote(item.name)
        lock = self._repolock()
        try:
            def getfilectx(repo, memctx, path):
                return context.memfilectx(path, data, False, False, False)
            
            if not item._id:
                self._add_item_internally(item) 
                                    
            msg = meta.get("comment", "")
            user = meta.get("editor", "anonymous")  # XXX: meta keys spec
            data = rev._data.getvalue()
            fname = [item._id]
            p1, p2 = self._repo.changelog.tip(), node.nullid
            # TODO: check this parents on merging task
            ctx = context.memctx(self._repo, (p1, p2), msg, fname, getfilectx, user, extra=meta)            
            
            if not item._id:
                ctx._status[1], ctx._status[0] = ctx._status[0], ctx._status[1]                
            self._repo.commitctx(ctx)
            
            
            #item._exists = True
        finally:
            del lock
            item._uncommitted_revision = None  # XXX: move to abstract

    def _rollback_item(self, item):
        """Reverts uncommited Item changes."""
        item._uncommitted_revision = None  # XXX: move to abstract

#                                                                               
#    def _trim(self, name):
#        """Trim given name to fit in maximum supported length on filesystem."""
#        # see http://www.moinmo.in/PawelPacana/MercurialBackend#Mercurialbehaviour
#        if len(name) > ((self._max_fname_length - 2) // 2):
#            m = md5.new()
#            m.update(name)
#            hashed = m.hexdigest()
#            return "%s-%s" % (name[:(self._max_fname_length - len(hashed) - 3) // 2], hashed)
#        else:
#            return name
#                                                                               

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
        lpath = self._upath(item._id + ".lock")
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

#                                                                               
#    def _quote(self, name):
#        """Return safely quoted name."""
#        if not isinstance(name, unicode):
#            name = unicode(name, 'utf-8')
#        return self._trim(quoteWikinameFS(name))
# 
#    def _unquote(self, quoted):
#        """Return unquoted, real name."""
#        return unquoteWikiname(quoted)

    def _get_revision_metadata(self, rev):
        ctx = self._repo[self._repo.changelog.tip()]                                                                                                                                                                          
        fctx = ctx[item._id].filectx(revno)
        return dict(((key.lstrip("_"), value) for key, value in 
                                    ctx.changectx().extra().iteritems() if key.startswith('_')))                                                                         
    
    def _namelock(self):
        """Acquire name mapping lock"""        
        return self._lock(os.path.join(self._path, "%s.lock" % self._name_db), self._name_lockref)
    
    def _create_new_cdb(self):
        """Create new name-mapping if it doesn't exist yet."""
        if not os.path.exists(self._name_db):
            maker = cdb.cdbmake(self._name_db, self._name_db + '.tmp')
            maker.finish()    
   
    def _get_item_id(self, itemname):
        """Get ID of item (or None if no such item exists)"""
        c = cdb.init(self._name_db)
        return c.get(itemname.encode('utf-8')) 
    
    def _add_item_internally(self, item):
        """
        """
#                                                                               
#        done = False
#        while not done:
#                                                                               
        m = md5.new()
        m.update("%s%s%d" % (datetime.datetime.now(), item.name.encode("utf-8"), random.randint(0, 1024)))
        item_id = m.hexdigest()
#                                                                               
#            path = self._u_path("%s.meta" % itemid)            
#            try:
#                fd = os.open(path, os.O_CREAT|os.O_EXCL)
#                done = True
#                os.close(fd)
#            except OSError, err:
#                if err.errno != errno.EEXIST:
#                    raise
#                                                                               
        nn = item.name.encode('utf-8')
        c = cdb.init(self._name_db)
        maker = cdb.cdbmake(self._name_db + '.ndb', self._name_db + '.tmp')
        r = c.each()
        while r:
            i, v = r
            if i == nn:
                # Oops. This item already exists! Clean up and error out.
                maker.finish()
                #os.unlink(self._name_db + '.ndb')
                #os.unlink(path)
                raise ItemAlreadyExistsError("new name already exists!")
            else:
                maker.add(i, v)
            r = c.each()
        maker.add(nn, item_id)
        maker.finish()

        # make item retrievable (by putting the name-mapping in place)
        util.rename(self._name_db + '.ndb', self._name_db)

        item._id = item_id 
        # po co?

