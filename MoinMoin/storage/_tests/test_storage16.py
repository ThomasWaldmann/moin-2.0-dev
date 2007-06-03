"""
    MoinMoin 1.6 compatible storage backend tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import py.test

from common import datadir, names, metadata, DummyConfig

from MoinMoin.storage.storage16 import UserStorage
from MoinMoin.storage.error import StorageError


class TestUserBackend():
    
    backend = None
    
    def setup_class(self):
        self.backend = UserStorage(datadir, DummyConfig())
    
    def teardown_class(self):
        self.backend = None
        
    def test_list_revisions(self):
        assert self.backend.list_revisions(names[0]) == [1]
        
    def test_create_revision(self):
        py.test.raises(NotImplementedError, self.backend.create_revision, names[0], 1)
    
    def test_remove_revision(self):
         py.test.raises(NotImplementedError, self.backend.remove_revision, names[0], 2)
    
    def test_get_data_backend(self):
         py.test.raises(NotImplementedError, self.backend.get_data_backend, names[0], 1, "a")
    
    def test_list_items(self):
        assert self.backend.list_items() == names
        assert self.backend.list_items({'name': 'HeinrichWendel'}) == [names[0]]
    
    def test_has_item(self):
        assert self.backend.has_item(names[0])
        assert not self.backend.has_item("asdf")
  
    def test_create_and_remove_item(self):
        self.backend.create_item("test");
        assert self.backend.has_item(names[0])
        
        py.test.raises(StorageError, self.backend.create_item, names[0])

        self.backend.remove_item("test");
        assert not self.backend.has_item("test")
        
        py.test.raises(StorageError, self.backend.remove_item, "blub")
    
    def test_get_metadata(self):
        assert self.backend.get_metadata(names[0], 1) == metadata
        py.test.raises(StorageError, self.backend.get_metadata, "blub", 0)   
    
    def test_set_metadata(self):
        self.backend.set_metadata(names[0], 0, {"aliasname": "test"})
        metadata["aliasname"] = "test";        
        assert self.backend.get_metadata(names[0], 1) == metadata
        self.backend.set_metadata(names[0], 0, {"aliasname": ""})
        metadata["aliasname"] = ""
        assert self.backend.get_metadata(names[0], 1) == metadata
        py.test.raises(StorageError, self.backend.set_metadata, "blub", 0, {'test': ''})
    
    def test_remove_metadata(self):
        self.backend.set_metadata(names[0], 0, {"battle": "test"})
        metadata["battle"] = "test";        
        assert self.backend.get_metadata(names[0], 1) == metadata
        self.backend.remove_metadata(names[0], 0, ["battle"])
        del metadata["battle"]        
        assert self.backend.get_metadata(names[0], 1) == metadata
        py.test.raises(StorageError, self.backend.remove_metadata, "blub", 0, ['test'])
