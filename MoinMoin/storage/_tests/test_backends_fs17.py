# -*- coding: utf-8 -*-
"""
    MoinMoin - fs17 read-only backend tests

    @copyright: 2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import os, re, tempfile, shutil

import py.test

from MoinMoin import wikiutil
from MoinMoin.storage import Item, DELETED
from MoinMoin.storage.backends.fs17 import FSPageBackend
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError

item_data = "Foo Bar"
item_name = "test_page"
item_mtime = 12345678
item_comment = "saved test item"
item_revisions = 2

deleted_item_data = "#acl All:\r\nFoo bar"
deleted_item_name = "deleted_page"

attachment_name = u"test.txt"
attachment_data = "attachment"
attachment_mtime = 12340000
attachment_comment = "saved test attachment"

logentry = lambda *items: "\t".join(items)
item_editlog = "\r\n".join([
    logentry(str(item_mtime * 1000000), '00000001', 'SAVE', item_name, '', '', '', '', item_comment),
    logentry(str(attachment_mtime * 1000000), '99999999', 'ATTNEW', item_name, '', '', '', attachment_name, attachment_comment),
    logentry(str(item_mtime * 1000000 + 1), '00000002', 'SAVE', item_name, '', '', '', '', item_comment),
])

deleted_item_editlog = "\r\n".join([
    logentry(str(item_mtime * 1000000), '00000001', 'SAVE', item_name, '', '', '', '', item_comment),
    logentry(str(item_mtime * 1000000 + 1), '00000002', 'SAVE/DELETE', item_name, '', '', '', '', item_comment),
])

items = [# name, rev, data, logline, attachments
         (item_name, 1, item_data, item_editlog, [attachment_name]),
         (item_name, 2, item_data, item_editlog, []),
         (u"äöüßłó ąćółąńśćżź", 1, item_data, '', []),
         (ur"name#special(characters?.\,", 1, item_data, '', []),
         (deleted_item_name, 1, deleted_item_data, '', []),
         (deleted_item_name, 2, '', '', []), # no rev 2 data, no edit-log
        ]

class TestFS17Backend(object):
    """
    MoinMoin - fs17 read-only backend tests
    """

    def setup_method(self, method):
        # create backend
        self.tempdir = d = tempfile.mkdtemp('', 'moin-')
        self.backend = FSPageBackend(self.tempdir)
        # populate it manually because the backend is just read-only
        join = os.path.join
        for name, revno, revdata, logdata, attachments in items:
            pagedir = join(d, 'pages', wikiutil.quoteWikinameFS(name))
            try:
                os.makedirs(join(pagedir, 'revisions'))
                os.makedirs(join(pagedir, 'attachments'))
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
            for attachment in attachments:
                f = file(join(pagedir, 'attachments', attachment.encode('utf-8')), 'w')
                f.write(attachment_data)
                f.close()

    def teardown_method(self, method):
        # remove backend data
        shutil.rmtree(self.tempdir)
        self.backend = None

    def test_get_item_that_doesnt_exist(self):
        py.test.raises(NoSuchItemError, self.backend.get_item, "i_do_not_exist")
        py.test.raises(NoSuchItemError, self.backend.get_item, item_name + "/not_exist.txt")

    def test_has_item_that_doesnt_exist(self):
        assert not self.backend.has_item("i_do_not_exist")
        assert not self.backend.has_item(item_name + "/not_exist.txt")

    def test_get_item_that_exists(self):
        for itemdata in items:
            name = itemdata[0]
            item = self.backend.get_item(name)
            assert isinstance(item, Item)
            assert item.name == name

    def test_get_item_attachment(self):
        name = item_name + '/' + attachment_name
        item = self.backend.get_item(name)
        assert isinstance(item, Item)
        assert item.name == name

    def test_has_item(self):
        for itemdata in items:
            name = itemdata[0]
            exists = self.backend.has_item(name)
            assert exists

    def test_iteritems(self):
        have_items = set([item.name for item in self.backend.iteritems()])
        expected_items = set()
        for itemdata in items:
            itemname = itemdata[0]
            attachments = itemdata[4]
            expected_items |= set([itemname] + ['%s/%s' % (itemname, att) for att in attachments])
        assert have_items == expected_items

    def test_rev_reading_chunks(self):
        item = self.backend.get_item(item_name)
        rev = item.get_revision(0)
        chunk = rev.read(1)
        data = ""
        while chunk != "":
            data += chunk
            chunk = rev.read(1)
        assert data == item_data

    def test_rev_reading_attachment(self):
        name = item_name + '/' + attachment_name
        item = self.backend.get_item(name)
        rev = item.get_revision(0)
        data = rev.read()
        assert data == attachment_data

    def test_deleted_rev_reading(self):
        item = self.backend.get_item(deleted_item_name)
        rev = item.get_revision(0)
        data = rev.read()
        assert data != ""
        rev = item.get_revision(1)
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
        rev = item.get_revision(1)
        assert rev[DELETED] is True
        assert rev['acl'] == "All:" # fs17 backend gets this from rev N-1

    def test_metadata_mtime(self):
        item = self.backend.get_item(item_name)
        rev = item.get_revision(0)
        assert rev.timestamp == item_mtime

    def test_metadata_mtime_attachment(self):
        name = item_name + '/' + attachment_name
        item = self.backend.get_item(name)
        rev = item.get_revision(0)
        assert rev.timestamp == attachment_mtime

    def test_item_revision_count(self):
        item = self.backend.get_item(item_name)
        revs = item.list_revisions()
        assert revs == range(item_revisions)

    def test_revision_that_doesnt_exist(self):
        item = self.backend.get_item(item_name)
        py.test.raises(NoSuchRevisionError, item.get_revision, 42)

    def test_revision_attachment_that_doesnt_exist(self):
        name = item_name + '/' + attachment_name
        item = self.backend.get_item(name)
        py.test.raises(NoSuchRevisionError, item.get_revision, 1) # attachment only has rev 0


