"""
    MoinMoin 1.6 compatible storage backend tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import os
import py.test

from common import user_dir, page_dir, names, metadata, DummyConfig, pages

from MoinMoin.storage.fs_moin16 import UserStorage, PageStorage
from MoinMoin.storage.error import StorageError


class TestUserBackend():
    
    backend = None
    
    def setup_class(self):
        self.backend = UserStorage(user_dir, DummyConfig())
    
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
        assert not self.backend.has_item("")
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
        py.test.raises(KeyError, self.backend.remove_metadata, names[0], 0, ['NotExist'])


class TestPageBackend():
    
    backend = None
    
    def setup_class(self):
        self.backend = PageStorage(page_dir, DummyConfig())
    
    def teardown_class(self):
        self.backend = None
        
    def test_list_items(self):
        assert self.backend.list_items() == pages
    
    def test_has_item(self):
        """
        TODO: Test metadata.
        """
        assert self.backend.has_item(pages[0])
        assert not self.backend.has_item("ad")
        assert not self.backend.has_item("")
    
    def test_create_and_remove_item(self):
        py.test.raises(StorageError, self.backend.create_item, "Test")
        self.backend.create_item("Yeah")
        assert os.path.isdir(os.path.join(page_dir, "Yeah"))
        assert os.path.isdir(os.path.join(page_dir, "Yeah", "cache"))
        assert os.path.isdir(os.path.join(page_dir, "Yeah", "cache", "__lock__"))
        assert os.path.isdir(os.path.join(page_dir, "Yeah", "revisions"))
        assert os.path.isfile(os.path.join(page_dir, "Yeah", "current"))
        assert os.path.isfile(os.path.join(page_dir, "Yeah", "edit-log"))
        
        py.test.raises(StorageError, self.backend.remove_item, "ADF")
        self.backend.remove_item("Yeah")
    
    def test_list_revisions(self):
        assert self.backend.list_revisions(pages[0]) == [1]
        assert self.backend.list_revisions(pages[1]) == [1, 2]
        py.test.raises(StorageError, self.backend.list_revisions, "ADF")
    
    def test_create_remove_revision(self):
        self.backend.create_revision(pages[0], 3)
        assert os.path.isfile(os.path.join(page_dir, pages[0], "revisions", "00000003"))
        self.backend.remove_revision(pages[0], 3)
        assert not os.path.isfile(os.path.join(page_dir, pages[0], "revisions", "00000003"))
        
        py.test.raises(StorageError, self.backend.create_revision, pages[0], 1)
        py.test.raises(StorageError, self.backend.create_revision, "ADF", 1)
        
        py.test.raises(StorageError, self.backend.remove_revision, pages[0], 4)
        py.test.raises(StorageError, self.backend.remove_revision, "ADF", 4)
    
    def test_get_data_backend(self):
        self.backend.get_data_backend(pages[0], 1, "r")
        py.test.raises(StorageError, self.backend.get_data_backend, "adsf", 2, "r")
        py.test.raises(StorageError, self.backend.get_data_backend, pages[0], 3, "r")
        
    def test_get_metadata(self):
        py.test.raises(StorageError, self.backend.get_metadata, "adsf", 2)
        py.test.raises(StorageError, self.backend.get_metadata, pages[0], 3)
        assert self.backend.get_metadata(pages[1], 2) == {'format': 'wiki', 'acl':'MoinPagesEditorGroup:read,write,delete,revert All:read', 'language':'sv'}
    
    def test_set_metadata(self):
        py.test.raises(StorageError, self.backend.set_metadata, "adsf", 2, {'asdf': '123' })
        py.test.raises(StorageError, self.backend.set_metadata, pages[0], 3, {'asdf': '123' })
        self.backend.set_metadata(pages[1], 2, {'format': 'test'})
        assert self.backend.get_metadata(pages[1], 2) == {'format': 'test', 'acl':'MoinPagesEditorGroup:read,write,delete,revert All:read', 'language':'sv'}
        self.backend.set_metadata(pages[1], 2, {'format': 'wiki'})
    
    def test_remove_metadata(self):
        py.test.raises(StorageError, self.backend.remove_metadata, "adsf", 2, ["adf"])
        py.test.raises(StorageError, self.backend.remove_metadata, pages[0], 3, ["adf"])
        py.test.raises(KeyError, self.backend.remove_metadata, pages[0], 1, ["adf"])
        self.backend.remove_metadata(pages[1], 2, ['format'])
        assert self.backend.get_metadata(pages[1], 2) == {'acl':'MoinPagesEditorGroup:read,write,delete,revert All:read', 'language':'sv'}
        self.backend.set_metadata(pages[1], 2, {'format': 'wiki'})


class TestPageData():
    """
    TODO: write this test, but the PageData calls are just forwarded to the fileDescriptor,
    so it is not really neccessary.
    """
    pass
