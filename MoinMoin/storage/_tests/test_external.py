"""
    MoinMoin external interfaces tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import py.test

from common import user_dir, names, metadata, DummyConfig, page_dir, pages

from MoinMoin.storage.fs_moin16 import UserStorage, PageStorage
from MoinMoin.storage.external import ItemCollection, Item, Revision, Metadata
from MoinMoin.storage.error import BackendError, RevisionNotExistsError, ItemNotExistsError
from MoinMoin.storage.interfaces import DataBackend



class TestItemCollection:
    item_collection = None

    def setup_class(self):
        self.item_collection = ItemCollection(UserStorage(user_dir, DummyConfig()), None)

    def teardown_class(self):
        self.item_collection = None

    def test_has_item(self):
        assert names[0] in self.item_collection
        assert not("asdf" in self.item_collection)

    def test_keys(self):
        assert self.item_collection.keys() == names
        assert self.item_collection.keys({'name': 'HeinrichWendel'}) == [names[0]]

    def test_get_item(self):
        item = self.item_collection[names[0]]
        assert isinstance(item, Item)
        assert item.name == names[0]
        py.test.raises(ItemNotExistsError, lambda: self.item_collection["test"])

    def test_new_delete_item(self):
        item = self.item_collection.new_item("1180424618.59.18120")
        assert isinstance(item, Item)
        assert item.name == "1180424618.59.18120"
        item.metadata.keys()
        item.keys()
        py.test.raises(BackendError, self.item_collection.new_item, names[0])
        assert "1180424618.59.18120" in self.item_collection
        del self.item_collection["1180424618.59.18120"]
        assert not "1180424618.59.18120" in self.item_collection


class TestItem:

    item = None

    def setup_class(self):
        self.item = ItemCollection(PageStorage(page_dir, DummyConfig()), None)[pages[0]]

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
        assert revision.revno == 0
        py.test.raises(RevisionNotExistsError, lambda: self.item[5])

    def test_keys(self):
        assert self.item.keys() == [0, 1]

    def test_del_add_revision(self):
        self.item.new_revision()
        assert 2 in self.item
        self.item.new_revision(4)
        assert 4 in self.item
        del self.item[2]
        del self.item[4]
        assert not 2 in self.item
        assert not 4 in self.item
        py.test.raises(RevisionNotExistsError, lambda: self.item[5])
        py.test.raises(BackendError, self.item.new_revision, 1)


class TestRevision:

    revision = None

    def setup_class(self):
        self.revision = ItemCollection(PageStorage(page_dir, DummyConfig()), None)[pages[0]][1]

    def teardown_class(self):
        self.revision = None

    def test(self):
        assert isinstance(self.revision.data, DataBackend)
        assert isinstance(self.revision.metadata, Metadata)


class TestMetadata:

    metadata = None

    def setup_class(self):
        self.metadata = ItemCollection(UserStorage(user_dir, DummyConfig()), None)[names[0]][1].metadata

    def teardown_class(self):
        self.metadata = None

    def test_contains(self):
        assert "name" in self.metadata
        assert not "xyz" in self.metadata

    def test_get(self):
        self.metadata["name"]
        py.test.raises(KeyError, lambda: self.metadata["yz"])

    def test_set(self):
        self.metadata["name"] = "123"
        assert self.metadata["name"] == "123"
        assert self.metadata.changed["name"] == "set"

    def test_remove(self):
        self.metadata["xyz"] = "123"
        assert "xyz" in self.metadata
        assert self.metadata.changed["xyz"] == "add"
        del self.metadata["xyz"]
        assert not "xyz" in self.metadata
        assert "xyz" not in self.metadata.changed
        del self.metadata["aliasname"]
        assert not "aliasname" in self.metadata
        assert self.metadata.changed["aliasname"] == "remove"
        self.metadata["aliasname"] = ""

    def test_keys(self):
        assert set(self.metadata.keys()) == set(metadata.keys())

    def test_save(self):
        pass

