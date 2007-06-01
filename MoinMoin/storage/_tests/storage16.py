"""
    MoinMoin 1.6 compatible storage backend tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

from common import *

import unittest

from MoinMoin.storage.storage16 import UserStorage
from MoinMoin.storage.error import StorageError


class TestUserBackend(unittest.TestCase):
    
    backend = None
    
    def setUp(self):
        self.backend = UserStorage(datadir)
    
    def tearDown(self):
        self.backend = None
        
    def test_list_revisions(self):
        self.assertEquals(self.backend.list_revisions(names[0]), [1])
        
    def test_create_revision(self):
        try:
            self.backend.create_revision(names[0], 1)
            self.fail()
        except NotImplementedError:
            self.assertTrue(True)
    
    def test_remove_revision(self):
        try:
            self.backend.remove_revision(names[0], 2)
            self.fail()
        except NotImplementedError:
            self.assertTrue(True)
    
    def test_get_data_backend(self):
        try:
            self.backend.get_data_backend(names[0], 1, "a")
            self.fail()
        except NotImplementedError:
            self.assertTrue(True)
    
    def test_list_items(self):
        self.assertEquals(self.backend.list_items(), names)
        self.assertEquals(self.backend.list_items({'name': 'HeinrichWendel'}), [names[0]])
    
    def test_has_item(self):
        self.assertTrue(self.backend.has_item(names[0]))
        self.assertFalse(self.backend.has_item("asdf"));
  
    def test_create_and_remove_item(self):
        self.backend.create_item("test");
        self.assertTrue(self.backend.has_item(names[0]))
        
        try:
            self.backend.create_item(names[0]);
            self.fail()
        except StorageError:
            self.assertTrue(True)

        self.backend.remove_item("test");
        self.assertFalse(self.backend.has_item("test"))
        
        try:
            self.backend.remove_item("blub");
            self.fail()
        except StorageError:
            self.assertTrue(True)
    
    def test_get_metadata(self):
        assertDicts(self, self.backend.get_metadata(names[0], 1), metadata)
        try:
            self.backend.get_metadata("blub", 0);
            self.fail()
        except StorageError:
            self.assertTrue(True)
    
    
    def test_set_metadata(self):
        self.backend.set_metadata(names[0], 0, {"aliasname": "test"})
        metadata["aliasname"] = "test";        
        assertDicts(self, self.backend.get_metadata(names[0], 1), metadata)
        self.backend.set_metadata(names[0], 0, {"aliasname": ""})
        metadata["aliasname"] = ""
        assertDicts(self, self.backend.get_metadata(names[0], 1), metadata)
        try:
            self.backend.set_metadata("blub", 0, {'test': ''});
            self.fail()
        except StorageError:
            self.assertTrue(True)
    
    def test_remove_metadata(self):
        self.backend.set_metadata(names[0], 0, {"battle": "test"})
        metadata["battle"] = "test";        
        assertDicts(self, self.backend.get_metadata(names[0], 1), metadata)
        self.backend.remove_metadata(names[0], 0, ["battle"])
        del metadata["battle"]        
        assertDicts(self, self.backend.get_metadata(names[0], 1), metadata)
        try:
            self.backend.remove_metadata("blub", 0, ['test']);
            self.fail()
        except StorageError:
            self.assertTrue(True)
    
if __name__ == "__main__":
        unittest.main()