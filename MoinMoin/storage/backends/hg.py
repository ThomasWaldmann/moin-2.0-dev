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

from MoinMoin.storage.abstract import Backend, Item, Revision
from MoinMoin.search import term
from mercurial import hg, ui, util

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
        self.ui = ui.ui(interactive=False)

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
        fd, fname = tempfile.mkstemp(prefix=itemname, dir=self.path)
        
        lock = self._lock() # one commit per item

        if not os.path.exists(self._path(itemname)):
            util.rename(fname, self._path(itemname))
        else:
            os.unlink(fname)
            raise BackendError("Item with that name already exists!")

        try:
            self.repo.add([itemname])
            self.repo.commit(text="created item %s" % itemname)

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
            raise NoSuchItemError

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
            raise NoSuchRevisionError

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


    
