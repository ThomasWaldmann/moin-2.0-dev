"""
    MoinMoin external interfaces tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.storage._tests.test_backends_moin16 import get_page_backend, setup_module, teardown_module, items

from MoinMoin.storage.external import ItemCollection, Item, Revision
from MoinMoin.storage.error import BackendError, NoSuchItemError, NoSuchRevisionError, LockingError

# TODO: add more tests

class TestItemCollection:
    item_collection = None

    def setup_class(self):
        self.item_collection = ItemCollection(get_page_backend(), None)

    def teardown_class(self):
        self.item_collection = None

    def test_has_item(self):
        assert items[0] in self.item_collection
        assert not "asdf" in self.item_collection

    def test_keys(self):
        assert self.item_collection.keys() == items
        assert self.item_collection.keys({'format': 'wiki'}) == [items[1]]

    def test_get_item(self):
        item = self.item_collection[items[0]]
        assert isinstance(item, Item)
        assert item.name == items[0]
        assert item._backend.name == "pages"
        py.test.raises(NoSuchItemError, lambda: self.item_collection["asdf"])

    def test_new_delete_item(self):
        item = self.item_collection.new_item("1180424618.59.18120")
        assert isinstance(item, Item)
        assert item.name == "1180424618.59.18120"
        item.metadata.keys()
        item.keys()
        py.test.raises(BackendError, self.item_collection.new_item, items[0])
        assert "1180424618.59.18120" in self.item_collection
        del self.item_collection["1180424618.59.18120"]
        assert not "1180424618.59.18120" in self.item_collection

    def test_rename_item(self):
        self.item_collection.rename_item(items[0], "asdf")
        assert "asdf" in self.item_collection
        self.item_collection.rename_item("asdf", items[0])
        assert items[0] in self.item_collection

    def test_copy_item(self):
        self.item_collection.copy_item(items[0], "asdf")
        assert "asdf" in self.item_collection
        del self.item_collection["asdf"]
        assert not "asdf" in self.item_collection
        py.test.raises(BackendError, self.item_collection.copy_item, items[0], "")
        py.test.raises(BackendError, self.item_collection.copy_item, items[0], items[0])
        py.test.raises(BackendError, self.item_collection.copy_item, items[0], items[1])
        py.test.raises(BackendError, self.item_collection.copy_item, "asdf", items[1])


class TestItem:

    item = None

    def setup_class(self):
        self.item = ItemCollection(get_page_backend(), None)[items[0]]

    def teardown_class(self):
        self.item = None

    def test_has_revision(self):
        assert 1 in self.item

    def test_get_revision(self):
        revision = self.item[1]
        assert isinstance(revision, Revision)
        assert revision.revno == 1
        revision = self.item[0]
        assert isinstance(revision, Revision)
        assert revision.revno == 1
        py.test.raises(NoSuchRevisionError, lambda: self.item[5])

    def test_keys(self):
        assert self.item.keys() == [1]

    def test_del_add_revision(self):
        self.item.lock = True
        assert self.item.current == 1
        assert isinstance(self.item.new_revision(), Revision)
        assert self.item.current == 1
        assert 2 in self.item
        assert isinstance(self.item.new_revision(3), Revision)
        assert 3 in self.item
        assert self.item.current == 1
        del self.item[3]
        assert self.item.current == 1
        del self.item[2]
        assert self.item.current == 1
        assert not 2 in self.item
        assert not 3 in self.item
        py.test.raises(NoSuchRevisionError, lambda: self.item[5])
        py.test.raises(BackendError, self.item.new_revision, 1)
        self.item.lock = False

    def test_acl(self):
        assert self.item.acl

    def test_edit_lock(self):
        self.item.lock = True
        assert self.item.edit_lock == (True, 1183317594000000L, '1183317550.72.7782')
        self.item.edit_lock = False
        self.item.metadata.save()
        assert self.item.edit_lock == (False, 0, None)
        self.item.edit_lock = (1183317594000000L, '1183317550.72.7782')
        self.item.metadata.save()
        assert self.item.edit_lock == (True, 1183317594000000L, '1183317550.72.7782')
        self.item.lock = False

    def test_lock(self):
        assert not self.item.lock
        self.item.lock = True
        assert self.item.lock
        self.item.lock = False
        assert not self.item.lock
        py.test.raises(LockingError, self.item.new_revision, 1)
        py.test.raises(LockingError, self.item[0].data.write, "test")


class TestRevision:

    revision = None

    def setup_class(self):
        self.revision = ItemCollection(get_page_backend(), None)[items[0]][1]

    def teardown_class(self):
        self.revision = None

    def test(self):
        self.revision.data
        self.revision.metadata

