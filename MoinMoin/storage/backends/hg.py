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

    Initial implementation will use repository working copy on filesystem. 
    Concurrent edits will be always merged and any conflict handling is left to 
    higher levels (human intervention). All history will be presented as linear 
    using standard page info action (and this is possible while making above
    merge assumption).
    In this iteration attachments access will be supported using  legacy method
    _get_item_path.

    ---

    @copyright: 2007 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""

from mercurial import hg, ui, util, commands, repo, revlog
import StringIO
import tempfile
import weakref
import os

from MoinMoin.wikiutil import quoteWikinameFS, unquoteWikiname
from MoinMoin.storage import Backend, Item, StoredRevision, NewRevision
from MoinMoin.storage.error import BackendError, NoSuchItemError,\
                                   NoSuchRevisionError,\
                                   RevisionNumberMismatchError,\
                                   ItemAlreadyExistsError, RevisionAlreadyExistsError


class MercurialBackend(Backend):
    """This class implements Mercurial backend storage."""
    
    def __init__(self, path, create=True):
        """
        Init backend repository. We store here Items with or without 
        any Revision.
        """
        if not os.path.isdir(path):
            raise BackendError("Invalid repository path: %s" % path)
        
        self.repo_path = os.path.abspath(path)
        self.unrevisioned_path = os.path.join(self.repo_path, 'unrevisioned')
        self.ui = ui.ui(interactive=False, quiet=True)
        self._lockref = None
            
        try:
            try:
                self.repo = hg.repository(self.ui, self.repo_path, create=create)
                os.mkdir(self.unrevisioned_path)
            except OSError:
                if create:
                    raise repo.RepoError()

        except repo.RepoError:
            if create:
                raise BackendError("Repository at given path exists: %s" % path)
            else:
                raise BackendError("Repository at given path does not exist: %s"
                        % path)

    def has_item(self, itemname, revisioned=None):
        """Checks whether Item with given name exists."""
        quoted_name = self._quote(itemname)
        try:
            self.repo.changectx().filectx(quoted_name)
            in_repo = True
        except revlog.LookupError:
            in_repo = False
    
        if revisioned:  # search only versioned Items
            return in_repo
        else:
            return in_repo or os.path.exists(self._unrev_path(quoted_name))

    def create_item(self, itemname):
        """
        Create Item in repository. This Item hasn't got any Revisions yet. Unless
        you create_revision+commit or change_metadata+publish_metdata, Item acts 
        like a proxy for storing filled data. This method returns Item object.
        """
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Wrong Item name type: %s" % (type(itemname)))

        if self.has_item(itemname):
            raise ItemAlreadyExistsError("Item with that name already exists: %s" % itemname)
        
        return Item(self, itemname)

    def get_item(self, itemname):
        """
        Returns an Item with given name. If not found, raises NoSuchItemError
        exception.
        """
        if not self.has_item(itemname):
            raise NoSuchItemError('Item does not exist: %s' % itemname)
        
        return Item(self, itemname)

    def iteritems(self):
        """
        Returns generator for iterating through items collection 
        in repository.
        """
        ctx = self.repo.changectx()

        for itemfctx in ctx.filectxs():
            yield Item(self, itemfctx.path())

    def _create_revision(self, item, revno):
        """Create new Item Revision."""
        revs = item.list_revisions()

        if not revs:
            if revno != 0:
                raise RevisionNumberMismatchError("Unable to create revision \
                      number: %d. First Revision number must be 0." % revno)

            item._tmpfd, item._tmpfname = tempfile.mkstemp(prefix=item.name,
                    dir=self.repo_path)
        else:
            if revno in revs:
                raise RevisionAlreadyExistsError("Item Revision already exists: %s" % revno)
            if revno != revs[-1] + 1:
                raise RevisionNumberMismatchError("Unable to create revision\
                      number %d. New Revision number must be next to latest Revision number." % revno)
        
        new_rev = NewRevision(item, revno)
        new_rev._revno = revno
        new_rev._data = StringIO.StringIO()
        return new_rev

    def _get_revision(self, item, revno):
        """Returns given Revision of an Item."""

        if not isinstance(revno, int):
            raise TypeError("Wrong Revision number type: %s" % (type(revno)))

        ctx = self.repo.changectx()
        try:
            revs = item.list_revisions()
            if revno == -1 and revs:
                revno = max(revs)

            ftx = ctx.filectx(self._quote(item.name)).filectx(revno)
        except LookupError:
            raise NoSuchRevisionError("Item Revision does not exist: %s" % revno)

        revision = StoredRevision(item, revno)
        revision._data = StringIO.StringIO(ftx.data())
        # XXX: Rev meta stuff
        # revision_metadata = 

        return revision

    def _list_revisions(self, item):
        """
        Return a list of Item revision numbers. 
        Retrieves only accessible rev numbers when internal indexfile
        inconsistency occurs.
        """
        filelog = self.repo.file(self._quote(item.name))
        cl_count = self.repo.changelog.count()

        revs = []
        for i in xrange(filelog.count()):
            try:
                assert filelog.linkrev(filelog.node(i)) < cl_count, \
                    "Revision number out of bounds, repository inconsistency!"
                revs.append(i)
            except (IndexError, AssertionError):  # malformed index file
                pass  # XXX: should we log inconsistency?

        return revs

    def _has_revisions(self, item):
        """Checks wheter given Item has any revisions."""
        filelog = self.repo.file(self._quote(item.name))
        return filelog.count()

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
        if not self.has_item(item.name):
            raise NoSuchItemError('Source item does not exist: %s' % item.name)
        
        lock = self._lock()
        try:
            if self.has_item(newname):
                raise ItemAlreadyExistsError("Destination item already exists: %s" % newname)
                
            old_quoted, new_quoted = self._quote(item.name), self._quote(newname)

            if not self._has_revisions(item):
                util.rename(self._unrev_path(old_quoted), self._unrev_path(new_quoted))
            else:
                commands.rename(self.ui, self.repo, self._path(old_quoted), self._path(new_quoted))
                msg = "Renamed %s to: %s" % (item.name.encode('utf-8'), newname.encode('utf-8'))
                self.repo.commit(text=msg, user="wiki", files=[old_quoted, new_quoted])
        
            item._name = newname
        finally:
            del lock
                
    def _commit_item(self, item):
        """Commit Item changes within transaction (Revision) to repository."""
        revision = item._uncommitted_revision
        quoted_name = self._quote(item.name)

        lock = self._lock()
        try:
            if not self.has_item(item.name, revisioned=True):
                os.write(item._tmpfd, revision._data.getvalue())
                os.close(item._tmpfd)
                util.rename(item._tmpfname, self._path(quoted_name))
                self.repo.add([quoted_name])
                msg = "Created item: %s" % item.name.encode('utf-8')
            else:
                if revision.revno == 0:
                    raise ItemAlreadyExistsError("Item already exists: %s" % item.name)
                elif revision.revno in item.list_revisions():
                    raise RevisionAlreadyExistsError("Revision already exists: %d" % revno)
                else:
                    revision._data.seek(0)
                    
                    fd, fname = tempfile.mkstemp(prefix=item.name, dir=self.repo_path)
                    os.write(fd, revision._data.getvalue())
                    os.close(fd)
                    util.rename(self._path(fname), self._path(quoted_name))
                    msg = "Revision commited: %d" % revision.revno

                    # XXX: Rev meta stuff?
                    # if revision._metadata:
                    #   revision._metadata.copy()   

            self.repo.commit(text=msg, user='wiki', files=[quoted_name])
        finally:
            del lock
            item._uncommitted_revision = None

    def _rollback_item(self, item):
        """Reverts uncommited Item changes."""
        try:
            os.unlink(self._path(item._tmpfname))
        except (AttributeError, OSError):
            pass

        item._uncommitted_revision = None

    def _lock(self):
        """
        Acquire internal lock. This method is helper for achieving one item
        commits.
        """
        if self._lockref and self._lockref():
            return self._lockref()
        lock = self.repo._lock(os.path.join(self.repo_path, 'wikilock'), True, None,
                None, '')
        self._lockref = weakref.ref(lock)
        return lock

    def _path(self, fname):
        """Return absolute path to revisioned Item in repository."""
        return os.path.join(self.repo_path, fname)

    def _unrev_path(self, fname):
        """Return absolute path to unrevisioned Item in repository."""
        return os.path.join(self.unrevisioned_path, fname)

    def _quote(self, name):
        """Return safely quoted name."""
        if not isinstance(name, unicode):
            name = unicode(name, 'utf-8')
        return quoteWikinameFS(name)

    def _unquote(self, quoted_name):
        """Return unquoted, real name."""
        return unquoteWikiname(quoted_name)

