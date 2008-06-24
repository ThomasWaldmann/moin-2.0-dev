# -*- coding: utf-8 -*- 
"""
    MoinMoin - TestBackend

    Simple test class for subclassing in specific backend tests.
    Remember to set up your backend environment with items: either
    default provided here or yours.

    ---

    @copyright: 2008 MoinMoin:PawelPacana
    @copyright: 2008 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.storage import Backend, Item, Revision, NewRevision
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, \
    ItemAlreadyExistsError, RevisionAlreadyExistsError, RevisionNumberMismatchError

import py

default_items = {   
    'NewPage': [   
        ('0', {}, "This is NewPage content. A to jest też zawartość."),
        ('1', {}, "Dummy message") 
    ], 
    'Test': [
        ('0', {}, "First of all, people don't wear enough hats!"),
        ('1', {}, "Soft\ncushions.") 
    ],                
}


class BackendTest(object):
    """
    Generic class for backend tests.
    """
    def __init__(cls, backend, items=None):
        cls.backend = backend
        cls.items = items or default_items

    def test_create_item(cls):
        for x in ("my_item", u"äöüß", "with space"):
            yield cls.create_item, x


    def create_item(cls, name):        
        new_item = cls.backend.create_item(name)
        assert isinstance(new_item, Item)
        assert new_item.name == name


    def test_create_item_wrong_itemname(cls):
        py.test.raises(TypeError, cls.backend.create_item, 42)


    def test_create_item_again(cls):
        item1 = cls.backend.create_item("item1")
        py.test.raises(ItemAlreadyExistsError, cls.backend.create_item, "item1")


    def test_get_item(cls):
        for x in cls.items.keys():
            yield cls.get_item, x


    def get_item(cls, name):
        my_item = cls.backend.get_item(name)
        assert isinstance(my_item, Item)
        assert my_item.name == cls.name


    def test_get_item_that_doesnt_exist(cls):
        py.test.raises(NoSuchItemError, cls.backend.get_item, "i_do_not_exist")


    def test_has_item(cls):
        my_item = cls.backend.create_item("yep")
        assert cls.backend.has_item("yep")


    def test_has_item_that_doesnt_exist(cls):
        assert not cls.backend.has_item("i_do_not_exist")


    def test_item_create_revision(cls):
        item = cls.backend.create_item('internal')
        rev = item.create_revision(0)
        assert isinstance(rev, NewRevision)


    def test_item_commit_revision(cls):
        test = cls.backend.create_item("test#11")
        rev = test.create_revision(0)
        rev.write("python rocks")
        test.commit()
        rev = test.get_revision(0)
        assert rev.read() == "python rocks"


    def test_item_writing_data_multiple_times(cls):
        test = cls.backend.create_item("multiple")
        rev = test.create_revision(0)
        rev.write("Alle ")
        rev.write("meine ")
        rev.write("Entchen")
        test.commit()
        rev = test.get_revision(0)

        chunk = rev.read(1)
        data = ""
        while chunk != "":
            data += chunk
            chunk = rev.read(1)

        assert data == "Alle meine Entchen"


    def test_item_reading_chunks(cls):
        test = cls.backend.create_item("slices")
        rev = test.create_revision(0)
        rev.write("Alle meine Entchen")
        test.commit()
        rev.read_data(2)


    def test_item_get_revision(cls):
        test = cls.backend.create_item("test#12")
        rev = test.create_revision(0)
        rev.write("jefferson airplane rocks")
        test.commit()
        another_rev = test.get_revision(0)
        assert another_rev.read() == "jefferson airplane rocks"


    def test_item_list_revisions(cls):
        test = cls.backend.create_item("test#13")

        for revno in range(0, 10):
            rev = test.create_revision(revno)
            test.commit()

        assert test.list_revisions() == range(0,10)


    def test_item_rename(cls):
        ugly_name = cls.backend.create_item("hans_wurst")
        ugly_name.rename("Arthur_Schopenhauer")
        assert ugly_name.name == "Arthur_Schopenhauer"
        assert cls.backend.has_item("Arthur_Schopenhauer")
        assert not cls.backend.has_item("hans_wurst")


    def test_item_rename_unicode(cls):
        ugly_name = cls.backend.create_item(u"hans_würstchen")
        ugly_name.rename(u"äöüßüöä")
        assert ugly_name.name == u"äöüßüöä"
        assert cls.backend.has_item(u"äöüßüöä")
        assert not cls.backend.has_item(u"hans_würstchen")


    #XXX: completely missing tests for revision and newrevision
