"""
    MoinMoin 1.6 compatible storage backend tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import os
import py.test

from MoinMoin.storage._tests import get_user_dir, get_page_dir, names, metadata, DummyConfig, pages, setup, teardown, BackendTest

from MoinMoin.storage.fs_moin16 import UserStorage, PageStorage
from MoinMoin.storage.interfaces import DELETED, SIZE, ACL, LOCK_TIMESTAMP, LOCK_USER
from MoinMoin.storage.error import BackendError, NoSuchItemError, NoSuchRevisionError


def setup_module(module):
    setup(module)

def teardown_module(module):
    teardown(module)


class TestUserBackend(BackendTest):

    def setup_class(self):
        self.backend = UserStorage(get_user_dir(), DummyConfig(), "user")

    def test_name(self):
        assert self.backend.name == "user"

    def test_list_revisions(self):
        assert self.backend.list_revisions(names[0]) == [1]

    def test_current_revision(self):
        assert self.backend.current_revision(names[0]) == 1

    def test_has_revision(self):
        assert self.backend.has_revision(names[0], 1)
        assert self.backend.has_revision(names[1], 0)
        assert not self.backend.has_revision(names[2], 2)
        assert not self.backend.has_revision(names[0], -1)

    def test_create_revision(self):
        py.test.raises(NotImplementedError, self.backend.create_revision, names[0], 1)

    def test_remove_revision(self):
        py.test.raises(NotImplementedError, self.backend.remove_revision, names[0], 2)

    def test_get_data_backend(self):
        py.test.raises(NotImplementedError, self.backend.get_data_backend, names[0], 1)

    def test_rename_item(self):
        py.test.raises(NotImplementedError, self.backend.rename_item, names[0], names[1])

    def test_list_items(self):
        assert self.backend.list_items() == names
        assert self.backend.list_items({'name': 'HeinrichWendel'}) == [names[0]]

    def test_has_item(self):
        assert self.backend.has_item(names[0])
        assert not self.backend.has_item("asdf")
        BackendTest.test_has_item(self)

    def test_create_and_remove_item(self):
        self.backend.create_item("1180424618.59.18120")
        assert self.backend.has_item("1180424618.59.18120")

        py.test.raises(BackendError, self.backend.create_item, names[0])

        self.backend.remove_item("1180424618.59.18120")
        assert not self.backend.has_item("1180424618.59.18120")

        py.test.raises(NoSuchItemError, self.backend.remove_item, "blub")

    def test_get_metadata(self):
        assert self.backend.get_metadata(names[0], 1) == metadata
        py.test.raises(NoSuchItemError, self.backend.get_metadata, "blub", 0)

    def test_set_metadata(self):
        self.backend.set_metadata(names[0], 0, {"aliasname": "test"})
        metadata["aliasname"] = "test"
        assert self.backend.get_metadata(names[0], 1) == metadata
        self.backend.set_metadata(names[0], 0, {"aliasname": ""})
        metadata["aliasname"] = ""
        assert self.backend.get_metadata(names[0], 1) == metadata
        py.test.raises(NoSuchItemError, self.backend.set_metadata, "blub", 0, {'test': ''})

    def test_remove_metadata(self):
        self.backend.set_metadata(names[0], 0, {"battle": "test"})
        metadata["battle"] = "test"
        assert self.backend.get_metadata(names[0], 1) == metadata
        self.backend.remove_metadata(names[0], 0, ["battle"])
        del metadata["battle"]
        assert self.backend.get_metadata(names[0], 1) == metadata
        py.test.raises(NoSuchItemError, self.backend.remove_metadata, "blub", 0, ['test'])
        py.test.raises(KeyError, self.backend.remove_metadata, names[0], 0, ['NotExist'])

        
class TestPageBackend(BackendTest):

    def setup_class(self):
        self.backend = PageStorage(get_page_dir(), DummyConfig(), "pages")

    def test_name(self):
        assert self.backend.name == "pages"
        
    def test_list_items(self):
        assert self.backend.list_items() == pages
        assert self.backend.list_items({'format': 'wiki'}) == [pages[1]]

    def test_has_item(self):
        assert self.backend.has_item(pages[0])
        assert not self.backend.has_item("ad")
        BackendTest.test_has_item(self)

    def test_create_and_remove_item(self):
        py.test.raises(BackendError, self.backend.create_item, "Test")
        self.backend.create_item("Yeah")
        assert os.path.isdir(os.path.join(get_page_dir(), "Yeah"))
        assert os.path.isdir(os.path.join(get_page_dir(), "Yeah", "cache"))
        assert os.path.isdir(os.path.join(get_page_dir(), "Yeah", "cache", "__lock__"))
        assert os.path.isdir(os.path.join(get_page_dir(), "Yeah", "revisions"))
        assert os.path.isfile(os.path.join(get_page_dir(), "Yeah", "current"))
        assert os.path.isfile(os.path.join(get_page_dir(), "Yeah", "edit-log"))
        py.test.raises(NoSuchItemError, self.backend.remove_item, "ADF")
        assert self.backend.current_revision("Yeah") == 0
        self.backend.remove_item("Yeah")

    def test_current_revision(self):
        assert self.backend.current_revision(pages[0]) == 1
        assert self.backend.current_revision(pages[1]) == 2

    def test_list_revisions(self):
        assert self.backend.list_revisions(pages[0]) == [1]
        assert self.backend.list_revisions(pages[1]) == [2, 1]
        py.test.raises(NoSuchItemError, self.backend.list_revisions, "ADF")

    def test_has_revision(self):
        assert self.backend.has_revision(pages[0], 0)
        assert self.backend.has_revision(pages[0], 1)
        assert not self.backend.has_revision(pages[0], 2)
        assert self.backend.has_revision(pages[1], 0)
        assert self.backend.has_revision(pages[1], 1)
        assert self.backend.has_revision(pages[1], 2)
        assert not self.backend.has_revision(pages[1], 3)

    def test_create_remove_revision(self):
        assert self.backend.create_revision(pages[0], 3) == 3
        assert os.path.isfile(os.path.join(get_page_dir(), pages[0], "revisions", "00000003"))
        assert open(os.path.join(get_page_dir(), pages[0], "current"), "r").read() == "00000003\n"
        assert self.backend.remove_revision(pages[0], 3) == 3
        assert open(os.path.join(get_page_dir(), pages[0], "current"), "r").read() == "00000001\n"
        assert not os.path.isfile(os.path.join(get_page_dir(), pages[0], "revisions", "00000003"))

        py.test.raises(BackendError, self.backend.create_revision, pages[0], 1)
        py.test.raises(NoSuchItemError, self.backend.create_revision, "ADF", 1)

        py.test.raises(NoSuchRevisionError, self.backend.remove_revision, pages[0], 4)
        py.test.raises(NoSuchItemError, self.backend.remove_revision, "ADF", 4)

    def test_get_data_backend(self):
        data = self.backend.get_data_backend(pages[0], 1)
        data.close()
        py.test.raises(NoSuchItemError, self.backend.get_data_backend, "adsf", 2)
        py.test.raises(NoSuchRevisionError, self.backend.get_data_backend, pages[0], 3)

    def test_get_metadata(self):
        py.test.raises(NoSuchItemError, self.backend.get_metadata, "adsf", 2)
        py.test.raises(NoSuchRevisionError, self.backend.get_metadata, pages[0], 3)
        assert self.backend.get_metadata(pages[1], 2) == {SIZE: 192L, 'format': 'wiki', 'acl':['MoinPagesEditorGroup:read,write,delete,revert All:read'], 'language':'sv'}
        assert self.backend.get_metadata(pages[0], -1) == {LOCK_TIMESTAMP: '1183317594000000', LOCK_USER: '1183317550.72.7782'}
        assert self.backend.get_metadata(pages[1], -1) == {LOCK_TIMESTAMP: '1182452549000000', LOCK_USER: '127.0.0.1'}

    def test_set_metadata(self):
        py.test.raises(NoSuchItemError, self.backend.set_metadata, "adsf", 2, {'asdf': '123' })
        py.test.raises(NoSuchRevisionError, self.backend.set_metadata, pages[0], 3, {'asdf': '123' })
        self.backend.set_metadata(pages[1], 2, {'format': 'test'})
        assert self.backend.get_metadata(pages[1], 2) == {SIZE: 192L, 'format': 'test', 'acl':['MoinPagesEditorGroup:read,write,delete,revert All:read'], 'language':'sv'}
        self.backend.set_metadata(pages[1], 2, {'format': 'wiki'})
        self.backend.set_metadata(pages[1], -1, {LOCK_TIMESTAMP: '1283317594000000', LOCK_USER: '192.168.0.1'})
        assert self.backend.get_metadata(pages[1], -1) == {LOCK_TIMESTAMP: '1283317594000000', LOCK_USER: '192.168.0.1'}

    def test_remove_metadata(self):
        py.test.raises(NoSuchItemError, self.backend.remove_metadata, "adsf", 2, ["adf"])
        py.test.raises(NoSuchRevisionError, self.backend.remove_metadata, pages[0], 3, ["adf"])
        py.test.raises(KeyError, self.backend.remove_metadata, pages[0], 1, ["adf"])
        self.backend.remove_metadata(pages[1], 2, ['format'])
        assert self.backend.get_metadata(pages[1], 2) == {SIZE: 179L, 'acl':['MoinPagesEditorGroup:read,write,delete,revert All:read'], 'language':'sv'}
        self.backend.set_metadata(pages[1], 2, {'format': 'wiki'})
        self.backend.remove_metadata(pages[1], -1, [LOCK_TIMESTAMP, LOCK_USER])
        assert self.backend.get_metadata(pages[1], -1) == {}

    def test_rename_item(self):
        self.backend.rename_item(pages[0], "abcde")
        assert os.path.isdir(os.path.join(get_page_dir(), "abcde"))
        assert self.backend.has_item("abcde")
        self.backend.rename_item("abcde", pages[0])
        assert os.path.isdir(os.path.join(get_page_dir(), pages[0]))
        assert self.backend.has_item(pages[0])
        py.test.raises(BackendError, self.backend.rename_item, pages[0], pages[1])
        BackendTest.test_rename_item(self)
        

class TestPageData:
    """
    TODO: write this test, but the PageData calls are just forwarded to the fileDescriptor,
    so it is not really neccessary.
    """
    pass

