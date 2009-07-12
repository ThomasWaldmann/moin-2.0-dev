# -*- coding: utf-8 -*-
"""
    MoinMoin - MercurialBackend tests

    Testcases specific only for MercurialBackend.
    Common backend API tests are defined in test_backends.py

    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""

import py.test
py.test.skip("Broken, please fix.")

from tempfile import mkdtemp, mkstemp, gettempdir
import shutil
import os

from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.hg import MercurialBackend
from MoinMoin.storage.error import BackendError
from MoinMoin.storage._tests.test_backends import item_names

class TestMercurialBackend(BackendTest):
    """MercurialBackend test class."""
    try:
        from mercurial.context import memctx
    except ImportError:
        py.test.skip("Wrong version of mercurial: please test on development version.")

    def __init__(self):
        names = item_names + (u'_ĄółóĄ_', )
        BackendTest.__init__(self, None, valid_names=names)

    def create_backend(self):
        self.test_dir = mkdtemp()
        return MercurialBackend(self.test_dir)

    def kill_backend(self):
        shutil.rmtree(self.test_dir)

    def test_backend_init(self):
        emptydir, file = mkdtemp(), mkstemp()[1]
        nonexisting = os.path.join(gettempdir(), 'to-be-created')
        dirstruct = mkdtemp()
        os.mkdir(os.path.join(dirstruct, "meta"))
        os.mkdir(os.path.join(dirstruct, "rev"))
        try:
            assert isinstance(MercurialBackend(nonexisting), MercurialBackend)
            assert isinstance(MercurialBackend(emptydir), MercurialBackend)
            assert isinstance(MercurialBackend(emptydir), MercurialBackend) # init on existing
            py.test.raises(BackendError, MercurialBackend, file)
            assert isinstance(MercurialBackend(dirstruct), MercurialBackend)
        finally:
            shutil.rmtree(emptydir)
            shutil.rmtree(dirstruct)
            shutil.rmtree(nonexisting)
            os.unlink(file)

    def test_permission(self):
        import sys
        if sys.platform == 'win32':
            py.test.skip("Not much usable test on win32.")
        no_perms = os.path.join("/", "permission-error-dir")
        py.test.raises(BackendError, MercurialBackend, no_perms)

    def test_backend_init_non_empty_datadir(self):
        datadir = mkdtemp()
        os.mkdir(os.path.join(datadir, "meta"))
        os.mkdir(os.path.join(datadir, "rev"))
        try:
            revitem = mkstemp(dir=os.path.join(datadir, "rev"))[1]
            assert isinstance(MercurialBackend(datadir), MercurialBackend)
            os.unlink(revitem)
            metaitem = mkstemp(dir=os.path.join(datadir, "meta"))[1]
            assert isinstance(MercurialBackend(datadir), MercurialBackend)
            os.unlink(metaitem)
        finally:
            shutil.rmtree(datadir)

    def test_large_revision_meta(self):
        item = self.backend.create_item('existing')
        rev = item.create_revision(0)
        for num in xrange(10000):
            revval = "revision metatdata value for key %d" % num
            rev["%s" % num] = revval * 10
        item.commit()
        item = self.backend.get_item('existing')
        rev = item.get_revision(-1)
        assert len(dict(rev)) == 10000
        for num in xrange(10000):
            revval = "revision metatdata value for key %d" % num
            assert rev["%s" % num] == revval * 10
