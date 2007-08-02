"""
    MoinMoin 1.6 compatible storage backend tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import os
import py.test

from MoinMoin.storage._tests import get_user_dir, get_page_dir, names, metadata, DummyConfig, pages, setup, teardown, BackendTest

from MoinMoin.storage.backends.moin16 import UserBackend, PageBackend
from MoinMoin.storage.external import SIZE, ACL
from MoinMoin.storage.external import EDIT_LOCK_TIMESTAMP, EDIT_LOCK_USER
from MoinMoin.storage.external import EDIT_LOG_MTIME, EDIT_LOG_USERID, EDIT_LOG_COMMENT, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME, EDIT_LOG_EXTRA, EDIT_LOG_ACTION
from MoinMoin.storage.error import BackendError, NoSuchItemError, NoSuchRevisionError


def setup_module(module):
    setup(module)

def teardown_module(module):
    teardown(module)


class TestUserBackend(BackendTest):

    def setup_class(self):
        self.backend = UserBackend("user", get_user_dir(), DummyConfig())

    def test_name(self):
        assert self.backend.name == "user"

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

    def test_list_revisions(self):
        assert self.backend.list_revisions(names[0]) == [1]

    def test_current_revision(self):
        assert self.backend.current_revision(names[0]) == 1

    def test_has_revision(self):
        assert self.backend.has_revision(names[0], 1)
        assert self.backend.has_revision(names[1], 0)
        assert not self.backend.has_revision(names[2], 2)
        assert not self.backend.has_revision(names[0], -1)

    def test_get_metadata_backend(self):
        self.backend.get_metadata_backend(names[0], 1)


class TestUserMetadata:

    def setup_class(self):
        self.backend = UserBackend("user", get_user_dir(), DummyConfig())
        self.metadata = self.backend.get_metadata_backend(names[0], 1)

    def test_get(self):
        assert self.metadata == metadata

    def test_set(self):
        self.metadata["aliasname"] = "test"
        self.metadata.save()
        metadata["aliasname"] = "test"
        assert self.metadata == metadata

        self.metadata["aliasname"] = ""
        self.metadata.save()
        metadata["aliasname"] = ""
        assert self.metadata == metadata

    def test_del(self):
        self.metadata["battle"] = "test"
        self.metadata.save()
        metadata["battle"] = "test"
        assert self.metadata == metadata

        del self.metadata["battle"]
        self.metadata.save()
        del metadata["battle"]
        assert self.metadata == metadata


class TestPageBackend(BackendTest):

    def setup_class(self):
        self.backend = PageBackend("pages", get_page_dir(), DummyConfig())

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

    def test_rename_item(self):
        py.test.raises(BackendError, self.backend.rename_item, pages[0], "")
        py.test.raises(BackendError, self.backend.rename_item, pages[0], pages[0])
        self.backend.rename_item(pages[0], "abcde")
        assert os.path.isdir(os.path.join(get_page_dir(), "abcde"))
        assert self.backend.has_item("abcde")
        self.backend.rename_item("abcde", pages[0])
        assert os.path.isdir(os.path.join(get_page_dir(), pages[0]))
        assert self.backend.has_item(pages[0])
        py.test.raises(BackendError, self.backend.rename_item, pages[0], pages[1])

    def test_list_revisions(self):
        assert self.backend.list_revisions(pages[0]) == [1]
        assert self.backend.list_revisions(pages[1]) == [2, 1]
        py.test.raises(NoSuchItemError, self.backend.list_revisions, "ADF")

    def test_current_revision(self):
        assert self.backend.current_revision(pages[0]) == 1
        assert self.backend.current_revision(pages[1]) == 2

    def test_has_revision(self):
        assert self.backend.has_revision(pages[0], 0)
        assert self.backend.has_revision(pages[0], 1)
        assert not self.backend.has_revision(pages[0], 2)
        assert self.backend.has_revision(pages[1], 0)
        assert self.backend.has_revision(pages[1], 1)
        assert self.backend.has_revision(pages[1], 2)
        assert not self.backend.has_revision(pages[1], 3)

    def test_create_remove_revision(self):
        assert self.backend.create_revision(pages[0], 2) == 2
        assert os.path.isfile(os.path.join(get_page_dir(), pages[0], "revisions", "00000002"))
        assert open(os.path.join(get_page_dir(), pages[0], "current"), "r").read() == "00000002\n"
        assert self.backend.current_revision(pages[0]) == 1
        assert self.backend.current_revision(pages[0], includeEmpty=True) == 2
        assert self.backend.remove_revision(pages[0], 2) == 2
        assert open(os.path.join(get_page_dir(), pages[0], "current"), "r").read() == "00000001\n"
        assert not os.path.isfile(os.path.join(get_page_dir(), pages[0], "revisions", "00000002"))
        assert self.backend.current_revision(pages[0]) == 1
        assert self.backend.current_revision(pages[0], includeEmpty=True) == 1

        py.test.raises(BackendError, self.backend.create_revision, pages[0], 1)
        py.test.raises(NoSuchItemError, self.backend.create_revision, "ADF", 1)

        py.test.raises(NoSuchRevisionError, self.backend.remove_revision, pages[0], 4)
        py.test.raises(NoSuchItemError, self.backend.remove_revision, "ADF", 4)

    def test_get_data_backend(self):
        self.backend.get_data_backend(pages[0], 1)

    def test_get_metadata_backend(self):
        self.backend.get_metadata_backend(pages[0], 1)


class TestPageMetadata:

    def setup_class(self):
        self.backend = PageBackend("pages", get_page_dir(), DummyConfig())

    def test_get(self):
        metadata1 = self.backend.get_metadata_backend(pages[1], 2)
        assert metadata1 == {EDIT_LOG_EXTRA: '', EDIT_LOG_ACTION: 'SAVE', EDIT_LOG_ADDR: '127.0.0.1', EDIT_LOG_HOSTNAME: 'localhost', EDIT_LOG_COMMENT: '', EDIT_LOG_USERID: '1180352194.13.59241', EDIT_LOG_MTIME: metadata1[EDIT_LOG_MTIME], SIZE: 192L, 'format': 'wiki', ACL: 'MoinPagesEditorGroup:read,write,delete,revert All:read', 'language': 'sv'}
        metadata2 = self.backend.get_metadata_backend(pages[0], -1)
        assert metadata2 == {EDIT_LOCK_TIMESTAMP: '1183317594000000', EDIT_LOCK_USER: '1183317550.72.7782'}
        metadata3 = self.backend.get_metadata_backend(pages[1], -1)
        assert metadata3 == {EDIT_LOCK_TIMESTAMP: '1182452549000000', EDIT_LOCK_USER: '127.0.0.1'}

    def test_set(self):
        metadata1 = self.backend.get_metadata_backend(pages[1], 2)
        metadata1['format'] = 'test'
        metadata1.save()
        assert metadata1 == {EDIT_LOG_EXTRA: '', EDIT_LOG_ACTION: 'SAVE', EDIT_LOG_ADDR: '127.0.0.1', EDIT_LOG_HOSTNAME: 'localhost', EDIT_LOG_COMMENT: '', EDIT_LOG_USERID: '1180352194.13.59241', EDIT_LOG_MTIME: metadata1[EDIT_LOG_MTIME], SIZE: 192L, 'format': 'test', ACL: 'MoinPagesEditorGroup:read,write,delete,revert All:read', 'language': 'sv'}
        metadata1['format'] = 'wiki'
        metadata1.save()

        metadata2 = self.backend.get_metadata_backend(pages[1], -1)
        metadata2[EDIT_LOCK_TIMESTAMP] = '1283317594000000'
        metadata2[EDIT_LOCK_USER]= '192.168.0.1'
        metadata2.save()
        assert metadata2 == {EDIT_LOCK_TIMESTAMP: '1283317594000000', EDIT_LOCK_USER: '192.168.0.1'}

    def test_del(self):
        metadata1 = self.backend.get_metadata_backend(pages[1], 2)
        del metadata1['format']
        metadata1.save()
        assert metadata1 == {EDIT_LOG_EXTRA: '', EDIT_LOG_ACTION: 'SAVE', EDIT_LOG_ADDR: '127.0.0.1', EDIT_LOG_HOSTNAME: 'localhost', EDIT_LOG_COMMENT: '', EDIT_LOG_USERID: '1180352194.13.59241', EDIT_LOG_MTIME: metadata1[EDIT_LOG_MTIME], SIZE: 179L, ACL: 'MoinPagesEditorGroup:read,write,delete,revert All:read', 'language': 'sv'}

        metadata2 = self.backend.get_metadata_backend(pages[1], -1)
        del metadata2[EDIT_LOCK_TIMESTAMP]
        del metadata2[EDIT_LOCK_USER]
        metadata2.save()
        assert metadata2 == {}


