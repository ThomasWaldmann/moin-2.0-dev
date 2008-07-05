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


    def setup_class(cls):
        cls.fake_dir = os.path.join(tempfile.gettempdir(),
                tempfile._RandomNameSequence().next())
        cls.real_dir = tempfile.mkdtemp()
        cls.non_dir = tempfile.mkstemp()[1]


    def teardown_class(cls):
        shutil.rmtree(cls.real_dir)
        os.unlink(cls.non_dir)


    def create_backend(self):
        self.test_dir = tempfile.mkdtemp()
        return MercurialBackend(self.test_dir)


    def kill_backend(self):
        shutil.rmtree(self.test_dir)


    def test_backend_init(self):
        py.test.raises(BackendError, MercurialBackend, self.fake_dir)
        py.test.raises(BackendError, MercurialBackend, self.non_dir)
        py.test.raises(BackendError, MercurialBackend, self.real_dir, create=False)

        hg_backend = MercurialBackend(self.real_dir)
        assert isinstance(hg_backend, MercurialBackend)
        py.test.raises(BackendError, MercurialBackend, self.real_dir, create=True)

