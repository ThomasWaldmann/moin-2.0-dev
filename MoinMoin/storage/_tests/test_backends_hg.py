# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - MercurialBackend

    Testcases specific only for MercurialBackend.
    Common backend API tests are defined in test_backends.py
    
    ---

    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""

import py.test
import tempfile
import shutil
import os

from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.hg import MercurialBackend
from MoinMoin.storage.error import BackendError

class TestMercurialBackend(BackendTest):
    """MercurialBackend test class."""
    def __init__(self):
        self.backend = None
        BackendTest.__init__(self, self.backend)
        
    def setup_class(cls):
        cls.not_dir = tempfile.mkstemp()[1]
        cls.empty_dir = tempfile.mkdtemp()        
        cls.empty_struct = tempfile.mkdtemp()         
        os.mkdir(os.path.join(cls.empty_struct, "unversioned"))        
        cls.data_struct = tempfile.mkdtemp()
        path = os.path.join(cls.data_struct, "unversioned")
        os.mkdir(path)
        f = open(os.path.join(path, "dataitem"), "w")
        f.close()
                
    def teardown_class(cls):
        shutil.rmtree(cls.empty_dir)
        shutil.rmtree(cls.empty_struct)
        shutil.rmtree(cls.data_struct)
        os.unlink(cls.non_dir)

    def create_backend(self):
        self.test_dir = tempfile.mkdtemp()
        return MercurialBackend(self.test_dir)

    def kill_backend(self):
        shutil.rmtree(self.test_dir)

    def test_backend_init(self):
        py.test.raises(BackendError, MercurialBackend, self.empty_dir, create=False)
        py.test.raises(BackendError, MercurialBackend, self.not_dir)
        py.test.raises(BackendError, MercurialBackend, "non-existing-dir")        
        assert isinstance(MercurialBackend(self.empty_dir), MercurialBackend)
        py.test.raises(BackendError, MercurialBackend, self.empty_dir)        
        py.test.raises(BackendError, MercurialBackend, self.data_struct)
        assert isinstance(MercurialBackend(self.empty_struct), MercurialBackend)

