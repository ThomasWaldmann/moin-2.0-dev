"""
    MoinMoin 1.6 compatible storage backend

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""


import unittest

from MoinMoin.storage.storage16 import UserStorage
from MoinMoin.storage.error import NotImplementedError
from MoinMoin.storage.error import StorageError

class TestUserBackend(unittest.TestCase):
    
    datadir = "data/user"
    
    names = [ "1180352194.13.59241", "1180424607.34.55818", "1180424618.59.18110" ]
    
    metadata = {u'aliasname' : u'',
                u'bookmarks' : {},
                u'css_url' : u'',
                u'date_fmt' : u'',
                u'datetime_fmt' : u'',
                u'disabled' : u'0',
                u'edit_on_doubleclick' : u'0',
                u'edit_rows' : u'20',
                u'editor_default' : u'text',
                u'editor_ui' : u'freechoice',
                u'email' : u'h_wendel@cojobo.net',
                u'enc_password' : u'{SHA}ujz/zJOpLgj4LDPFXYh2Zv3zZK4=',
                u'language': u'',
                u'last_saved': u'1180435816.61',
                u'mailto_author' : u'0',
                u'name': u'HeinrichWendel',
                u'quicklinks': [u'www.google.de', u'www.test.de', u'WikiSandBox'],
                u'remember_last_visit': u'0',
                u'remember_me' : u'1',
                u'show_comments' : u'0',
                u'show_fancy_diff' : u'1',
                u'show_nonexist_qm' : u'0',
                u'show_page_trail' : u'1',
                u'show_toolbar' : u'1',
                u'show_topbottom' : u'0',
                u'subscribed_pages' : [u'WikiSandBox', u'FrontPage2'],
                u'theme_name' : u'modern',
                u'tz_offset' : u'0',
                u'want_trivial' : u'0',
                u'wikiname_add_spaces' : u'0'
                }
    
    backend = None
    
    def setUp(self):
        self.backend = UserStorage("data/user/")
    
    def tearDown(self):
        self.backend = None
        
    def test_list_revisions(self):
        self.assertEquals(self.backend.list_revisions(self.names[0]), [1])
        
    def test_current_revision(self):
        self.assertEquals(self.backend.current_revision(self.names[0]), 1)
        
    def test_create_revision(self):
        try:
            self.backend.create_revision(self.names[0], 1)
            self.fail()
        except NotImplementedError:
            self.assertTrue(True)
    
    def test_remove_revision(self):
        try:
            self.backend.remove_revision(self.names[0], 2)
            self.fail()
        except NotImplementedError:
            self.assertTrue(True)
    
    def test_get_data_backend(self):
        try:
            self.backend.get_data_backend(self.names[0], 1, "a")
            self.fail()
        except NotImplementedError:
            self.assertTrue(True)
    
    def test_list_items(self):
        self.assertEquals(self.backend.list_items(), self.names)
    
    def test_has_item(self):
        self.assertTrue(self.backend.has_item(self.names[0]))
        self.assertFalse(self.backend.has_item("asdf"));
  
    def test_create_and_remove_item(self):
        self.backend.create_item("test");
        self.assertTrue(self.backend.has_item(self.names[0]))
        
        try:
            self.backend.create_item(self.names[0]);
            self.fail()
        except StorageError:
            self.assertTrue(True)

        self.backend.remove_item("test");
        self.assertFalse(self.backend.has_item("test"))
        
        try:
            self.backend.remove_item("blub");
            self.fail()
        except StorageError:
            self.assertTrue(True)
    
    def test_get_metadata(self):
        self.__assertDicts(self.backend.get_metadata(self.names[0], 1), self.metadata)
    
    def test_set_metadata(self):
        self.backend.set_metadata(self.names[0], 0, "aliasname", "test")
        self.metadata["aliasname"] = "test";        
        self.__assertDicts(self.backend.get_metadata(self.names[0], 1), self.metadata)
        self.backend.set_metadata(self.names[0], 0, "aliasname", "")
        self.metadata["aliasname"] = ""
        self.__assertDicts(self.backend.get_metadata(self.names[0], 1), self.metadata)
    
    def test_remove_metadata(self):
        self.backend.set_metadata(self.names[0], 0, "battle", "test")
        self.metadata["battle"] = "test";        
        self.__assertDicts(self.backend.get_metadata(self.names[0], 1), self.metadata)
        self.backend.remove_metadata(self.names[0], 0, "battle")
        del self.metadata["battle"]        
        self.__assertDicts(self.backend.get_metadata(self.names[0], 1), self.metadata)
    
    def __assertDicts(self, dict1, dict2):
        for key, value in dict1.iteritems():
            self.assertEquals(dict2[key], value)
    
if __name__ == "__main__":
        unittest.main()