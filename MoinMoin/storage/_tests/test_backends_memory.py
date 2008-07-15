# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - MemoryBackend

    This defines tests for the MemoryBackend.

    ---

    @copyright: 2008 MoinMoin:ChristopherDenter,
                2008 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

import py

from MoinMoin.storage.backends.memory import MemoryBackend
from MoinMoin.storage import Backend, Item, Revision, NewRevision
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, \
                                   ItemAlreadyExistsError, \
                                   RevisionAlreadyExistsError, RevisionNumberMismatchError


class TestMemoryBackend(object):
    """
    Test the MemoryBackend
    """
    def __init__(self):
        self.backend = MemoryBackend()
        self.always_there = self.backend.create_item("always_there")  # for convenience
        self.always_there.create_revision(0)
        self.always_there.commit()

    # Test instance of MemoryBackend

    def test_create_item(self):
        my_item = self.backend.create_item("my_item")
        assert isinstance(my_item, Item)
        assert my_item.name == "my_item"

    def test_create_item_unicode(self):
        non_ascii = self.backend.create_item(u"äöüß")
        non_ascii.create_revision(0)  # You cannot commit an Item without a Revision on it.
        non_ascii.commit()
        assert isinstance(non_ascii, Item)
        assert non_ascii.name == u"äöüß"
        assert self.backend.has_item(u"äöüß")

    def test_create_item_invalid_itemname(self):
        py.test.raises(TypeError, self.backend.create_item, 42)

    def test_create_item_again(self):
        item1 = self.backend.create_item("item1")
        item1.create_revision(0)
        item1.commit()
        py.test.raises(ItemAlreadyExistsError, self.backend.create_item, "item1")

    def test_get_item(self):
        my_item = self.backend.get_item("always_there")
        assert my_item.name == self.always_there.name

    def test_get_item_that_doesnt_exist(self):
        py.test.raises(NoSuchItemError, self.backend.get_item, "i_do_not_exist")

    def test_has_item(self):
        my_item = self.backend.create_item("yep")
        my_item.create_revision(0)
        my_item.commit()
        assert self.backend.has_item("yep")

    def test_has_item_that_doesnt_exist(self):
        assert not self.backend.has_item("i_do_not_exist")

    def test_create_order(self):
        i1 = self.backend.create_item('1')
        i2 = self.backend.create_item('2')
        r1 = i1.create_revision(0)
        r2 = i2.create_revision(0)
        r1.write('1')
        r2.write('2')
        i2.commit()
        i1.commit()
        i1 = self.backend.get_item('1')
        i2 = self.backend.get_item('2')
        r1 = i1.get_revision(0)
        r2 = i2.get_revision(0)
        assert r1.read() == '1'
        assert r2.read() == '2'

    def test_mixed_commit_metadata1(self):
        i = self.backend.create_item('mixed1')
        i.create_revision(0)
        py.test.raises(RuntimeError, i.change_metadata)
        i.rollback()

    def test_mixed_commit_metadata2(self):
        i = self.backend.create_item('mixed2')
        i.change_metadata()
        py.test.raises(RuntimeError, i.create_revision, 0)
        i.publish_metadata()


    # Test instance of Item

    def test_item_metadata_change_and_publish(self):
        i = self.backend.create_item("test item metadata change")
        i.change_metadata()
        i["creator"] = "Vincent van Gogh"
        i.publish_metadata()
        i2 = self.backend.get_item("test item metadata change")
        assert i2["creator"] == "Vincent van Gogh"

    def test_item_metadata_invalid_change(self):
        i = self.backend.create_item("test item metadata invalid change")
        try:
            i["this should"] = "FAIL!"
            assert False  # There should have been an Exception due to i.change() missing.

        except AttributeError:
            pass  # We expected that Exception to be thrown. Everything fine.

    def test_item_metadata_without_publish(self):
        i = self.backend.create_item("test item metadata invalid change")
        i.change_metadata()
        i["change but"] = "don't publish"
        py.test.raises(NoSuchItemError, self.backend.get_item, "test item metadata invalid change")

    def test_item_metadata_change_after_read(self):
        i = self.backend.create_item("fooafoeofo")
        i.change_metadata()
        i["asd"] = "asd"
        i.publish_metadata()


    def test_item_create_revision(self):
        rev = self.always_there.create_revision(1)
        assert isinstance(rev, NewRevision)
        self.always_there.rollback()

    def test_item_commit_revision(self):
        test = self.backend.create_item("test#11")
        rev = test.create_revision(0)
        rev.write("python rocks")
        test.commit()
        rev = test.get_revision(0)
        assert rev.read() == "python rocks"

    def test_item_writing_data_multiple_times(self):
        test = self.backend.create_item("multiple")
        rev = test.create_revision(0)
        rev.write("Alle ")
        rev.write("meine ")
        rev.write("Entchen")
        test.commit()
        rev = test.get_revision(0)

        assert rev.read() == "Alle meine Entchen"

    def test_item_reading_chunks(self):
        test = self.backend.create_item("slices")
        rev = test.create_revision(0)
        rev.write("Alle meine Entchen")
        test.commit()
        rev = test.get_revision(0)

        chunk = rev.read(1)
        data = ""
        while chunk != "":
            data += chunk
            chunk = rev.read(1)

        assert data == "Alle meine Entchen"


    def test_item_get_revision(self):
        test = self.backend.create_item("test#12")
        rev = test.create_revision(0)
        rev.write("jefferson airplane rocks")
        test.commit()
        another_rev = test.get_revision(0)
        assert another_rev.read() == "jefferson airplane rocks"

    def test_item_list_revisions(self):
        test = self.backend.create_item("test#13")

        for revno in range(0, 10):
            rev = test.create_revision(revno)
            test.commit()

        assert test.list_revisions() == range(0, 10)

    def test_item_rename(self):
        ugly_name = self.backend.create_item("hans_wurst")
        ugly_name.create_revision(0)
        ugly_name.commit()
        ugly_name.rename("Arthur_Schopenhauer")
        assert ugly_name.name == "Arthur_Schopenhauer"
        assert self.backend.has_item("Arthur_Schopenhauer")
        assert not self.backend.has_item("hans_wurst")

    def test_item_rename_unicode(self):
        ugly_name = self.backend.create_item(u"hans_würstchen")
        ugly_name.create_revision(0)
        ugly_name.commit()
        ugly_name.rename(u"äöüßüöä")
        assert ugly_name.name == u"äöüßüöä"
        assert self.backend.has_item(u"äöüßüöä")
        assert not self.backend.has_item(u"hans_würstchen")

    def test_large(self):
        i = self.backend.create_item('large')
        r = i.create_revision(0)
        r['0'] = 'x' * 100
        r['1'] = 'y' * 200
        r['2'] = 'z' * 300
        for x in xrange(1000):
            r.write('lalala! ' * 10)
        i.commit()

        i = self.backend.get_item('large')
        r = i.get_revision(0)
        assert r['0'] == 'x' * 100
        assert r['1'] == 'y' * 200
        assert r['2'] == 'z' * 300
        for x in xrange(1000):
            assert r.read(8 * 10) == 'lalala! ' * 10
        assert r.read() == ''

    def test_metadata(self):
        i = self.backend.create_item('no metadata')
        i.create_revision(0)
        i.commit()
        i = self.backend.get_item('no metadata')
        py.test.raises(KeyError, i.__getitem__, 'asdf')

    def test_create_existing_1(self):
        i = self.backend.create_item('existing now')
        i.change_metadata()
        i.publish_metadata()
        py.test.raises(ItemAlreadyExistsError, self.backend.create_item, 'existing now')

    def test_create_existing_2(self):
        i1 = self.backend.create_item('existing now2')
        i2 = self.backend.create_item('existing now2')

        i1.change_metadata()
        i1.publish_metadata()

        i2.create_revision(0)
        py.test.raises(ItemAlreadyExistsError, i2.commit)




    # completely missing tests for revision and newrevision
