# -*- coding: utf-8 -*- 
"""
    MoinMoin - Test - MercurialBackend

    Rather ugly but usable tests for Mercurialbackend

    ---

    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.storage._tests.test_backends import BackendTest, \
    default_items as di
from MoinMoin.storage.backends.hg import MercurialBackend
from MoinMoin.storage.error import BackendError
from mercurial import hg, ui
import tempfile
import shutil
import os
import py



test_dir = None

#def setup_module(module):
def prepare_repository():
    """
    Prepare backend repository.
    """
    global test_dir 
    test_dir = tempfile.mkdtemp()    
    repo = hg.repository(ui.ui(interactive=False, quiet=True), test_dir, create=True)
   
    for name in di.keys():
        for rev in xrange(len(di[name])):
            repo.wwrite(name, di[name][rev][2], '')
            if rev == 0:
                repo.add([name])
            repo.commit(text='init')

        #XXX: meta?


def teardown_module(module):
    """
    Delete created test files.
    """
    global test_dir
    shutil.rmtree(test_dir)
    test_dir = None

class TestMercurialBackend(BackendTest):
    """
    MercurialBackend test class. 
    """
    def __init__(cls):
        pass
        #XXX: need setup_module before init
        prepare_repository()

        cls.backend = MercurialBackend(test_dir, create=False)
        BackendTest.__init__(cls, cls.backend)


    def setup_class(cls):
        cls.fake_dir = os.path.join(tempfile.gettempdir(),
                tempfile._RandomNameSequence().next())
        cls.real_dir = tempfile.mkdtemp()
        cls.non_dir = tempfile.mkstemp()[1]


    def teardown_class(cls):
        shutil.rmtree(cls.real_dir)
        os.unlink(cls.non_dir)


    def test_backend_init(cls):
        py.test.raises(BackendError, MercurialBackend, cls.fake_dir)        
        py.test.raises(BackendError, MercurialBackend, cls.non_dir)        
        py.test.raises(BackendError, MercurialBackend, cls.real_dir, create=False)

        mb = MercurialBackend(cls.real_dir)   
        assert isinstance(mb, MercurialBackend)
        py.test.raises(BackendError, MercurialBackend, cls.real_dir, create=True)


