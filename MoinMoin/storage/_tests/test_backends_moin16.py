"""
    MoinMoin 1.6 compatible storage backend tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import os
import py.test
import py.magic
import shutil
import tempfile

from MoinMoin.storage._tests import AbstractBackendTest, AbstractMetadataTest, default_items

from MoinMoin.storage.backends.moin16 import UserBackend, PageBackend
from MoinMoin.storage.error import BackendError, NoSuchItemError, StorageError



test_dir = None


def setup_module(module):
    """
    Extract test data to tmp.
    """
    global test_dir
    test_dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(test_dir, "data", "pages"))
    os.makedirs(os.path.join(test_dir, "data", "user"))

def teardown_module(module):
    """
    Remove test data from tmp.
    """
    global test_dir
    #shutil.rmtree(test_dir)
    test_dir = None


def get_user_backend():
    return UserBackend("users", get_user_dir(), DummyConfig())

def get_page_backend():
    return PageBackend("pages", get_page_dir(), DummyConfig())

def get_user_dir():
    return os.path.join(test_dir, "data/user")

def get_page_dir():
    return os.path.join(test_dir, "data/pages") 


class DummyConfig:
    tmp_dir = tempfile.gettempdir()
    indexes = ["name", "language", "format"]

    def __init__(self):
        self.indexes_dir = test_dir


user = ["1180352194.13.59241", "1180424607.34.55818", "1180424618.59.18110", ]

user_revisions = {}
user_revisions[0] = [1]
user_revisions[1] = [1]
user_revisions[2] = [1]

user_metadata = {}
user_metadata[0] = {}
user_metadata[0][1] = {u'aliasname': u'',
            u'bookmarks': {},
            u'css_url': u'',
            u'date_fmt': u'',
            u'datetime_fmt': u'',
            u'disabled': u'0',
            u'edit_on_doubleclick': u'0',
            u'edit_rows': u'20',
            u'editor_default': u'text',
            u'editor_ui': u'freechoice',
            u'email': u'h_wendel@cojobo.net',
            u'enc_password': u'{SHA}ujz/zJOpLgj4LDPFXYh2Zv3zZK4=',
            u'language': u'',
            u'last_saved': u'1180435816.61',
            u'mailto_author': u'0',
            u'name': u'HeinrichWendel',
            u'quicklinks': [u'www.google.de', u'www.test.de', u'WikiSandBox', ],
            u'remember_last_visit': u'0',
            u'remember_me': u'1',
            u'show_comments': u'0',
            u'show_fancy_diff': u'1',
            u'show_nonexist_qm': u'0',
            u'show_page_trail': u'1',
            u'show_toolbar': u'1',
            u'show_topbottom': u'0',
            u'subscribed_pages': [u'WikiSandBox', u'FrontPage2', ],
            u'theme_name': u'modern',
            u'tz_offset': u'0',
            u'want_trivial': u'0',
            u'wikiname_add_spaces': u'0',
           }

user_metadata[1] = {}
user_metadata[1][1] = user_metadata[0][1]
user_metadata[2] = {}
user_metadata[2][1] = user_metadata[0][1]

user_filter = ['name', 'HeinrichWendel', user[0]]


"""
class TestUserBackend(AbstractBackendTest):

    newname = "1182252194.13.52241"

    def setup_class(cls):
        cls.name = "users"
        cls.backend = get_user_backend()

    def test_list_items(self):
        assert self.backend.list_items() == user
        assert self.backend.list_items({'name': 'HeinrichWendel'}) == [user[0]]

    def test_has_item(self):
        assert self.backend.has_item(user[0])
        assert not self.backend.has_item(self.notexist)
        assert not self.backend.has_item("")

    def test_create_item(self):
        py.test.raises(BackendError, self.backend.create_item, user[0])
        self.backend.create_item(self.newname)
        assert self.backend.has_item(self.newname)
        assert self.backend.list_items() == user + [self.newname]
        assert self.backend.current_revision(self.newname) == 1

    def test_remove_item(self):
        self.backend.remove_item(self.newname)
        assert not self.backend.has_item(self.newname)
        assert self.backend.list_items() == user
        py.test.raises(NoSuchItemError, self.backend.remove_item, self.newname)

    def test_rename_item(self):
        py.test.raises(StorageError, self.backend.rename_item, user[0], self.newname)

    def test_list_revisions(self):
        assert self.backend.list_revisions(user[0]) == [1]

    def test_current_revision(self):
        assert self.backend.current_revision(user[0]) == 1
        assert self.backend.current_revision(user[1]) == 1

    def test_has_revision(self):
        assert self.backend.has_revision(user[0], 1)
        assert self.backend.has_revision(user[1], 0)
        assert not self.backend.has_revision(user[2], 2)
        assert not self.backend.has_revision(user[0], -1)

    def test_create_revision(self):
        py.test.raises(StorageError, self.backend.create_revision, user[0], 1)

    def test_remove_revision(self):
        py.test.raises(StorageError, self.backend.remove_revision, user[0], 1)

    def test_get_data_backend(self):
        py.test.raises(StorageError, self.backend.get_data_backend, user[0], 1)

    def test_get_metadata_backend(self):
        self.backend.get_metadata_backend(user[0], 1)


class TestUserMetadata(AbstractMetadataTest):

    def setup_class(cls):
        cls.item = user[0]
        cls.metadata = user_metadata[0][1]
        AbstractMetadataTest.init(get_user_backend())
"""

class TestPageBackend(AbstractBackendTest):

    def setup_class(self):
        AbstractBackendTest.init("pages", get_page_backend())

    def test_create_item(self):
        AbstractBackendTest.test_create_item(self)
        assert os.path.isdir(os.path.join(get_page_dir(), self.newname))
        assert os.path.isdir(os.path.join(get_page_dir(), self.newname, "cache"))
        assert os.path.isdir(os.path.join(get_page_dir(), self.newname, "cache", "__lock__"))
        assert os.path.isdir(os.path.join(get_page_dir(), self.newname, "revisions"))
        assert os.path.isfile(os.path.join(get_page_dir(), self.newname, "current"))
        assert os.path.isfile(os.path.join(get_page_dir(), self.newname, "edit-log"))

    def test_remove_item(self):
        AbstractBackendTest.test_remove_item(self)
        assert not os.path.exists(os.path.join(get_page_dir(), self.newname))

    def test_rename_item(self):
        AbstractBackendTest.test_rename_item(self)
        self.backend.rename_item(default_items[0], self.newname)
        assert os.path.isdir(os.path.join(get_page_dir(), self.newname))
        assert not os.path.isdir(os.path.join(get_page_dir(), default_items[0]))
        self.backend.rename_item(self.newname, default_items[0])

    def test_current_revision(self):
        AbstractBackendTest.test_current_revision(self)
        assert open(os.path.join(get_page_dir(), default_items[0], "current"), "r").read() == "00000002\n"
        assert open(os.path.join(get_page_dir(), default_items[1], "current"), "r").read() == "00000003\n"

    def test_has_revision(self):
        AbstractBackendTest.test_has_revision(self)
        assert os.path.isfile(os.path.join(get_page_dir(), default_items[0], "revisions", "00000001"))
        assert os.path.isfile(os.path.join(get_page_dir(), default_items[0], "revisions", "00000002"))
        assert os.path.isfile(os.path.join(get_page_dir(), default_items[1], "revisions", "00000001"))
        assert os.path.isfile(os.path.join(get_page_dir(), default_items[1], "revisions", "00000002"))
        assert os.path.isfile(os.path.join(get_page_dir(), default_items[1], "revisions", "00000003"))

    def test_create_revision(self):
        AbstractBackendTest.test_create_revision(self)
        assert os.path.isfile(os.path.join(get_page_dir(), default_items[0], "revisions", "00000003"))
        assert open(os.path.join(get_page_dir(), default_items[0], "current"), "r").read() == "00000003\n"

    def test_remove_revision(self):
        AbstractBackendTest.test_remove_revision(self)
        assert open(os.path.join(get_page_dir(), default_items[0], "current"), "r").read() == "00000002\n"
        assert not os.path.isfile(os.path.join(get_page_dir(), default_items[0], "revisions", "00000003"))



class TestPageMetadata(AbstractMetadataTest):

    # TODO: test special keys

    def setup_class(self):
        AbstractMetadataTest.init(get_page_backend())
