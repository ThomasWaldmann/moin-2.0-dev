# -*- coding: utf-8 -*-
"""
    MoinMoin - TestBackend

    This module provides class for testing backend API. This class tries 
    to cover sane backend usage examples.  
    
    This class should be inherited by descendant backend test classes.
    Add tests suitable for API here and for your backend in backend-specific 
    test class with this one inherited.
    
    ---

    @copyright: 2008 MoinMoin:PawelPacana
    @copyright: 2008 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import py.test, re

from MoinMoin.storage import Item, NewRevision
from MoinMoin.storage.error import NoSuchItemError, ItemAlreadyExistsError, NoSuchRevisionError
from MoinMoin.search import term

item_names = ("quite_normal",
              u"äöüßłóąćółąńśćżź",
              "with space",
              "name#special(characters?.\,",
              "very_long_name_" * 100 + "ending_1",
              "very_long_name_" * 100 + "ending_2",)

invalid_names = (42, object())

class BackendTest(object):
    """
    Generic class for backend tests.

    Creates a new backend for each test so they can assume to be
    sandboxed.
    """

    def __init__(self, backend, valid_names=item_names, invalid_names=invalid_names):
        self.backend = backend
        self.valid_names = valid_names
        self.invalid_names = invalid_names

    def setup_method(self, method):
        self.backend = self.create_backend()

    def teardown_method(self, method):
        self.kill_backend()
        self.backend = None

    def create_rev_item_helper(self, name):
        item = self.backend.create_item(name)
        item.create_revision(0)
        item.commit()
        return item

    def create_meta_item_helper(self, name):
        item = self.backend.create_item(name)
        item.change_metadata()
        item.publish_metadata()
        return item

    def create_item(self, name):
        item = self.backend.create_item(name)
        assert isinstance(item, Item)
        assert item.name == name
        item.create_revision(0)
        item.commit()
        assert self.backend.has_item(name)

    def get_item(self, name):
        item = self.backend.get_item(name)
        assert isinstance(item, Item)
        assert item.name == name

    def has_rename_item(self, old_name, new_name):
        item = self.backend.get_item(old_name)
        item.rename(new_name)
        assert item.name == new_name
        assert self.backend.has_item(new_name)
        assert not self.backend.has_item(old_name)

    def test_create_get_rename_get_item(self):
        for num, item_name in enumerate(self.valid_names):
            yield self.create_item, item_name
            yield self.get_item, item_name
            new_name = "renamed_item_%d" % num
            yield self.has_rename_item, item_name, new_name
            yield self.get_item, new_name
            
    def test_item_rename_to_existing(self):
        item1 = self.create_rev_item_helper("fresh_item")
        item2 = self.create_rev_item_helper("try to rename")
        py.test.raises(ItemAlreadyExistsError, item1.rename, item2.name)
        
    def rename_item_invalid_name(self, name, newname):
        item = self.backend.create_item(name)
        py.test.raises(TypeError, item.rename, newname)
        
    def test_item_rename_to_invalid(self):
        for num, invalid_name in enumerate(self.invalid_names):
            yield self.rename_item_invalid_name, "item_%s" % num, invalid_name
            
    def create_item_invalid_name(self, name):
        py.test.raises(TypeError, self.backend.create_item, name)

    def test_create_item_wrong_itemname(self):
        for item_name in self.invalid_names:
            yield self.create_item_invalid_name, item_name
            
    def test_create_order(self):
        item1 = self.backend.create_item('1')
        item2 = self.backend.create_item('2')
        revision1 = item1.create_revision(0)
        revision2 = item2.create_revision(0)
        revision1.write('1')
        revision2.write('2')
        item2.commit()
        item1.commit()
        item1 = self.backend.get_item('1')
        item2 = self.backend.get_item('2')
        revision1 = item1.get_revision(0)
        revision2 = item2.get_revision(0)
        assert revision1.read() == '1'
        assert revision2.read() == '2'

    def test_create_rev_item_again(self):
        self.create_rev_item_helper("item1")
        py.test.raises(ItemAlreadyExistsError, self.backend.create_item, "item1")
        
    def test_create_meta_item_again(self):
        self.create_meta_item_helper("item2")
        py.test.raises(ItemAlreadyExistsError, self.backend.create_item, "item2")

    def test_get_item_that_doesnt_exist(self):
        py.test.raises(NoSuchItemError, self.backend.get_item, "i_do_not_exist")

    def test_has_item(self):
        self.create_rev_item_helper("versioned")
        self.create_meta_item_helper("unversioned")
        assert self.backend.has_item("versioned")
        assert self.backend.has_item("unversioned")

    def test_has_item_that_doesnt_exist(self):
        assert not self.backend.has_item("i_do_not_exist")

    def test_search_simple(self):
        for name in ["songlist", "song lyric", "odd_SONG_item"]:
            self.create_rev_item_helper(name)
        self.create_meta_item_helper("new_song_player")
        query_string = u"song"
        query = term.Name(query_string, True)
        for num, item in enumerate(self.backend.search_item(query)):
            assert isinstance(item, Item)
            assert item.name.find(query_string) != -1
        assert num == 2

    def test_search_better(self):
        self.create_rev_item_helper('abcde')
        self.create_rev_item_helper('abcdef')
        self.create_rev_item_helper('abcdefg')
        self.create_rev_item_helper('abcdefgh')

        def _test_search(term, expected):
            found = list(self.backend.search_item(term))
            assert len(found) == expected

        # must be /part/ of the name
        yield _test_search, term.Name(u'AbCdEf', False), 3
        yield _test_search, term.Name(u'AbCdEf', True), 0
        yield _test_search, term.Name(u'abcdef', True), 3
        yield _test_search, term.NameRE(re.compile(u'abcde.*')), 4
        yield _test_search, term.NameFn(lambda n: n == 'abcdef'), 1

    def test_iteritems_1(self):
        for num in range(10, 20):
            self.create_rev_item_helper("item_" + str(num).zfill(2))
        for num in range(10):
            self.create_meta_item_helper("item_" + str(num).zfill(2))
        itemlist = [item.name for item in self.backend.iteritems()]
        itemlist.sort()
        for num, itemname in enumerate(itemlist):
            assert itemname == "item_" + str(num).zfill(2)
        assert len(itemlist) == 20
        
    def test_iteritems_2(self):
        self.create_rev_item_helper('abcdefghijklmn')
        count = 0
        for item in self.backend.iteritems():
            assert isinstance(item, Item)
            count += 1
        assert count > 0

    def test_existing_item_create_revision(self):
        self.create_rev_item_helper("existing")
        item = self.backend.get_item("existing")
        old_rev = item.get_revision(-1)
        rev = item.create_revision(old_rev.revno + 1)
        assert isinstance(rev, NewRevision)
        item.rollback()
        rev = item.get_revision(-1)
        assert old_rev == rev

    def test_new_item_create_revision(self):
        item = self.backend.create_item('internal')
        rev = item.create_revision(0)
        assert isinstance(rev, NewRevision)
        item.rollback()
        assert not self.backend.has_item(item.name)

    def test_item_commit_revision(self):
        item = self.backend.create_item("item#11")
        rev = item.create_revision(0)
        rev.write("python rocks")
        item.commit()
        rev = item.get_revision(0)
        assert rev.read() == "python rocks"

    def test_item_writing_data_multiple_times(self):
        item = self.backend.create_item("multiple")
        rev = item.create_revision(0)
        rev.write("Alle ")
        rev.write("meine ")
        rev.write("Entchen")
        item.commit()
        rev = item.get_revision(0)
        assert rev.read() == "Alle meine Entchen"

    def test_item_reading_chunks(self):
        item = self.backend.create_item("slices")
        rev = item.create_revision(0)
        rev.write("Alle meine Entchen")
        item.commit()
        rev = item.get_revision(0)
        chunk = rev.read(1)
        data = ""
        while chunk != "":
            data += chunk
            chunk = rev.read(1)
        assert data == "Alle meine Entchen"

    def test_item_get_revision(self):
        item = self.backend.create_item("item#12")
        rev = item.create_revision(0)
        rev.write("jefferson airplane rocks")
        item.commit()
        another_rev = item.get_revision(0)
        assert another_rev.read() == "jefferson airplane rocks"

    def test_item_list_revisions_with_revmeta_changes(self):
        item = self.backend.create_item("item_13")
        for revno in range(0, 10):
            rev = item.create_revision(revno)
            rev["revno"] = "%s" % revno
            item.commit()
        assert item.list_revisions() == range(0, 10)
    
    def test_item_list_revisions_with_revdata_changes(self):
        item = self.backend.create_item("item_13")
        for revno in range(0, 10):
            rev = item.create_revision(revno)
            rev.write("%s" % revno)
            item.commit()
        assert item.list_revisions() == range(0, 10)
    
    def test_item_list_revisions_without_changes(self):
        item = self.backend.create_item("item_13")
        for revno in range(0, 10):
            item.create_revision(revno)
            item.commit()
        assert item.list_revisions() == range(0, 10)

    def test_item_list_revisions_without_committing(self):
        item = self.backend.create_item("new_item_14")
        assert item.list_revisions() == []

    def test_mixed_commit_metadata1(self):
        item = self.backend.create_item('mixed1')
        item.create_revision(0)
        py.test.raises(RuntimeError, item.change_metadata)

    def test_mixed_commit_metadata2(self):
        item = self.backend.create_item('mixed2')
        item.change_metadata()
        py.test.raises(RuntimeError, item.create_revision, 0)

    def test_item_metadata_change_and_publish(self):
        item = self.backend.create_item("test item metadata change")
        item.change_metadata()
        item["creator"] = "Vincent van Gogh"
        item.publish_metadata()
        item2 = self.backend.get_item("test item metadata change")
        assert item2["creator"] == "Vincent van Gogh"

    def test_item_metadata_invalid_change(self):
        item = self.backend.create_item("test item metadata invalid change")
        try:
            item["this should"] = "FAIL!"
            assert False
        except AttributeError:
            pass
        
    def test_item_metadata_without_publish(self):
        item = self.backend.create_item("test item metadata invalid change")
        item.change_metadata()
        item["change but"] = "don't publish"
        py.test.raises(NoSuchItemError, self.backend.get_item, "test item metadata invalid change")

    def test_item_create_existing_mixed_1(self):
        item1 = self.backend.create_item('existing now 0')
        item1.change_metadata()
        item2 = self.backend.create_item('existing now 0')
        item1.publish_metadata()
        item2.create_revision(0)
        py.test.raises(ItemAlreadyExistsError, item2.commit)

    def test_item_create_existing_mixed_2(self):
        item1 = self.backend.create_item('existing now 0')
        item1.change_metadata()
        item2 = self.backend.create_item('existing now 0')
        item2.create_revision(0)
        item2.commit()
        py.test.raises(ItemAlreadyExistsError, item1.publish_metadata)
        
    def test_item_multiple_change_metadata_after_create(self):
        name = "foo"
        item1 = self.backend.create_item(name)
        item2 = self.backend.create_item(name)
        item1.change_metadata()
        item2.change_metadata()
        item1["a"] = "a"
        item2["a"] = "b"
        item1.publish_metadata()
        py.test.raises(ItemAlreadyExistsError, item2.publish_metadata)
        item = self.backend.get_item(name)
        assert item["a"] == "a"

    def test_metadata(self):
        self.create_rev_item_helper('no metadata')
        item = self.backend.get_item('no metadata')
        py.test.raises(KeyError, item.__getitem__, 'asdf')
        
    def test_revision(self):
        self.create_meta_item_helper('no revision')
        item = self.backend.get_item('no revision')
        py.test.raises(NoSuchRevisionError, item.get_revision, -1)
