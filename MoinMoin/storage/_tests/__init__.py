"""
    Common stuff for storage unit tests.

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import py.test
import time

from MoinMoin.storage.error import BackendError, LockingError, NoSuchItemError, NoSuchRevisionError
from MoinMoin.storage.external import ACL
from MoinMoin.support.python_compatibility import set

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
default_items_metadata[0][1] = {'format': 'wiki',
            ACL: ['MoinPagesEditorGroup:read,write,delete,revert All:read', 'HeinrichWendel:read'],
            'language': 'sv', }

default_items_metadata[0][2] = default_items_metadata[0][1]
default_items_metadata[1] = {}
default_items_metadata[1][1] = {}
default_items_metadata[1][2] = default_items_metadata[1][1]
default_items_metadata[1][3] = default_items_metadata[1][1]

default_items_filters = [['format', 'wiki', default_items[0]], ['language', 'sv', default_items[0]]]


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


class AbstractTest(object):

    @classmethod
    def init(cls, backend, items=None, revisions=None, data=None, metadata=None, filters=None, name=None, newname=None, notexist=None, key=None):
        cls.backend = backend

        cls.items = items or default_items

        if revisions is None:
            cls.items_revisions = default_items_revisions
        else:
            cls.items_revisions = revisions

        if data is None:
            cls.items_data = default_items_data
        else:
            cls.items_data = data

        if metadata is None:
            cls.items_metadata = default_items_metadata
        else:
            cls.items_metadata = metadata

        if filters is None:
            cls.items_filters = default_items_filters
        else:
            cls.items_filters = filters

        cls.name = name or "pages"
        cls.newname = newname or "Blub"
        cls.notexist = notexist or "Juhu"
        cls.key = key or "key"

    def teardown_class(self):
        remove_data(self)


class AbstractBackendTest(AbstractTest):

    def test_name(self):
        assert self.backend.name == self.name

    def test_list_items(self):
        assert self.backend.list_items() == self.items
        for filter in self.items_filters:
            assert self.backend.list_items({filter[0]: filter[1]}) == [filter[2]]

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

        if self.items_revisions:
            assert self.backend.list_revisions(self.newname) == []
            assert self.backend.current_revision(self.newname) == 0
        else:
            assert self.backend.list_revisions(self.newname) == [1]
            assert self.backend.current_revision(self.newname) == 1

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
        if self.items_revisions:
            for item in self.items_revisions:
                assert self.backend.list_revisions(self.items[item]) == self.items_revisions[item]
            py.test.raises(NoSuchItemError, self.backend.list_revisions, self.newname)
        else:
            for item in self.items:
                assert self.backend.list_revisions(item) == [1]

    def test_current_revision(self):
        if self.items_revisions:
            for item in self.items_revisions:
                assert self.backend.current_revision(self.items[item]) == self.items_revisions[item][0]
            py.test.raises(NoSuchItemError, self.backend.current_revision, self.newname)
        else:
            for item in self.items:
                assert self.backend.current_revision(item) == 1

    def test_has_revision(self):
        if self.items_revisions:
            for item in self.items_revisions:
                for revno in self.items_revisions[item]:
                    assert self.backend.has_revision(self.items[item], revno)
                assert not self.backend.has_revision(self.items[item], self.items_revisions[item][0] + 1)
                assert self.backend.has_revision(self.items[item], 0)
                assert self.backend.has_revision(self.items[item], -1)
                assert not self.backend.has_revision(self.items[item], -2)

            py.test.raises(NoSuchItemError, self.backend.has_revision, self.notexist, 1)
        else:
            for item in self.items:
                assert self.backend.has_revision(item, 0)
                assert self.backend.has_revision(item, 1)
                assert not self.backend.has_revision(item, -1)
                assert not self.backend.has_revision(item, 2)
                assert not self.backend.has_revision(item, -2)

    def test_create_revision(self):
        if self.items_revisions:
            current_revision = self.items_revisions[0][0]
            next_revision = self.items_revisions[0][0] + 1
            assert self.backend.create_revision(self.items[0], next_revision) == next_revision
            assert self.backend.has_revision(self.items[0], next_revision)
            assert self.backend.list_revisions(self.items[0]) == [next_revision] + self.items_revisions[0]
            assert self.backend.current_revision(self.items[0]) == current_revision
            assert self.backend.current_revision(self.items[0], includeEmpty=True) == next_revision

            py.test.raises(BackendError, self.backend.create_revision, self.items[0], current_revision)
            py.test.raises(BackendError, self.backend.create_revision, self.items[0], -1)
            py.test.raises(BackendError, self.backend.create_revision, self.items[0], -2)
            py.test.raises(NoSuchItemError, self.backend.create_revision, self.notexist, current_revision)

    def test_remove_revision(self):
        if self.items_revisions:
            current_revision = self.items_revisions[0][0]
            next_revision = self.items_revisions[0][0] + 1
            assert self.backend.remove_revision(self.items[0], next_revision) == next_revision
            assert not self.backend.has_revision(self.items[0], next_revision)
            assert self.backend.list_revisions(self.items[0]) == self.items_revisions[0]
            assert self.backend.current_revision(self.items[0]) == current_revision
            assert self.backend.current_revision(self.items[0], includeEmpty=True) == current_revision

            py.test.raises(NoSuchRevisionError, self.backend.remove_revision, self.items[0], next_revision)
            py.test.raises(BackendError, self.backend.remove_revision, self.items[0], -1)
            py.test.raises(BackendError, self.backend.remove_revision, self.items[0], -2)
            py.test.raises(NoSuchItemError, self.backend.remove_revision, self.notexist, next_revision)

    def test_get_data_backend(self):
        if self.items_data:
            self.backend.get_data_backend(self.items[0], 1)

    def test_get_metadata_backend(self):
        if self.items_metadata:
            self.backend.get_metadata_backend(self.items[0], 1)

    def test_lock_unlock_item(self):
        self.backend.lock(self.newname)
        py.test.raises(LockingError, self.backend.lock, self.newname)
        self.backend.unlock(self.newname)
        self.backend.lock(self.newname, timeout=1)
        py.test.raises(LockingError, self.backend.lock, self.newname, 1)
        self.backend.unlock(self.newname)

    def test_news(self):
        starttime = time.time()
        self.backend.create_item(self.newname)
        if self.items_revisions:
            self.backend.create_revision(self.newname, 0)
        metadata = self.backend.get_metadata_backend(self.newname, 0)
        metadata["test"] = "test"
        metadata.save()
        news = self.backend.news(starttime)
        assert len(news) == 1
        assert len(news[0]) == 3
        assert news[0][2] == self.newname
        assert news[0][1] == 1
        self.backend.remove_item(self.newname)
        news = self.backend.news()
        newlist = []
        oldtime = 0
        for item in news:
            newlist.append(str(item[1]) + item[2])
            if oldtime == 0:
                continue
            assert oldtime >= item[0]
            oldtime = item[0]
        assert len(set(newlist)) == len(newlist)


class AbstractMetadataTest(AbstractTest):

    def test_get(self):
        if self.items_revisions:
            for item in self.items_revisions:
                for revno in self.items_revisions[item]:
                    metadata1 = self.backend.get_metadata_backend(self.items[item], revno)
                    self.assertDict(metadata1, self.items_metadata[item][revno])
        else:
            for itemno in range(1, len(self.items)):
                metadata1 = self.backend.get_metadata_backend(self.items[itemno], 1)
                self.assertDict(metadata1, self.items_metadata[itemno][1])

    def test_set(self):
        metadata1 = self.backend.get_metadata_backend(self.items[0], 1)
        metadata1[self.key] = 'test'
        self.items_metadata[0][1][self.key] = 'test'
        metadata1.save()
        self.assertDict(metadata1, self.items_metadata[0][1])

    def test_del(self):
        metadata1 = self.backend.get_metadata_backend(self.items[0], 1)
        del metadata1[self.key]
        del self.items_metadata[0][1][self.key]
        metadata1.save()
        self.assertDict(metadata1, self.items_metadata[0][1])

    def assertDict(self, dict1, dict2):
        for key in dict1:
            assert key in dict2
            assert dict1[key] == dict2[key]


class AbstractDataTest(AbstractTest):

    def test_read(self):
        if self.items_revisions:
            for item in self.items_revisions:
                for revno in self.items_revisions[item]:
                    assert self.backend.get_data_backend(self.items[item], revno).read() == self.items_data[item][revno]
        else:
            for itemno in range(1, len(self.items)):
                assert self.backend.get_data_backend(self.items[itemno], 1).read() == self.items_data[itemno][1]

    def test_write(self):
        newdata = "testdata\nwriteit\nyes"
        data_backend = self.backend.get_data_backend(self.items[0], 1)
        data_backend.write(newdata)
        data_backend.close()
        assert data_backend.read() == newdata
        data_backend.close()

    def test_tell_seek(self):
        data_backend = self.backend.get_data_backend(self.items[0], 1)
        assert data_backend.tell() == 0
        data_backend.seek(5)
        assert data_backend.tell() == 5
        data_backend.close()

