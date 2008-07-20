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
from os.path import join
import py.test
import shutil
import os

from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.hg import MercurialBackend
from MoinMoin.storage.error import BackendError #, ItemAlreadyExistsError
from MoinMoin.storage._tests.test_backends import item_names

class TestMercurialBackend(BackendTest):
    """MercurialBackend test class."""
    def __init__(self):
        names = item_names + (u'_ĄółóĄ_',) # tricky for internal hg quoting
        BackendTest.__init__(self, None, valid_names=names)

    def create_backend(self):
        self.file = mkstemp()[1]        
        self.empty_dir = mkdtemp()        
        self.empty_struct = mkdtemp()         
        os.mkdir(join(self.empty_struct, "unversioned"))        
        self.data_struct = mkdtemp()
        path = join(self.data_struct, "unversioned")
        os.mkdir(path)
        f = open(join(path, "dataitem"), "w")
        f.close()    
        self.test_dir = mkdtemp()
        return MercurialBackend(self.test_dir)

    def kill_backend(self):
        shutil.rmtree(self.empty_dir)
        shutil.rmtree(self.empty_struct)
        shutil.rmtree(self.data_struct)
        shutil.rmtree(self.test_dir)
        os.unlink(self.file)

    def test_backend_init(self):
        py.test.raises(BackendError, MercurialBackend, self.empty_dir, create=False)
        py.test.raises(BackendError, MercurialBackend, self.file)
        py.test.raises(BackendError, MercurialBackend, "non-existing-dir")        
        assert isinstance(MercurialBackend(self.empty_dir), MercurialBackend)
        py.test.raises(BackendError, MercurialBackend, self.empty_dir)        
        py.test.raises(BackendError, MercurialBackend, self.data_struct)
        assert isinstance(MercurialBackend(self.empty_struct), MercurialBackend)
        
    # XXX: to be removed when finally hanging    
    def test_item_metadata_multiple_change_existing(self):
        name = "foo"
        self.create_meta_item_helper(name)        
        item1 = self.backend.get_item(name)
        item2 = self.backend.get_item(name)
        item1.change_metadata()
        item2.change_metadata() # should hang on lock, does it?
        assert False
        
    def test_large(self):
        i = self.backend.create_item('large')
        r = i.create_revision(0)
        r['0'] = 'x' * 100
        r['1'] = 'y' * 200
        r['2'] = 'z' * 300
        for x in xrange(1000):
            r.write('lalala! ' * 10)
        i.commit()

        i = self.backend.get_item('large')
        r = i.get_revision(0)
        assert r['0'] == 'x' * 100
        assert r['1'] == 'y' * 200
        assert r['2'] == 'z' * 300
        for x in xrange(1000):
            assert r.read(8 * 10) == 'lalala! ' * 10
        assert r.read() == ''

    def test_all_unlocked(self):
        i1 = self.backend.create_item('existing now 1')
        i1.create_revision(0)
        i1.commit()
        i2 = self.backend.get_item('existing now 1')
        i2.change_metadata()
        # if we leave out the latter line, it fails
        i2.publish_metadata()

    def test_change_meta(self):
        item = self.backend.create_item('existing now 2')
        item.change_metadata()
        item.publish_metadata()
        item = self.backend.get_item('existing now 2')
        item.change_metadata()
        item['asdf'] = 'b'
        # if we leave out the latter line, it fails
        item.publish_metadata()
        item = self.backend.get_item('existing now 2')
        assert item['asdf'] == 'b'
 
 

        
