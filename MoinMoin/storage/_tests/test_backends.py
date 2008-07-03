# -*- coding: utf-8 -*-
"""
    MoinMoin - TestBackend

    Simple test class for subclassing in specific backend tests.
    Rebackender to set up your backend environment with items: either
    default provided here or yours.

    ---

    @copyright: 2008 MoinMoin:PawelPacana
    @copyright: 2008 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import py

from MoinMoin.storage import Backend, Item, Revision, NewRevision
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError,\
                                   ItemAlreadyExistsError, RevisionAlreadyExistsError,\
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

default_names = ("my_item", u"äöüß", u"hans_würstchen", "with space", "name#with#hash",
                 "very_long_name_quite_safe_although_exceedind_255_chars_length_limit_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",)

default_invalid = (42,)


class BackendTest(object):
    """Generic class for backend tests."""

    def __init__(self, backend, items=None, item_names=None, invalid_names=None):
        self.backend = backend
        self.items = items or default_items
        self.item_names = item_names or default_names
        self.invalid_names = invalid_names or default_invalid

    def create_item_helper(self, name):
        item = self.backend.create_item(name)
        item.create_revision(0)
        item.commit()
        return item

    def create_item(self, name):
        new_item = self.backend.create_item(name)
        assert isinstance(new_item, Item)
        assert new_item.name == name
        new_item.create_revision(0)
        new_item.commit()
        assert self.backend.has_item(name)

    def get_item(self, name):
        my_item = self.backend.get_item(name)
        assert isinstance(my_item, Item)
        assert my_item.name == name

    def get_rename_item(self, old_name, new_name):
        item = self.backend.get_item(old_name)
        item.rename(new_name)
        assert item.name == new_name
        assert self.backend.has_item(new_name)
        assert not self.backend.has_item(old_name)

    def test_create_get_rename_get_item(self):
        for num, item_name in enumerate(self.item_names):
            yield self.create_item, item_name
            yield self.get_item, item_name
            new_name = "renamed_item_%d" % num
            yield self.get_rename_item, item_name, new_name
            yield self.get_item, new_name
    
    def create_item_invalid_name(self, name):
        py.test.raises(TypeError, self.backend.create_item, name)

    def test_create_item_wrong_itemname(self):
        for item_name in self.invalid_names:
            yield self.create_item_invalid_name, item_name

    def test_create_item_again(self):
        self.create_item_helper("item1")
        py.test.raises(ItemAlreadyExistsError, self.backend.create_item, "item1")

    def test_get_item(self):
        for item in self.items.keys():
            yield self.get_item, item

    def test_get_item_that_doesnt_exist(self):
        py.test.raises(NoSuchItemError, self.backend.get_item, "i_do_not_exist")

    def test_has_item(self):
        self.create_item_helper("yep")
        assert self.backend.has_item("yep")

    def test_has_item_that_doesnt_exist(self):
        assert not self.backend.has_item("i_do_not_exist")

    def test_create_order(self):
        i1 = self.backend.create_item('1')
        i2 = self.backend.create_item('2')
        r1 = i1.create_revision(0)
        r2 = i2.create_revision(0)
        r1.write('1')
        r2.write('2')
        i2.commit()
        i1.commit()
        i1 = self.backend.get_item('1')
        i2 = self.backend.get_item('2')
        r1 = i1.get_revision(0)
        r2 = i2.get_revision(0)
        assert r1.read() == '1'
        assert r2.read() == '2'

    def test_mixed_commit_metadata1(self):
        i = self.backend.create_item('mixed1')
        i.create_revision(0)
        py.test.raises(RuntimeError, i.change_metadata)

    def test_mixed_commit_metadata2(self):
        i = self.backend.create_item('mixed2')
        i.change_metadata()
        py.test.raises(RuntimeError, i.create_revision, 0)

    def test_item_metadata_change_and_publish(self):
        i = self.backend.create_item("test item metadata change")
        i.change_metadata()
        i["creator"] = "Vincent van Gogh"
        i.publish_metadata()
        i2 = self.backend.get_item("test item metadata change")
        assert i2["creator"] == "Vincent van Gogh"

    def test_item_metadata_invalid_change(self):
        i = self.backend.create_item("test item metadata invalid change")
        try:
            i["this should"] = "FAIL!"
            assert False  # There should have been an Exception due to i.change() missing.

        except AttributeError:
            pass  # We expected that Exception to be thrown. Everything fine.

    def test_item_metadata_without_publish(self):
        i = self.backend.create_item("test item metadata invalid change")
        i.change_metadata()
        i["change but"] = "don't publish"
        py.test.raises(NoSuchItemError, self.backend.get_item, "test item metadata invalid change")

    def test_item_metadata_change_after_read(self):
        i = self.backend.create_item("fooafoeofo")
        i.change_metadata()
        i["asd"] = "asd"
        i.publish_metadata()

    def test_existing_item_create_revision(self):
        item = self.backend.get_item(self.items.keys()[0])
        rev = item.create_revision(0)
        assert isinstance(rev, NewRevision)

    def test_new_item_create_revision(self):
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

    def test_item_list_existing_revisions(self):
        for itemname in self.items.keys():
            yield self.list_revisions, itemname

    def list_revisions(self, itemname):
        item = self.backend.get_item(itemname)
        assert range(len(self.items[itemname])) == item.list_revisions()

    def test_item_list_revisions(self):
        item = self.backend.create_item("item_13")
        for revno in range(0, 10):
            rev = item.create_revision(revno)
            item.commit()
        assert item.list_revisions() == range(0, 10)

    def test_item_rename_nonexisting(self):
        item = self.backend.get_item(self.items.keys()[0])
        item._name = "certainly_non_existent"
        py.test.raises(NoSuchItemError, item.rename, "whatever")

    def test_item_rename_to_existing(self):
        item = self.create_item_helper("XEROX")
        py.test.raises(ItemAlreadyExistsError, item.rename, self.items.keys()[0])

    def test_item_rename_existing_to_existing(self):
        item = self.backend.get_item(self.items.keys()[1])
        py.test.raises(ItemAlreadyExistsError, item.rename, self.items.keys()[0])

    def test_item_rename_wrong_type(self):
        item = self.backend.get_item(self.items.keys()[0])
        py.test.raises(TypeError, item.rename, 13)
