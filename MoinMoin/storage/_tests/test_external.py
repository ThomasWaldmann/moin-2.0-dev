"""
    MoinMoin external interfaces tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.storage._tests import AbstractTest, create_data
from MoinMoin.storage._tests.test_backends_moin16 import get_page_backend, setup_module, teardown_module

from MoinMoin.storage.external import ItemCollection, Item, Revision
from MoinMoin.storage.error import BackendError, NoSuchItemError, NoSuchRevisionError, LockingError


class TestItemCollection(AbstractTest):

    def setup_class(self):
        AbstractTest.init(get_page_backend())
        create_data(self)
        self.item_collection = ItemCollection(self.backend, self.request)

    def test_has_item(self):
        assert self.items[0] in self.item_collection
        assert not self.notexist in self.item_collection
        assert not "" in self.item_collection

    def test_keys(self):
        assert self.item_collection.keys() == self.items
        for filter in self.items_filters:
            assert self.item_collection.keys({filter[0]: filter[1]}) == [filter[2]]

    def test_get_item(self):
        item = self.item_collection[self.items[0]]
        assert isinstance(item, Item)
        assert item.name == self.items[0]
        assert item._backend.name == self.name
        py.test.raises(NoSuchItemError, lambda: self.item_collection[self.notexist])

    def test_new_item(self):
        item = self.item_collection.new_item(self.newname)
        assert isinstance(item, Item)
        assert item.name == self.newname
        item.metadata.keys()
        item.keys()
        py.test.raises(BackendError, self.item_collection.new_item, self.items[0])
        assert self.newname in self.item_collection

    def test_delete_item(self):
        del self.item_collection[self.newname]
        assert not self.newname in self.item_collection

    def test_rename_item(self):
        self.item_collection.rename_item(self.items[0], self.newname)
        assert self.newname in self.item_collection
        assert not self.items[0] in self.item_collection
        self.item_collection.rename_item(self.newname, self.items[0])
        assert self.items[0] in self.item_collection
        assert not self.newname in self.item_collection

    def test_copy_item(self):
        self.item_collection.copy_item(self.items[0], self.newname)
        assert self.newname in self.item_collection
        assert self.items[0] in self.item_collection
        del self.item_collection[self.newname]
        assert not self.newname in self.item_collection
        assert self.items[0] in self.item_collection
        py.test.raises(BackendError, self.item_collection.copy_item, self.items[0], "")
        py.test.raises(BackendError, self.item_collection.copy_item, self.items[0], self.items[0])
        py.test.raises(BackendError, self.item_collection.copy_item, self.items[0], self.items[1])
        py.test.raises(BackendError, self.item_collection.copy_item, self.newname, self.items[1])


class TestItem(AbstractTest):

    def setup_class(self):
        AbstractTest.init(get_page_backend())
        create_data(self)
        self.item = ItemCollection(self.backend, self.request)[self.items[0]]

    def test_has_revision(self):
        assert 1 in self.item
        assert 2 in self.item
        assert not 3 in self.item
        assert 0 in self.item
        assert -1 in self.item
        assert not -2 in self.item

    def test_get_revision(self):
        revision = self.item[1]
        assert isinstance(revision, Revision)
        assert revision.revno == 1
        revision = self.item[0]
        assert isinstance(revision, Revision)
        assert revision.revno == 2
        py.test.raises(NoSuchRevisionError, lambda: self.item[5])
        py.test.raises(NoSuchRevisionError, lambda: self.item[-2])

    def test_keys(self):
        assert self.item.keys() == [2, 1]

    def test_add_revision(self):
        self.item.lock = True
        assert self.item.current == 2
        assert isinstance(self.item.new_revision(), Revision)
        assert self.item.current == 3
        assert 3 in self.item
        assert isinstance(self.item.new_revision(4), Revision)
        assert 4 in self.item
        assert self.item.current == 4
        self.item.lock = False

    def test_del_revision(self):
        self.item.lock = True
        del self.item[4]
        assert self.item.current == 3
        del self.item[3]
        assert self.item.current == 2
        assert not 3 in self.item
        assert not 4 in self.item
        py.test.raises(NoSuchRevisionError, lambda: self.item[5])
        py.test.raises(BackendError, self.item.new_revision, 1)
        self.item.lock = False

    def test_acl(self):
        from MoinMoin.security import AccessControlList
        assert isinstance(self.item.acl, AccessControlList)

    def test_edit_lock(self):
        assert self.item.edit_lock == (False, 0.0, "", "", "")
        self.item.edit_lock = True
        edit_lock = self.item.edit_lock
        assert edit_lock[0]
        assert isinstance(edit_lock[1], float)
        assert isinstance(edit_lock[2], str)
        assert isinstance(edit_lock[3], str)
        assert isinstance(edit_lock[4], str)
        self.item.edit_lock = False
        assert self.item.edit_lock == (False, 0.0, "", "", "")

    def test_lock(self):
        assert not self.item.lock
        self.item.lock = True
        assert self.item.lock
        self.item.lock = False
        assert not self.item.lock
        py.test.raises(LockingError, self.item.new_revision, 1)
        py.test.raises(LockingError, self.item[0].data.write, "test")


class TestRevision(AbstractTest):

    def setup_class(self):
        AbstractTest.init(get_page_backend())
        create_data(self)
        self.item = ItemCollection(self.backend, self.request)[self.items[0]]

    def test_data(self):
        self.item[0].data

    def test_metadata(self):
        self.item[0].metadata

    def test_acl(self):
        self.item.lock = True
        assert self.item[0].acl == ['MoinPagesEditorGroup:read,write,delete,revert All:read', 'HeinrichWendel:read']
        self.item[0].acl = ""
        self.item[0].save()
        assert self.item[0].acl == ['']
        self.item[0].acl = ['MoinPagesEditorGroup:read,write,delete,revert All:read', 'HeinrichWendel:read']
        self.item[0].save()
        assert self.item[0].acl == ['MoinPagesEditorGroup:read,write,delete,revert All:read', 'HeinrichWendel:read']
        self.item.lock = False

    def test_deleted(self):
        self.item.lock = True
        assert not self.item[0].deleted
        self.item[0].deleted = True
        self.item[0].save()
        self.item.lock = False
        self.item.lock = True
        assert self.item[0].deleted
        self.item[0].deleted = False
        self.item[0].save()
        self.item.lock = False
        self.item.lock = True
        assert not self.item[0].deleted
        self.item.lock = False

    def test_size(self):
        assert isinstance(self.item[0].size, long)

    def test_edit_log(self):
        assert self.item[0].action == ""
        assert isinstance(self.item[0].addr, str)
        assert isinstance(self.item[0].hostname, str)
        assert isinstance(self.item[0].userid, str)
        assert self.item[0].extra == ""
        assert self.item[0].comment == ""
        assert isinstance(self.item[0].mtime, float)
        self.item.lock = True
        self.item[0].data.write("hallo")
        self.item[0].save()
        self.item.lock = False
        assert self.item[0].action == "SAVE"
        assert isinstance(self.item[0].addr, str)
        assert isinstance(self.item[0].hostname, str)
        assert isinstance(self.item[0].userid, str)
        assert self.item[0].extra == ""
        assert self.item[0].comment == ""
        assert isinstance(self.item[0].mtime, float)
