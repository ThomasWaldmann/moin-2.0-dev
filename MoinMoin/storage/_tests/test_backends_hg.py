# -*- coding: utf-8 -*- 
"""
    MoinMoin - Test - MercurialBackend

    Rather ugly but usable tests for Mercurialbackend

    ---

    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""

from mercurial import hg, ui
import tempfile
import shutil
import os
import py

from MoinMoin.storage._tests.test_backends import BackendTest, \
    default_items as di
from MoinMoin.storage.backends.hg import MercurialBackend
from MoinMoin.storage.error import BackendError


class TestMercurialBackend(BackendTest):
    """MercurialBackend test class."""    

    def __init__(self):
        self.backend = None
        BackendTest.__init__(self, self.backend)


    def prepare_repository(self, dir):
        """Prepare backend repository."""
        repo = hg.repository(ui.ui(interactive=False, quiet=True), dir, create=True)
       
        for name in di.keys():
            for rev in xrange(len(di[name])):
                repo.wwrite(name, di[name][rev][2], '')
                if rev == 0:
                    repo.add([name])
                repo.commit(text='init')

            #XXX: meta?

        return MercurialBackend(dir, create=False)


    def setup_class(cls):
        cls.fake_dir = os.path.join(tempfile.gettempdir(),
                tempfile._RandomNameSequence().next())
        cls.real_dir = tempfile.mkdtemp()
        cls.non_dir = tempfile.mkstemp()[1]


    def teardown_class(cls):
        shutil.rmtree(cls.real_dir)
        os.unlink(cls.non_dir)
           

    def setup_method(self, method):
        self.test_dir = tempfile.mkdtemp()    
        self.backend = self.prepare_repository(self.test_dir)


    def teardown_method(self, method):
        shutil.rmtree(self.test_dir)
        self.backend = None


    def test_backend_init(self):
        py.test.raises(BackendError, MercurialBackend, self.fake_dir)        
        py.test.raises(BackendError, MercurialBackend, self.non_dir)        
        py.test.raises(BackendError, MercurialBackend, self.real_dir, create=False)

        hg_backend = MercurialBackend(self.real_dir)   
        assert isinstance(hg_backend, MercurialBackend)
        py.test.raises(BackendError, MercurialBackend, self.real_dir, create=True)

