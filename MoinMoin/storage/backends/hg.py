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

from MoinMoin.storage import Backend, Item, Revision, NewRevision
from mercurial import hg, ui, util, commands

from MoinMoin.storage.error import BackendError, NoSuchItemError, NoSuchRevisionError
from mercurial.repo import RepoError
from mercurial.revlog import LookupError

import weakref
import tempfile
import os

class MercurialBackend(Backend):
    """
    This class implements Mercurial backend storage.
    """
    
    def __init__(self, path, existing=False):
        """
        Init repository.
        """
        self.ui = ui.ui(interactive=False, quiet=True)

        if not os.path.isdir(path):
            raise BackendError("Invalid repository path!")
        else:
            self.path = os.path.abspath(path)

        if existing:
            try:
                self.repo = hg.repository(self.ui, self.path, create=False)
            except RepoError:
                raise BackendError("No repository at given path!")
        else:
            try:
                self.repo = hg.repository(self.ui, self.path)
            except RepoError:
                self.repo = hg.repository(self.ui, self.path, create=True)

        self._lockref = None


    def create_item(self, itemname):
        """
        Create revisioned item in repository. Returns Item object.
        """
        lock = self._lock() # one commit per item

        if not os.path.exists(self._path(itemname)):
            file = open(self._path(itemname), 'w')
        else:
            raise BackendError, "Item exists: %s" % itemname
        
        try:
            self.repo.add([itemname])
        
        finally:
            del lock

        return Item(self, itemname)


    def get_item(self, itemname):
        """
        Returns an Item with given name. If not found, raises NoSuchItemError
        exception.
        """        
        try:
            self.repo.changectx().filectx(itemname)
        except LookupError:
            raise NoSuchItemError, 'Item does not exist: %s' % itemname
            

        return Item(self, itemname)


    def iteritems(self):
        """
        Returns generator for iterating through items collection in repository.
        """
        ctx = self.repo.changectx()
        for itemfctx in ctx.filectxs():
            yield Item(self, itemfctx.path()) 


    def _get_revision(self, item, revno):
        """
        Returns given Revision of an Item.
        """
        ctx = self.repo.changectx()

        try:
            ftx = ctx.filectx(item._name).filectx(revno)
        except LookupError:
            raise NoSuchRevisionError, "Revision does not exist: %s" % revno

        #XXX: fix on Revision class defined
        return Revision()


    def _list_revisions(self, item):
        """
        Return a list of Item revision numbers. 
        Retrieves only accessible rev numbers when internal indexfile
        inconsistency occurs.
        """
        filelog = self.repo.file(item._name)
        cl_count = self.repo.changelog.count()

        revs = []
        for i in xrange(filelog.count()):
            try:
                assert filelog.linkrev(filelog.node(i)) < cl_count, \
                    "Revision number out of bounds, repository inconsistency!"
                revs.append(i)

            except (IndexError, AssertionError):  # malformed index file
                pass
                #XXX: should we log inconsistency?

        revs.reverse()
        return revs


    def _rename_item(self, item, newname):
        """
        Renames given Item to newname and commits changes. Raises
        NoSuchItemError if source item is unreachable or BackendError
        if destination exists. Note that this method commits change itself.
        """
        try:
            self.repo.changectx().filectx(item._name)
        except LookupError:
            raise NoSuchItemError, 'Source item does not exist: %s' % item._name
        
        lock = self._lock()
        
        try:
            if os.path.exists(self._path(newname)):
                raise BackendError, "Destination item already exists: %s" % newname
            
            commands.rename(self.ui, self.repo, self._path(item._name),
                    self._path(newname))            

        finally:
            del lock
                

    def _commit_item(self, item):
        """
        Commit Item changes to repository.
        """
        items = [item._name]
        
        lock = self._lock()               
        status = self.repo.status(files=items)

        if status[2]: # removes
            items.extend(self._find_copy_destination(item._name))
            
            if len(items) == 2:
                msg = "Renamed item %s to: %s" % (items[0], items[1])

            else:
                msg = "Removed item: %s" % item._name

        elif status[1]: # adds
            msg = "Created item: %s" % item._name

        elif status[0]: # modifications
            msg = "Modified item %s" % item._name

        try:
            #XXX: message, user from upper layer
            self.repo.commit(text=msg, user='wiki', files=items)
    
        finally:
            del lock


    def _rollback_item(self, item):
        """
        Reverts uncommited Item changes.
        """
        items = [item._name]

        lock = self._lock()

        try:            
            items = self._find_copy_destination(item._name)

            commands.revert(self.ui, self.repo, self._path( items[0] ),
                date=None, rev=None, all=None, no_backup=True)
        
            for itemname in self.repo.status(files=items)[4]:
                os.unlink(self._path(itemname))

        finally:
            del lock


    def _find_copy_destination(self, srcname):
        """
        Searches repository for copy of source Item and returns list with 
        destination name if found. Else returns empty list.
        """
        status = self.repo.status(files=[srcname])

        for dst, src in self.repo.dirstate.copies().iteritems(): 
            if src in status[2]:
                return [dst]
        return []


    def _lock(self):
        """
        Acquire internal lock. This method is helper for achieving one item
        commits.
        """
        if self._lockref and self._lockref():
            return self._lockref()
        lock = self.repo._lock(os.path.join(self.path, 'wikilock'), True, None,
                None, '')
        self._lockref = weakref.ref(lock)

        return lock


    def _path(self, fname):
        """
        Return absolute path to item in repository.
        """
        return os.path.join(self.path, fname)

