# -*- coding: utf-8 -*-
"""
    MoinMoin - TestBackend

    Simple test class for subclassing in specific backend tests.
    Remember to set up your backend environment with items: either
    default provided here or yours.

    ---

    @copyright: 2008 MoinMoin:PawelPacana
    @copyright: 2008 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import py

from MoinMoin.storage import Backend, Item, Revision, NewRevision
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, \
    ItemAlreadyExistsError, RevisionAlreadyExistsError, \
    RevisionNumberMismatchError

default_items = {
    'NewPage': [
        ('0', {}, "This is NewPage content. A to jest też zawartość."),
        ('1', {}, "Dummy message"),
    ],
    'Test': [
        ('0', {}, "First of all, people don't wear enough hats!"),
        ('1', {}, "Soft\ncushions."),
    ],
}

class BackendTest(object):
    """ Generic class for backend tests. """

    def __init__(self, backend, items=None):
        self.backend = backend
        self.items = items or default_items

    def test_create_item(self):
        for item_name in ("my_item", u"äöüß", "with space"):
            yield self.create_item, item_name

    def create_item(self, name):
        new_item = self.backend.create_item(name)
        assert isinstance(new_item, Item)
        assert new_item.name == name

    def test_create_item_wrong_itemname(self):
        # XXX More invalid names needed
        py.test.raises(TypeError, self.backend.create_item, 42)

    def test_create_item_again(self):
        item1 = self.backend.create_item("item1")
        py.test.raises(ItemAlreadyExistsError, self.backend.create_item, "item1")

    def test_get_item(self):
        for item in self.items.keys():
            yield self.get_item, item

    def get_item(self, name):
        my_item = self.backend.get_item(name)
        assert isinstance(my_item, Item)
        assert my_item.name == self.name

    def test_get_item_that_doesnt_exist(self):
        py.test.raises(NoSuchItemError, self.backend.get_item, "i_do_not_exist")

    def test_has_item(self):
        item = self.backend.create_item("yep")
        assert self.backend.has_item("yep")

    def test_has_item_that_doesnt_exist(self):
        assert not self.backend.has_item("i_do_not_exist")

    def test_item_create_revision(self):
        item = self.backend.create_item('internal')
        rev = item.create_revision(0)
        assert isinstance(rev, NewRevision)

    def test_item_commit_revision(self):
        item = self.backend.create_item("item#11")
        rev = item.create_revision(0)
        rev.write("python rocks")
        item.commit()
        rev = item.get_revision(0)
        assert rev.read() == "python rocks"

    def test_item_writing_data_multiple_times(self):
        item = self.backend.create_item("multiple")
        rev = item.create_revision(0)
        rev.write("Alle ")
        rev.write("meine ")
        rev.write("Entchen")
        item.commit()
        rev = item.get_revision(0)
        assert rev.read() == "Alle meine Entchen"

    def test_item_reading_chunks(self):
        item = self.backend.create_item("slices")
        rev = item.create_revision(0)
        rev.write("Alle meine Entchen")
        item.commit()
        rev = item.get_revision(0)
        chunk = rev.read(1)
        data = ""
        while chunk != "":
            data += chunk
            chunk = rev.read(1)
        assert data == "Alle meine Entchen"

    def test_item_get_revision(self):
        item = self.backend.create_item("item#12")
        rev = item.create_revision(0)
        rev.write("jefferson airplane rocks")
        item.commit()
        another_rev = item.get_revision(0)
        assert another_rev.read() == "jefferson airplane rocks"

    def test_item_list_revisions(self):
        item = self.backend.create_item("item#13")
        for revno in range(0, 10):
            rev = item.create_revision(revno)
            item.commit()
        assert item.list_revisions() == range(0, 10)

    def test_item_rename(self):
        ugly_item = self.backend.create_item("hans_wurst")
        ugly_item.rename("Arthur_Schopenhauer")
        assert ugly_item.name == "Arthur_Schopenhauer"
        assert self.backend.has_item("Arthur_Schopenhauer")
        assert not self.backend.has_item("hans_wurst")

    def test_item_rename_unicode(self):
        ugly_item = self.backend.create_item(u"hans_würstchen")
        ugly_item.rename(u"äöüßüöä")
        assert ugly_item.name == u"äöüßüöä"
        assert self.backend.has_item(u"äöüßüöä")
        assert not self.backend.has_item(u"hans_würstchen")

    #XXX: completely missing tests for revision and newrevision
