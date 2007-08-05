"""
    MoinMoin 1.6 compatible storage backend tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import copy
import os
import shutil
import tempfile

from MoinMoin.storage._tests import AbstractBackendTest, AbstractMetadataTest, AbstractDataTest, default_items_metadata

from MoinMoin.storage.backends.moin16 import UserBackend, PageBackend

from MoinMoin.storage.external import SIZE, DELETED
from MoinMoin.storage.external import EDIT_LOCK_TIMESTAMP, EDIT_LOCK_USER
from MoinMoin.storage.external import EDIT_LOG_MTIME, EDIT_LOG_USERID, EDIT_LOG_COMMENT, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME, EDIT_LOG_EXTRA, EDIT_LOG_ACTION


test_dir = None


def setup_module(module):
    """
    Extract test data to tmp.
    """
    global test_dir
    test_dir = tempfile.mkdtemp()

def teardown_module(module):
    """
    Remove test data from tmp.
    """
    global test_dir
    #shutil.rmtree(test_dir)
    test_dir = None


def get_user_backend(name="user"):
    try:
        os.makedirs(os.path.join(test_dir, "data", name))
    except:
        pass
    return UserBackend(name, os.path.join(test_dir, "data", name), DummyConfig())

def get_page_backend(name="pages"):
    try:
        os.makedirs(os.path.join(test_dir, "data", name))
    except:
        pass
    return PageBackend(name, os.path.join(test_dir, "data", name), DummyConfig())



class DummyConfig:
    tmp_dir = tempfile.gettempdir()
    indexes = ["name", "language", "format"]

    def __init__(self):
        self.indexes_dir = test_dir


user = ["1180352194.13.59241", "1180424607.34.55818", ]

user_revisions = {}

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
user_metadata[1][1] = {}

user_data = {}

user_filters = [['name', 'HeinrichWendel', user[0]], ['theme_name', 'modern', user[0]]]


class TestUserBackend(AbstractBackendTest):

    def setup_class(self):
        AbstractBackendTest.init("user", get_user_backend(), user, user_revisions, user_data, user_metadata, user_filters, "1182252194.13.52241", "1182252194.13.12241")

    def test_create_item(self):
        AbstractBackendTest.test_create_item(self)
        assert os.path.isfile(os.path.join(self.backend._get_page_path(""), self.newname))

    def test_remove_item(self):
        AbstractBackendTest.test_remove_item(self)
        assert not os.path.isfile(os.path.join(self.backend._get_page_path(""), self.newname))

    def test_rename_item(self):
        AbstractBackendTest.test_rename_item(self)
        self.backend.rename_item(self.items[0], self.newname)
        assert os.path.isfile(os.path.join(self.backend._get_page_path(""), self.newname))
        assert not os.path.isfile(os.path.join(self.backend._get_page_path(""), self.items[0]))
        self.backend.rename_item(self.newname, self.items[0])

class TestUserMetadata(AbstractMetadataTest):

    def setup_class(self):
        AbstractMetadataTest.init(get_user_backend(), user, user_revisions, user_metadata)


class TestPageBackend(AbstractBackendTest):

    def setup_class(self):
        AbstractBackendTest.init("pages", get_page_backend())

    def test_create_item(self):
        AbstractBackendTest.test_create_item(self)
        assert os.path.isdir(os.path.join(self.backend._get_page_path(""), self.newname))
        assert os.path.isdir(os.path.join(self.backend._get_page_path(""), self.newname, "cache"))
        assert os.path.isdir(os.path.join(self.backend._get_page_path(""), self.newname, "cache", "__lock__"))
        assert os.path.isdir(os.path.join(self.backend._get_page_path(""), self.newname, "revisions"))
        assert os.path.isfile(os.path.join(self.backend._get_page_path(""), self.newname, "current"))
        assert os.path.isfile(os.path.join(self.backend._get_page_path(""), self.newname, "edit-log"))

    def test_remove_item(self):
        AbstractBackendTest.test_remove_item(self)
        assert not os.path.exists(os.path.join(self.backend._get_page_path(""), self.newname))

    def test_rename_item(self):
        AbstractBackendTest.test_rename_item(self)
        self.backend.rename_item(self.items[0], self.newname)
        assert os.path.isdir(os.path.join(self.backend._get_page_path(""), self.newname))
        assert not os.path.isdir(os.path.join(self.backend._get_page_path(""), self.items[0]))
        self.backend.rename_item(self.newname, self.items[0])

    def test_current_revision(self):
        AbstractBackendTest.test_current_revision(self)
        assert open(os.path.join(self.backend._get_page_path(""), self.items[0], "current"), "r").read() == "00000002\n"
        assert open(os.path.join(self.backend._get_page_path(""), self.items[1], "current"), "r").read() == "00000003\n"

    def test_has_revision(self):
        AbstractBackendTest.test_has_revision(self)
        assert os.path.isfile(os.path.join(self.backend._get_page_path(""), self.items[0], "revisions", "00000001"))
        assert os.path.isfile(os.path.join(self.backend._get_page_path(""), self.items[0], "revisions", "00000002"))
        assert os.path.isfile(os.path.join(self.backend._get_page_path(""), self.items[1], "revisions", "00000001"))
        assert os.path.isfile(os.path.join(self.backend._get_page_path(""), self.items[1], "revisions", "00000002"))
        assert os.path.isfile(os.path.join(self.backend._get_page_path(""), self.items[1], "revisions", "00000003"))

    def test_create_revision(self):
        AbstractBackendTest.test_create_revision(self)
        assert os.path.isfile(os.path.join(self.backend._get_page_path(""), self.items[0], "revisions", "00000003"))
        assert open(os.path.join(self.backend._get_page_path(""), self.items[0], "current"), "r").read() == "00000003\n"

    def test_remove_revision(self):
        AbstractBackendTest.test_remove_revision(self)
        assert open(os.path.join(self.backend._get_page_path(""), self.items[0], "current"), "r").read() == "00000002\n"
        assert not os.path.isfile(os.path.join(self.backend._get_page_path(""), self.items[0], "revisions", "00000003"))


class TestPageMetadata(AbstractMetadataTest):

    # TODO: fix edit_lock
    # TODO: fix edit_log

    def setup_class(self):
        metadata = copy.copy(default_items_metadata)
        for item in metadata:
            for revno in metadata[item]:
                metadata[item][revno][EDIT_LOG_EXTRA] = ''
                metadata[item][revno][EDIT_LOG_ACTION] = 'SAVE'
                metadata[item][revno][EDIT_LOG_ADDR] = '127.0.0.1'
                metadata[item][revno][EDIT_LOG_HOSTNAME] = 'localhost'
                metadata[item][revno][EDIT_LOG_COMMENT] = ''
                metadata[item][revno][EDIT_LOG_USERID] = '1180352194.13.59241'
                metadata[item][revno][EDIT_LOG_MTIME] = '1186237890.109'
                metadata[item][revno][SIZE] = ''

        AbstractMetadataTest.init(get_page_backend(), metadata=metadata)

    def assertDict(self, dict1, dict2):
        for key in [SIZE, EDIT_LOG_MTIME]:
            if key in dict1:
                del dict1[key]
            if key in dict2:
                del dict2[key]
        AbstractMetadataTest.assertDict(self, dict1, dict2)

    def test_size(self):
        metadata = self.backend.get_metadata_backend(self.items[0], 1)
        assert SIZE in metadata

    def test_edit_lock(self):
        metadata = self.backend.get_metadata_backend(self.items[0], -1)
        metadata[EDIT_LOCK_TIMESTAMP] = "1186237890.109"
        metadata[EDIT_LOCK_USER] = "127.0.0.1"
        metadata.save()
        metadata = self.backend.get_metadata_backend(self.items[0], -1)
        assert metadata[EDIT_LOCK_TIMESTAMP] == "1186237890.11"
        assert metadata[EDIT_LOCK_USER] == "127.0.0.1"
        assert os.path.isfile(os.path.join(self.backend._get_page_path(""), self.items[0], "edit-lock"))
        assert open(os.path.join(self.backend._get_page_path(""), self.items[0], "edit-lock"), "r").read() == "1186237890109000\t0\t0\t0\t0\t0\t127.0.0.1\t0\t0\n"
        del metadata[EDIT_LOCK_TIMESTAMP]
        del metadata[EDIT_LOCK_USER]
        metadata.save()
        metadata = self.backend.get_metadata_backend(self.items[0], -1)
        assert not EDIT_LOCK_TIMESTAMP in metadata
        assert not EDIT_LOCK_USER in metadata
        assert not os.path.isfile(os.path.join(self.backend._get_page_path(""), self.items[0], "edit-lock"))

    def test_deleted(self):
        metadata = self.backend.get_metadata_backend(self.items[0], self.items_revisions[0][0])
        metadata[DELETED] = "True"
        metadata.save()
        assert self.backend.current_revision(self.items[0], 0) == self.items_revisions[0][0]
        assert self.backend.create_revision(self.items[0], 0) == self.items_revisions[0][0] + 1
        assert not os.path.isfile(os.path.join(self.backend._get_page_path(""), self.items[0], "revisions", "00000002"))
        metadata = self.backend.get_metadata_backend(self.items[0], self.items_revisions[0][0])
        metadata[DELETED] = "False"
        metadata.save()
        assert os.path.isfile(os.path.join(self.backend._get_page_path(""), self.items[0], "revisions", "00000002"))


class TestPageData(AbstractDataTest):

    def setup_class(self):
        AbstractDataTest.init(get_page_backend())

