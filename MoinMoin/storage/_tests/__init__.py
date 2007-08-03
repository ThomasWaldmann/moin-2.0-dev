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


items = ["New", "Test", ]
items_metadata = { EDIT_LOG_EXTRA: '',
            EDIT_LOG_ACTION: 'SAVE',
            EDIT_LOG_ADDR: '127.0.0.1',
            EDIT_LOG_HOSTNAME: 'localhost',
            EDIT_LOG_COMMENT: '',
            EDIT_LOG_USERID: '1180352194.13.59241',
            EDIT_LOG_MTIME: '',
            SIZE: '',
            'format': 'wiki',
            ACL: 'MoinPagesEditorGroup:read,write,delete,revert All:read',
            'language' : 'sv', }


class AbstractBackendTest(object):
    
    newname = "Blub"
    notexist = "Juhu"

    def test_name(self):
        assert self.backend.name == self.name

    def test_list_items(self):
        assert self.backend.list_items() == items
        assert self.backend.list_items({'format': 'wiki'}) == [items[1]]

    def test_has_item(self):
        assert self.backend.has_item(items[0])
        assert not self.backend.has_item(self.notexist)
        assert not self.backend.has_item("")

    def test_create_item(self):
        py.test.raises(BackendError, self.backend.create_item, items[1])
        self.backend.create_item(self.newname)
        assert self.backend.has_item(self.newname)
        assert self.backend.list_items() == [self.newname] + items
        assert self.backend.current_revision(self.newname) == 0
    
    def test_remove_item(self):
        self.backend.remove_item(self.newname)
        assert not self.backend.has_item(self.newname)
        assert self.backend.list_items() == items
        py.test.raises(NoSuchItemError, self.backend.remove_item, self.newname)

    def test_rename_item(self):
        py.test.raises(BackendError, self.backend.rename_item, items[0], "")
        py.test.raises(BackendError, self.backend.rename_item, items[0], items[0])
        py.test.raises(BackendError, self.backend.rename_item, items[0], items[1])

        self.backend.rename_item(items[0], self.newname)
        assert self.backend.has_item(self.newname)
        assert not self.backend.has_item(items[0])
        newitems = items[:]
        newitems.remove(items[0])
        newitems.insert(0, self.newname)
        assert self.backend.list_items() == newitems
        
        self.backend.rename_item(self.newname, items[0])
        assert not self.backend.has_item(self.newname)
        assert self.backend.has_item(items[0])
        assert self.backend.list_items() == items

    def test_list_revisions(self):
        assert self.backend.list_revisions(items[0]) == [1]
        assert self.backend.list_revisions(items[1]) == [2, 1]
        py.test.raises(NoSuchItemError, self.backend.list_revisions, self.newname)

    def test_current_revision(self):
        assert self.backend.current_revision(items[0]) == 1
        assert self.backend.current_revision(items[1]) == 2

    def test_has_revision(self):
        assert self.backend.has_revision(items[0], 0)
        assert self.backend.has_revision(items[0], 1)
        assert not self.backend.has_revision(items[0], 2)
        assert self.backend.has_revision(items[1], 0)
        assert self.backend.has_revision(items[1], 1)
        assert self.backend.has_revision(items[1], 2)
        assert not self.backend.has_revision(items[1], 3)

        py.test.raises(NoSuchItemError, self.backend.has_revision, self.notexist, 1)

    def test_create_revision(self):
        assert self.backend.create_revision(items[0], 2) == 2
        assert self.backend.has_revision(items[0], 2)
        assert self.backend.list_revisions(items[0]) == [2, 1]
        assert self.backend.current_revision(items[0]) == 1
        assert self.backend.current_revision(items[0], includeEmpty=True) == 2

        py.test.raises(BackendError, self.backend.create_revision, items[0], 1)
        py.test.raises(NoSuchItemError, self.backend.create_revision, self.notexist, 1)

    def test_remove_revision(self):
        assert self.backend.remove_revision(items[0], 2) == 2
        assert not self.backend.has_revision(items[0], 2)
        assert self.backend.list_revisions(items[0]) == [1]
        assert self.backend.current_revision(items[0]) == 1
        assert self.backend.current_revision(items[0], includeEmpty=True) == 1

        py.test.raises(NoSuchRevisionError, self.backend.remove_revision, items[0], 4)
        py.test.raises(NoSuchItemError, self.backend.remove_revision, self.notexist, 4)

    def test_get_data_backend(self):
        self.backend.get_data_backend(items[0], 1)

    def test_get_metadata_backend(self):
        self.backend.get_metadata_backend(items[0], 1)

    def test_lock_unlock_item(self):
        self.backend.lock(self.newname)
        py.test.raises(LockingError, self.backend.lock, self.newname)
        self.backend.unlock(self.newname)
        self.backend.lock(self.newname, timeout=1)
        py.test.raises(LockingError, self.backend.lock, self.newname, 1)
        self.backend.unlock(self.newname)


class AbstractMetadataTest(object):

    key = 'abc'
    totest = items[1]
    tometadata = items_metadata

    def test_get(self):
        metadata1 = self.backend.get_metadata_backend(self.totest, 2)
        self._assertDict(metadata1, self.tometadata)

    def test_set(self):
        metadata1 = self.backend.get_metadata_backend(self.totest, 2)
        metadata1[self.key] = 'test'
        self.tometadata[self.key] = 'test'
        metadata1.save()
        self._assertDict(metadata1, self.tometadata)

    def test_del(self):
        metadata1 = self.backend.get_metadata_backend(self.totest, 2)
        del metadata1[self.key]
        del self.tometadata[self.key]
        metadata1.save()
        self._assertDict(metadata1, self.tometadata)

    def _assertDict(self, dict1, dict2):
        for key in dict1:
            assert key in dict2
            if key != SIZE and key != EDIT_LOG_MTIME:
                assert dict1[key] == dict2[key]

