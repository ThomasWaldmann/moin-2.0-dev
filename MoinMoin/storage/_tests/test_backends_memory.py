# -*- coding: utf-8 -*- 
"""
    MoinMoin - Test - MemoryBackend

    This defines tests for the MemoryBackend.

    ---

    @copyright: 2008 MoinMoin:ChristopherDenter,
                2008 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""


from MoinMoin.storage import Backend, Item, Revision, NewRevision
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, \
                                   ItemAlreadyExistsError, \
                                   RevisionAlreadyExistsError, RevisionNumberMismatchError

from MoinMoin.storage.backends.memory import MemoryBackend

import py

class TestMemoryBackend(object):
    """
    Test the MemoryBackend
    """
    def __init__(self):
        self.memb = MemoryBackend()
        self.always_there = self.memb.create_item("always_there")  # for convenience

    def test_create_item(self):
        my_item = self.memb.create_item("my_item")
        assert isinstance(my_item, Item)
        assert my_item.name == "my_item"

    def test_create_item(self):
        non_ascii = self.memb.create_item(u"äöüß")
        assert isinstance(non_ascii, Item)
        assert non_ascii.name == u"äöüß"
        assert self.memb.has_item(u"äöüß")

    def test_create_item_wrong_itemname(self):
        py.test.raises(TypeError, self.memb.create_item, 42)

    def test_create_item_again(self):
        item1 = self.memb.create_item("item1")
        py.test.raises(ItemAlreadyExistsError, self.memb.create_item, "item1")

    def test_get_item(self):
        my_item = self.memb.get_item("always_there")
        assert my_item.name == self.always_there.name

    def test_get_item_that_doesnt_exist(self):
        py.test.raises(NoSuchItemError, self.memb.get_item, "i_do_not_exist")

    def test_has_item(self):
        my_item = self.memb.create_item("yep")
        assert self.memb.has_item("yep")

    def test_has_item_that_doesnt_exist(self):
        assert not self.memb.has_item("i_do_not_exist")

    def test_item_create_revision(self):
        rev = self.always_there.create_revision(0)
        assert isinstance(rev, NewRevision)

    def test_revision_write_data_without_committing(self):
        test = self.memb.create_item("test#10")
        rev = test.create_revision(0)
        rev.write_data("python rocks")
        assert rev.read_data() is None      # Since we havn't committed it yet.

    def test_item_commit_revision(self):
        test = self.memb.create_item("test#11")
        rev = test.create_revision(0)
        rev.write_data("python rocks")
        test.commit()
        assert rev.read_data() == "python rocks"

    def test_item_get_revision(self):
        test = self.memb.create_item("test#12")
        rev = test.create_revision(0)
        rev.write_data("jefferson airplane rocks")
        test.commit()
        another_rev = test.get_revision(0)
        assert another_rev.read_data() == "jefferson airplane rocks"

    def test_item_list_revisions(self):
        test = self.memb.create_item("test#13")

        for revno in range(0, 10):
            rev = test.create_revision(revno)
            test.commit()

        assert test.list_revisions() == range(0,10)

    def test_item_rename(self):
        ugly_name = self.memb.create_item("hans_wurst")
        ugly_name.rename("Arthur_Schopenhauer")
        assert ugly_name.name == "Arthur_Schopenhauer"
        assert self.memb.has_item("Arthur_Schopenhauer")
        assert not self.memb.has_item("hans_wurst")

    def test_item_rename_unicode(self):
        ugly_name = self.memb.create_item(u"hans_würstchen")
        ugly_name.rename(u"äöüßüöä")
        assert ugly_name.name == u"äöüßüöä"
        assert self.memb.has_item(u"äöüßüöä")
        assert not self.memb.has_item(u"hans_würstchen")



    # completely missing tests for revision and newrevision
