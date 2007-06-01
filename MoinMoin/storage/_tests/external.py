"""
    MoinMoin external interfaces tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

from common import *

import unittest

from MoinMoin.storage.storage16 import UserStorage
from MoinMoin.storage.external import ItemCollection, Item, Revision, Metadata, Data


class ItemCollectionTest(unittest.TestCase):
    
    item_collection = None    
    
    def setUp(self):
        self.item_collection = ItemCollection(UserStorage(datadir), None)
    
    def tearDown(self):
        self.item_collection = None
        
    def test_has_item(self):
        self.assertTrue(names[0] in self.item_collection)
        self.assertFalse("asdf" in self.item_collection)
        
    def test_keys(self):
        self.assertEquals(self.item_collection.keys(), names)
        self.assertEquals(self.item_collection.keys({'name' : 'HeinrichWendel'}), [names[0]])
    
    def test_get_item(self):
        item = self.item_collection[names[0]]
        self.assertTrue(isinstance(item, Item))
        self.assertEquals(item.name, names[0])
        try:
            self.item_collection["test"]
            self.fail()
        except KeyError:
            self.assertTrue(True)
    
    def test_new_item(self):
        item  = self.item_collection.new_item("test")
        self.assertTrue(isinstance(item, Item))
        self.assertEquals(item.name, "test")
        self.assertTrue(item.new)
        
        try:
            self.item_collection.new_item(names[0])
            self.fail()
        except:
            self.assertTrue(True)
    
    def test_delete_item(self):
        """
        TODO: it's just one call...
        """
        pass

class ItemTest(unittest.TestCase):
    
    item = None
    
    def setUp(self):
        self.item = ItemCollection(UserStorage(datadir), None)[names[0]]
    
    def tearDown(self):
        self.item = None
    
    def test_has_revision(self):
        self.assertTrue(1 in self.item)
    
    def test_get_revision(self):
        revision = self.item[1]
        self.assertTrue(isinstance(revision, Revision))
        self.assertEquals(revision.revno, 1)
        try:
            self.item[5]
            self.fail()
        except:
            self.assertTrue(True)
    
    def test_keys(self):
        self.assertEquals(self.item.keys(), [1])
        
    def test_del_add_revision(self):
        self.item.new_revision()
        self.assertTrue(2 in self.item)
        self.item.new_revision(4)
        self.assertTrue(4 in self.item)
        del self.item[2]
        del self.item[4]
        self.assertFalse(2 in self.item)
        self.assertFalse(4 in self.item)
        try:
            del self.item[5]
            self.fail()
        except:
            self.assertTrue(True)
        try:
            self.item.new_revision(1)
            self.fail()
        except:
            self.assertTrue(True)
    
    def test_save(self):
        """
        TODO: just do it.
        """
        pass


class RevisionTest(unittest.TestCase):
    revision = None
    
    def setUp(self):
        self.revision = ItemCollection(UserStorage(datadir), None)[names[0]][1]
    
    def tearDown(self):
        self.revision = None
    
    def test(self):
        self.assertTrue(isinstance(self.revision.data, Data))
        self.assertTrue(isinstance(self.revision.metadata, Metadata))
    
    
class MetadataTest(unittest.TestCase):
    metadata = None
    
    def setUp(self):
        self.metadata = ItemCollection(UserStorage(datadir), None)[names[0]][1].metadata
    
    def tearDown(self):
        self.metadata = None
    
    def test_contains(self):
        self.assertTrue("name" in self.metadata)
        self.assertFalse("xyz" in self.metadata)
    
    def test_get(self):
        self.metadata["name"]
        try:
            self.metadata["yz"]
            self.fail()
        except:
            self.assertTrue(True)
    
    def test_set(self):
        self.metadata["name"] = "123"
        self.assertEquals(self.metadata["name"], "123")
    
    def test_remove(self):
        self.metadata["xyz"] = "123"
        self.assertTrue("xyz" in self.metadata)
        del self.metadata["xyz"]
        self.assertFalse("xyz" in self.metadata)
        
    def test_keys(self):
        assertLists(self, self.metadata.keys(), metadata.keys())
    
if __name__ == "__main__":
        unittest.main()