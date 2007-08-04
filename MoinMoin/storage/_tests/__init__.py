"""
    Common stuff for storage unit tests.

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.storage.error import BackendError, LockingError, NoSuchItemError, NoSuchRevisionError
from MoinMoin.storage.external import SIZE, ACL
from MoinMoin.storage.external import EDIT_LOCK_TIMESTAMP, EDIT_LOCK_USER
from MoinMoin.storage.external import EDIT_LOG_MTIME, EDIT_LOG_USERID, EDIT_LOG_COMMENT, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME, EDIT_LOG_EXTRA, EDIT_LOG_ACTION


default_items = ["New", "Test" ]

default_items_revisions = {}
default_items_revisions[0] = [2, 1]
default_items_revisions[1] = [3, 2, 1]

default_items_data = {}
default_items_data[0] = {}
default_items_data[0][1] = "Some text with\nAnd a new line."
default_items_data[0][2] = "[[SystemAdmin]]"
default_items_data[1] = {}
default_items_data[1][1] = "Hallo"
default_items_data[1][2] = "more text\ntext\ntext\n"
default_items_data[1][3] = "bla blub test"

default_items_metadata = {}
default_items_metadata[0] = {}
default_items_metadata[0][1] = { EDIT_LOG_EXTRA: '',
            EDIT_LOG_ACTION: 'SAVE',
            EDIT_LOG_ADDR: '127.0.0.1',
            EDIT_LOG_HOSTNAME: 'localhost',
            EDIT_LOG_COMMENT: '',
            EDIT_LOG_USERID: '1180352194.13.59241',
            EDIT_LOG_MTIME: '1186237890.109',
            SIZE: '',
            'format': 'wiki',
            ACL: 'MoinPagesEditorGroup:read,write,delete,revert All:read',
            'language' : 'sv', }

default_items_metadata[0][2] = default_items_metadata[0][1]
default_items_metadata[1] = {}
default_items_metadata[1][1] = {}
default_items_metadata[1][2] = {}
default_items_metadata[1][3] = {}

default_items_filter = ['format', 'wiki', default_items[0]]


def create_data(cls):
    for item in cls.items:
        cls.backend.create_item(item)
    for item in cls.items_revisions:
        for rev in cls.items_revisions[item]:
            cls.backend.create_revision(cls.items[item], rev)
    for item in cls.items_data:
        for rev in cls.items_data[item]:
            data = cls.backend.get_data_backend(cls.items[item], rev)
            data.write(cls.items_data[item][rev])
            data.close()
    for item in cls.items_metadata:
        for rev in cls.items_metadata[item]:
            metadata = cls.backend.get_metadata_backend(cls.items[item], rev)
            metadata.update(cls.items_metadata[item][rev])
            metadata.save()

def remove_data(cls):
    for item in cls.items:
        cls.backend.remove_item(item)


class AbstractBackendTest(object):

    newname = "Blub"
    notexist = "Juhu"

    items = default_items
    items_revisions = default_items_revisions
    items_data = default_items_data
    items_metadata = default_items_metadata
    items_filter = default_items_filter

    @classmethod
    def init(cls, name, backend):
        cls.name = name
        cls.backend = backend
        create_data(cls)

    def teardown_class(self):
        remove_data(self)

    def test_name(self):
        assert self.backend.name == self.name

    def test_list_items(self):
        assert self.backend.list_items() == self.items
        assert self.backend.list_items({self.items_filter[0]: self.items_filter[1]}) == [self.items_filter[2]]

    def test_has_item(self):
        for item in self.items:
            assert self.backend.has_item(item)
        assert not self.backend.has_item(self.notexist)
        assert not self.backend.has_item("")

    def test_create_item(self):
        py.test.raises(BackendError, self.backend.create_item, self.items[0])
        self.backend.create_item(self.newname)
        assert self.backend.has_item(self.newname)
        assert self.backend.list_items() == sorted([self.newname] + self.items)
        assert self.backend.current_revision(self.newname) == 0
    
    def test_remove_item(self):
        self.backend.remove_item(self.newname)
        assert not self.backend.has_item(self.newname)
        assert self.backend.list_items() == self.items
        py.test.raises(NoSuchItemError, self.backend.remove_item, self.newname)

    def test_rename_item(self):
        py.test.raises(BackendError, self.backend.rename_item, self.items[0], "")
        py.test.raises(BackendError, self.backend.rename_item, self.items[0], self.items[0])
        py.test.raises(BackendError, self.backend.rename_item, self.items[0], self.items[1])

        self.backend.rename_item(self.items[0], self.newname)
        assert self.backend.has_item(self.newname)
        assert not self.backend.has_item(self.items[0])
        newitems = self.items[:]
        newitems.remove(self.items[0])
        newitems.append(self.newname)
        newitems.sort()
        assert self.backend.list_items() == newitems

        self.backend.rename_item(self.newname, self.items[0])
        assert not self.backend.has_item(self.newname)
        assert self.backend.has_item(self.items[0])
        assert self.backend.list_items() == self.items

    def test_list_revisions(self):
        for item in self.items_revisions:
            assert self.backend.list_revisions(self.items[item]) == self.items_revisions[item]
        py.test.raises(NoSuchItemError, self.backend.list_revisions, self.newname)

    def test_current_revision(self):
        for item in self.items_revisions:
            assert self.backend.current_revision(self.items[item]) == self.items_revisions[item][0]
        py.test.raises(NoSuchItemError, self.backend.current_revision, self.newname)

    def test_has_revision(self):
        for item in self.items_revisions:
            for revno in self.items_revisions[item]:
                assert self.backend.has_revision(self.items[item], revno)
            assert not self.backend.has_revision(self.items[item], self.items_revisions[item][0] + 1)

        py.test.raises(NoSuchItemError, self.backend.has_revision, self.notexist, 1)

    def test_create_revision(self):
        current_revision = self.items_revisions[0][0]
        next_revision = self.items_revisions[0][0] + 1
        assert self.backend.create_revision(self.items[0], next_revision) == next_revision
        assert self.backend.has_revision(self.items[0], next_revision)
        assert self.backend.list_revisions(self.items[0]) == [next_revision] + self.items_revisions[0]
        assert self.backend.current_revision(self.items[0]) == current_revision
        assert self.backend.current_revision(self.items[0], includeEmpty=True) == next_revision

        py.test.raises(BackendError, self.backend.create_revision, self.items[0], current_revision)
        py.test.raises(NoSuchItemError, self.backend.create_revision, self.notexist, current_revision)

    def test_remove_revision(self):
        current_revision = self.items_revisions[0][0]
        next_revision = self.items_revisions[0][0] + 1
        assert self.backend.remove_revision(self.items[0], next_revision) == next_revision
        assert not self.backend.has_revision(self.items[0], next_revision)
        assert self.backend.list_revisions(self.items[0]) == self.items_revisions[0]
        assert self.backend.current_revision(self.items[0]) == current_revision
        assert self.backend.current_revision(self.items[0], includeEmpty=True) == current_revision

        py.test.raises(NoSuchRevisionError, self.backend.remove_revision, self.items[0], next_revision)
        py.test.raises(NoSuchItemError, self.backend.remove_revision, self.notexist, next_revision)

    def test_get_data_backend(self):
        self.backend.get_data_backend(self.items[0], 1)

    def test_get_metadata_backend(self):
        self.backend.get_metadata_backend(self.items[0], 1)

    def test_lock_unlock_item(self):
        self.backend.lock(self.newname)
        py.test.raises(LockingError, self.backend.lock, self.newname)
        self.backend.unlock(self.newname)
        self.backend.lock(self.newname, timeout=1)
        py.test.raises(LockingError, self.backend.lock, self.newname, 1)
        self.backend.unlock(self.newname)


class AbstractMetadataTest(object):

    key = 'abc'

    items = default_items
    items_revisions = default_items_revisions
    items_data = default_items_data
    items_metadata = default_items_metadata
    items_filter = default_items_filter

    backend = None

    @classmethod
    def init(cls, backend):
        cls.backend = backend
        create_data(cls)

    def teardown_class(self):
        remove_data(self)

    def test_get(self):
        metadata1 = self.backend.get_metadata_backend(self.items[0], 1)
        self._assertDict(metadata1, self.items_metadata[0][1])

    def test_set(self):
        metadata1 = self.backend.get_metadata_backend(self.items[0], 1)
        metadata1[self.key] = 'test'
        self.items_metadata[0][1][self.key] = 'test'
        metadata1.save()
        self._assertDict(metadata1, self.items_metadata[0][1])

    def test_del(self):
        metadata1 = self.backend.get_metadata_backend(self.items[0], 1)
        del metadata1[self.key]
        del self.items_metadata[0][1][self.key]
        metadata1.save()
        self._assertDict(metadata1, self.items_metadata[0][1])

    def _assertDict(self, dict1, dict2):
        for key in dict1:
            assert key in dict2
            if key != SIZE and key != EDIT_LOG_MTIME:
                assert dict1[key] == dict2[key]


# TODO: AbstractDataTest
