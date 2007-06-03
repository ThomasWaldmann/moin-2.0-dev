"""
    MoinMoin external interfaces tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import py.test

from common import datadir, names, metadata, DummyConfig

from MoinMoin.storage.storage16 import UserStorage
from MoinMoin.storage.external import ItemCollection, Item, Revision, Metadata, Data
from MoinMoin.storage.error import StorageError


class TestItemCollection():
    
    item_collection = None    
    
    def setup_class(self):
        self.item_collection = ItemCollection(UserStorage(datadir, DummyConfig()), None)
    
    def teardown_class(self):
        self.item_collection = None
        
    def test_has_item(self):
        assert names[0] in self.item_collection
        assert not("asdf" in self.item_collection)
        
    def test_keys(self):
        assert self.item_collection.keys() == names
        assert self.item_collection.keys({'name' : 'HeinrichWendel'}) == [names[0]]
    
    def test_get_item(self):
        item = self.item_collection[names[0]]
        assert isinstance(item, Item)
        assert item.name == names[0]
        py.test.raises(KeyError, lambda: self.item_collection["test"])
    
    def test_new_item(self):
        item  = self.item_collection.new_item("test")
        assert isinstance(item, Item)
        assert item.name == "test"
        assert item.new
        py.test.raises(StorageError, self.item_collection.new_item, names[0])
    
    def test_delete_item(self):
        """
        TODO: it's just one call...
        """
        pass


class TestItem():    
    
    item = None
    
    def setup_class(self):
        self.item = ItemCollection(UserStorage(datadir, DummyConfig()), None)[names[0]]
    
    def teardown_class(self):
        self.item = None
    
    def test_has_revision(self):
        assert 1 in self.item
    
    def test_get_revision(self):
        revision = self.item[1]
        assert isinstance(revision, Revision)
        assert revision.revno == 1
        py.test.raises(KeyError, lambda: self.item[5])
            
    def test_keys(self):
        assert self.item.keys() == [1]
        
    def test_del_add_revision(self):
        self.item.new_revision()
        assert 2 in self.item
        assert ['add', 2] in self.item.changed
        self.item.new_revision(4)
        assert 4 in self.item
        assert ['add', 4] in self.item.changed
        del self.item[2]
        assert ['remove', 2] in self.item.changed
        del self.item[4]
        assert ['remove', 4] in self.item.changed
        assert not 2 in self.item
        assert not 4 in self.item
        py.test.raises(KeyError, lambda: self.item[5])
        py.test.raises(StorageError, self.item.new_revision, 1)
    
    def test_save(self):
        """
        TODO: test adding/removing of revisions && test new
        """
        self.item = ItemCollection(UserStorage(datadir, DummyConfig()), None)[names[0]]
        del self.item[1].metadata["aliasname"]
        self.item.save()
        self.item = ItemCollection(UserStorage(datadir, DummyConfig()), None)[names[0]]
        assert "aliasname" not in self.item[1].metadata
        self.item[1].metadata["aliasname"]= ""
        self.item.save()
        self.item = ItemCollection(UserStorage(datadir, DummyConfig()), None)[names[0]]
        assert "aliasname" in self.item[1].metadata


class TestRevision():
    
    revision = None
    
    def setup_class(self):
        self.revision = ItemCollection(UserStorage(datadir, DummyConfig()), None)[names[0]][1]
    
    def teardown_class(self):
        self.revision = None
    
    def test(self):
        assert isinstance(self.revision.data, Data)
        assert isinstance(self.revision.metadata, Metadata)
    
    
class TestMetadata():
    
    metadata = None
    
    def setup_class(self):
        self.metadata = ItemCollection(UserStorage(datadir, DummyConfig()), None)[names[0]][1].metadata
    
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
    