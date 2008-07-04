# -*- coding: utf-8 -*- 
"""
    MoinMoin - Test - FSBackend


    @copyright: 2008 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

import py, os, tempfile, shutil

from MoinMoin.storage.error import ItemAlreadyExistsError
from MoinMoin.storage._tests.test_backends import BackendTest, default_items
from MoinMoin.storage.backends.fs import FSBackend

class TestFSBackend(BackendTest):
    def setup_method(self, method):
        self.tempdir = tempfile.mkdtemp('', 'moin-')
        self.backend = FSBackend(self.tempdir, nfs=True)
        for iname in self.items:
            item = self.backend.create_item(iname)
            for revnostr, meta, revdata in self.items[iname]:
                rev = item.create_revision(int(revnostr))
                for k, v in meta.iteritems():
                    rev[k] = v
                rev.write(revdata.encode('utf-8'))
                item.commit()

    def teardown_method(self, method):
        shutil.rmtree(self.tempdir)

    def __init__(self):
        BackendTest.__init__(self, None)

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

    def test_metadata(self):
        i = self.backend.create_item('no metadata')
        i.create_revision(0)
        i.commit()
        i = self.backend.get_item('no metadata')
        py.test.raises(KeyError, i.__getitem__, 'asdf')

    def test_create_existing_1(self):
        i = self.backend.create_item('existing now')
        i.change_metadata()
        i.publish_metadata()
        py.test.raises(ItemAlreadyExistsError, self.backend.create_item, 'existing now')

    def test_create_existing_2(self):
        i1 = self.backend.create_item('existing now')
        i1.change_metadata()
        i2 = self.backend.create_item('existing now')
        i1.publish_metadata()
        i2.create_revision(0)
        py.test.raises(ItemAlreadyExistsError, i2.commit)
