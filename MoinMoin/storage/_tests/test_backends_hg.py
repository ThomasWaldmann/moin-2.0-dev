# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - MercurialBackend

    Testcases specific only for MercurialBackend.
    Common backend API tests are defined in test_backends.py
    
    ---

    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""

from tempfile import mkdtemp, mkstemp
import py.test
import shutil
import os

from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.hg import MercurialBackend
from MoinMoin.storage.error import BackendError
from MoinMoin.storage._tests.test_backends import item_names

class TestMercurialBackend(BackendTest):
    """MercurialBackend test class."""
    def __init__(self):
        names = item_names + (u'_ĄółóĄ_',) # tricky for internal hg quoting
        BackendTest.__init__(self, None, valid_names=names)

    def create_backend(self):
        self.test_dir = mkdtemp()
        return MercurialBackend(self.test_dir)      
                    
    def kill_backend(self):
        shutil.rmtree(self.test_dir)        

    def test_backend_init(self):
        nonexisting = os.path.join("/", "non-existing-dir")
        py.test.raises(BackendError, MercurialBackend, nonexisting)        
        emptydir, file = mkdtemp(), mkstemp()[1]
        dirstruct = mkdtemp()         
        os.mkdir(os.path.join(dirstruct, "meta"))
        os.mkdir(os.path.join(dirstruct, "rev"))  
        try:
            py.test.raises(BackendError, MercurialBackend, emptydir, create=False)
            assert isinstance(MercurialBackend(emptydir), MercurialBackend)
            py.test.raises(BackendError, MercurialBackend, emptydir)
            assert isinstance(MercurialBackend(emptydir, create=False), MercurialBackend)
            py.test.raises(BackendError, MercurialBackend, file)
            assert isinstance(MercurialBackend(dirstruct), MercurialBackend)         
        finally:
            shutil.rmtree(emptydir)
            shutil.rmtree(dirstruct)
            os.unlink(file)             
            
    def test_backend_init_non_empty_datadir(self):
        datadir = mkdtemp()         
        os.mkdir(os.path.join(datadir, "meta"))
        os.mkdir(os.path.join(datadir, "rev"))
        try:
            revitem = mkstemp(dir=os.path.join(datadir, "rev"))[1]
            py.test.raises(BackendError, MercurialBackend, datadir)
            os.unlink(revitem)
            mkstemp(dir=os.path.join(datadir, "meta"))[1]
            py.test.raises(BackendError, MercurialBackend, datadir)
        finally:
            shutil.rmtree(datadir) 
               
    def test_large_revision_meta(self):
        item = self.backend.create_item('existing')
        rev = item.create_revision(0)
        for num in xrange(10000):
            revval = "revision metatdata value for key %d" % num
            rev["%s" % num] = revval * 100
        item.commit()
        item = self.backend.get_item('existing')
        rev = item.get_revision(-1)
        assert len(dict(rev)) == 10000
        for num in xrange(10000):
            revval = "revision metatdata value for key %d" % num
            assert rev["%s" % num] == revval * 100
   
    def test_revisions_after_rename(self):
        def create_item_with_revs(name, revnum):
            self.create_rev_item_helper(name)
            item = self.backend.get_item(name)
            for revno in xrange(1, revnum):
                item.create_revision(revno)
                item.commit()
            return item
        
        revnum = 5
        item = create_item_with_revs("A", revnum)
        assert item.list_revisions() == range(revnum)
        item.rename("B")
        # mercurial renames have to be commited unless
        # we use hashes/ids to represent Items in hg
        # and provide mapping like in FSBackend,
        # however this is not the 'right way', read below
        assert item.list_revisions() == range(revnum + 1)
        # http://www.moinmo.in/PawelPacana/MercurialBackend/HadItem
        assert self.backend.has_item("B")
        assert not self.backend.has_item("A")
        assert self.backend.had_item("A")
        assert not self.backend.had_item("B")  
        item = self.backend.get_item("A")
        revs = item.list_revisions()
        item.create_revision(max(revs) + 1)
        item.commit()
        item.create_revision(max(revs) + 2)
        item.commit()
        assert item.list_revisions() == range(revs + 2)  
