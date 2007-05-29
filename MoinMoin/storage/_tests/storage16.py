"""
    MoinMoin 1.6 compatible storage backend

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""


import unittest

from MoinMoin.storage.storage16 import UserStorage
from MoinMoin.storage.error import NotImplementedError

class TestUserBackend(unittest.TestCase):
    
    backend = None
    
    def setUp(self):
        self.backend = UserStorage()
    
    def tearDown(self):
        self.backend = None
        
    def test_list_revisions(self):
        self.assertEquals(self.backend.list_revisions("1180352194.13.59241"), [1])
        
    def test_current_revision(self):
        self.assertEquals(self.backend.current_revision("1180352194.13.59241"), 1)
        
    def test_create_revision(self):
        try:
            self.backend.create_revision("1180352194.13.59241", 1)
            self.fail()
        except NotImplementedError:
            self.assertTrue(True)
    
    def test_remove_revision(self):
        try:
            self.backend.remove_revision("1180352194.13.59241", 2)
            self.fail()
        except NotImplementedError:
            self.assertTrue(True)
    
    def test_get_data_backend(self):
        try:
            self.backend.get_data_backend("1180352194.13.59241", 1, "a")
            self.fail()
        except NotImplementedError:
            self.assertTrue(True)
            
if __name__ == "__main__":
        unittest.main()