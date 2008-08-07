# -*- coding: utf-8 -*-
"""
    MoinMoin - fs17 read-only backend tests

    @copyright: 2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import os, re, tempfile, shutil

import py.test

from MoinMoin import wikiutil
from MoinMoin.storage import Item, DELETED, EDIT_LOG_MTIME
from MoinMoin.storage.backends.fs17 import FSBackend
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError

item_data = "Foo Bar"
item_name = "test_page"
item_mtime = 12345678
deleted_item_name = "deleted_page"
log = lambda *items: "\t".join(items)
items = [# name, rev, data, logline
         (item_name, 1, item_data, log(str(item_mtime * 1000000), '00000001', 'SAVE', item_name, )),
         (u"äöüßłó ąćółąńśćżź", 1, item_data, log('0')),
         (ur"name#special(characters?.\,", 1, item_data, log('0')),
         (deleted_item_name, 1, "", ""), # no rev data, no edit-log
        ]

class TestFS17Backend(object):
    """
    MoinMoin - fs17 read-only backend tests
    """

    def setup_method(self, method):
        # create backend
        self.tempdir = d = tempfile.mkdtemp('', 'moin-')
        self.backend = FSBackend(self.tempdir)
        # populate it manually because the backend is just read-only
        join = os.path.join
        for name, revno, revdata, logdata in items:
            pagedir = join(d, wikiutil.quoteWikinameFS(name))
            try:
                os.makedirs(join(pagedir, 'revisions'))
            except:
                pass
            f = file(join(pagedir, 'current'), 'w')
            f.write('%08d' % revno)
            f.close()
            if revdata:
                f = file(join(pagedir, 'revisions', '%08d' % revno), 'w')
                f.write(revdata)
                f.close()
            if logdata:
                f = file(join(pagedir, 'edit-log'), 'a')
                f.write(logdata)
                f.close()


    def teardown_method(self, method):
        # remove backend data
        #shutil.rmtree(self.tempdir)
        self.backend = None

    def test_get_item_that_doesnt_exist(self):
        py.test.raises(NoSuchItemError, self.backend.get_item, "i_do_not_exist")

    def test_has_item_that_doesnt_exist(self):
        assert not self.backend.has_item("i_do_not_exist")

    def test_get_item_that_exists(self):
        for itemdata in items:
            name = itemdata[0]
            item = self.backend.get_item(name)
            assert isinstance(item, Item)
            assert item.name == name

    def test_has_item(self):
        for itemdata in items:
            name = itemdata[0]
            exists = self.backend.has_item(name)
            assert exists

    def test_iteritems(self):
        itemlist = [item.name for item in self.backend.iteritems()]
        assert set([itemdata[0] for itemdata in items]) == set(itemlist)
        assert len(itemlist) == len(items)

    def test_rev_reading_chunks(self):
        item = self.backend.get_item(item_name)
        rev = item.get_revision(0)
        chunk = rev.read(1)
        data = ""
        while chunk != "":
            data += chunk
            chunk = rev.read(1)
        assert data == item_data

    def test_deleted_rev_reading(self):
        item = self.backend.get_item(deleted_item_name)
        rev = item.get_revision(0)
        data = rev.read()
        assert data == ""

    def test_metadata_that_doesnt_exist(self):
        item = self.backend.get_item(item_name)
        py.test.raises(KeyError, item.__getitem__, 'asdf')

    def test_metadata_not_deleted(self):
        item = self.backend.get_item(item_name)
        rev = item.get_revision(0)
        py.test.raises(KeyError, rev.__getitem__, DELETED)

    def test_metadata_deleted(self):
        item = self.backend.get_item(deleted_item_name)
        rev = item.get_revision(0)
        assert rev[DELETED] is True

    def test_metadata_mtime(self):
        item = self.backend.get_item(item_name)
        rev = item.get_revision(0)
        assert rev[EDIT_LOG_MTIME] == item_mtime

    def test_revision(self):
        item = self.backend.get_item(item_name)
        py.test.raises(NoSuchRevisionError, item.get_revision, -1)
        py.test.raises(NoSuchRevisionError, item.get_revision, 9999)

