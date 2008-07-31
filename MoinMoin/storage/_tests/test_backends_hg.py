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
            nameitem = mkstemp(dir=datadir)[1]
            py.test.raises(BackendError, MercurialBackend, datadir)            
            os.unlink(nameitem)
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
   