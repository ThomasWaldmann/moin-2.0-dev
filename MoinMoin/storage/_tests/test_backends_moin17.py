"""
    MoinMoin 1.7 storage backend tests

    @copyright: 2007 MoinMoin:ThomasWaldmann, based on
                code from MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import copy
import os
import shutil
import tempfile

from MoinMoin.storage._tests import AbstractBackendTest, AbstractMetadataTest, AbstractDataTest, default_items_metadata, create_data

from MoinMoin.storage.backends.moin17 import UserBackend, ItemBackend

from MoinMoin.storage.external import SIZE, DELETED
from MoinMoin.storage.external import EDIT_LOCK_TIMESTAMP, EDIT_LOCK_ADDR, EDIT_LOCK_HOSTNAME, EDIT_LOCK_USERID
from MoinMoin.storage.external import EDIT_LOG_MTIME, EDIT_LOG_USERID, EDIT_LOG_COMMENT, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME, EDIT_LOG_EXTRA, EDIT_LOG_ACTION

from MoinMoin.search import term

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
    shutil.rmtree(test_dir)
    test_dir = None


def get_user_backend(name="user"):
    try:
        os.makedirs(os.path.join(test_dir, "data", name))
    except:
        pass
    return UserBackend(name, os.path.join(test_dir, "data", name), DummyConfig())

def get_page_backend(name="items"):
    try:
        os.makedirs(os.path.join(test_dir, "data", name))
    except:
        pass
    return ItemBackend(name, os.path.join(test_dir, "data", name), DummyConfig())



class DummyConfig:
    indexes = ["name", "language", "format"]

    acl_rights_default = u"Trusted:read,write,delete,revert Known:read,write,delete,revert All:read,write"
    acl_rights_before = u""
    acl_rights_after = u""
    acl_rights_valid = ['read', 'write', 'delete', 'revert', 'admin']
    acl_hierarchic = False

    def __init__(self):
        self.indexes_dir = test_dir
        self.tmp_dir = test_dir


user = ["1180352194.13.59241", "1180424607.34.55818", ]

user_revisions = {}

user_metadata = {}
user_metadata[0] = {}
user_metadata[0][1] = {
            u'aliasname': u'',
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

user_filters = [(term.MetaDataMatch('name', 'HeinrichWendel'), [user[0]]),
                (term.MetaDataMatch('theme_name', 'modern'), [user[0]])]


class TestUserBackend(AbstractBackendTest):

    def setup_class(self):
        AbstractBackendTest.init(get_user_backend(), items=user, revisions=user_revisions, data=user_data, metadata=user_metadata, filters=user_filters, name="user", newname="1182252194.13.52241", notexist="1182252194.13.12241")
        create_data(self)

    def test_create_item(self):
        AbstractBackendTest.test_create_item(self)
        assert os.path.isfile(os.path.join(self.backend._get_item_path(""), self.newname))

    def test_remove_item(self):
        AbstractBackendTest.test_remove_item(self)
        assert not os.path.isfile(os.path.join(self.backend._get_item_path(""), self.newname))

    def test_rename_item(self):
        AbstractBackendTest.test_rename_item(self)
        self.backend.rename_item(self.items[0], self.newname)
        assert os.path.isfile(os.path.join(self.backend._get_item_path(""), self.newname))
        assert not os.path.isfile(os.path.join(self.backend._get_item_path(""), self.items[0]))
        self.backend.rename_item(self.newname, self.items[0])


class TestUserMetadata(AbstractMetadataTest):

    def setup_class(self):
        AbstractMetadataTest.init(get_user_backend(), items=user, revisions=user_revisions, metadata=user_metadata, data=user_data)
        create_data(self)


class TestItemBackend(AbstractBackendTest):

    def setup_class(self):
        AbstractBackendTest.init(get_page_backend(), name="items")
        create_data(self)

    def test_create_item(self):
        AbstractBackendTest.test_create_item(self)
        assert os.path.isdir(os.path.join(self.backend._get_item_path(""), self.newname))
        assert os.path.isdir(os.path.join(self.backend._get_item_path(""), self.newname, "cache"))
        assert os.path.isdir(os.path.join(self.backend._get_item_path(""), self.newname, "cache", "__lock__"))
        assert os.path.isdir(os.path.join(self.backend._get_item_path(""), self.newname, "meta.revisions"))
        assert os.path.isdir(os.path.join(self.backend._get_item_path(""), self.newname, "data.revisions"))
        assert os.path.isfile(os.path.join(self.backend._get_item_path(""), self.newname, "meta"))

    def test_remove_item(self):
        AbstractBackendTest.test_remove_item(self)
        assert not os.path.exists(os.path.join(self.backend._get_item_path(""), self.newname))

    def test_rename_item(self):
        AbstractBackendTest.test_rename_item(self)
        self.backend.rename_item(self.items[0], self.newname)
        assert os.path.isdir(os.path.join(self.backend._get_item_path(""), self.newname))
        assert not os.path.isdir(os.path.join(self.backend._get_item_path(""), self.items[0]))
        self.backend.rename_item(self.newname, self.items[0])

    def test_current_revision(self):
        AbstractBackendTest.test_current_revision(self)
        #assert open(os.path.join(self.backend._get_item_path(""), self.items[0], "current"), "r").read() == "00000002\n"
        #assert open(os.path.join(self.backend._get_item_path(""), self.items[1], "current"), "r").read() == "00000003\n"

    def test_has_revision(self):
        AbstractBackendTest.test_has_revision(self)
        assert os.path.isfile(os.path.join(self.backend._get_item_path(""), self.items[0], "meta.revisions", "00000001"))
        assert os.path.isfile(os.path.join(self.backend._get_item_path(""), self.items[0], "meta.revisions", "00000002"))
        assert os.path.isfile(os.path.join(self.backend._get_item_path(""), self.items[1], "data.revisions", "00000001"))
        assert os.path.isfile(os.path.join(self.backend._get_item_path(""), self.items[1], "data.revisions", "00000002"))
        assert os.path.isfile(os.path.join(self.backend._get_item_path(""), self.items[1], "data.revisions", "00000003"))

    def test_create_revision(self):
        AbstractBackendTest.test_create_revision(self)
        assert os.path.isfile(os.path.join(self.backend._get_item_path(""), self.items[0], "meta.revisions", "00000003"))
        #assert open(os.path.join(self.backend._get_item_path(""), self.items[0], "current"), "r").read() == "00000003\n"

    def test_remove_revision(self):
        AbstractBackendTest.test_remove_revision(self)
        #assert open(os.path.join(self.backend._get_item_path(""), self.items[0], "current"), "r").read() == "00000002\n"
        assert not os.path.isfile(os.path.join(self.backend._get_item_path(""), self.items[0], "meta.revisions", "00000003"))


class TestItemMetadata(AbstractMetadataTest):

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
                metadata[item][revno][EDIT_LOG_MTIME] = '1186237890.110'
                metadata[item][revno][SIZE] = ''

        AbstractMetadataTest.init(get_page_backend(), metadata=metadata)
        create_data(self)

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
        metadata[EDIT_LOCK_TIMESTAMP] = "1186237890.110"
        metadata[EDIT_LOCK_ADDR] = "127.0.0.1"
        metadata[EDIT_LOCK_HOSTNAME] = "localhost"
        metadata[EDIT_LOCK_USERID] = "1180352194.13.59241"
        metadata.save()
        metadata = self.backend.get_metadata_backend(self.items[0], -1)
        assert metadata[EDIT_LOCK_TIMESTAMP] == "1186237890.110"
        assert metadata[EDIT_LOCK_ADDR] == "127.0.0.1"
        assert metadata[EDIT_LOCK_HOSTNAME] == "localhost"
        assert metadata[EDIT_LOCK_USERID] == "1180352194.13.59241"
        del metadata[EDIT_LOCK_TIMESTAMP]
        del metadata[EDIT_LOCK_ADDR]
        del metadata[EDIT_LOCK_HOSTNAME]
        del metadata[EDIT_LOCK_USERID]
        metadata.save()
        metadata = self.backend.get_metadata_backend(self.items[0], -1)
        assert not EDIT_LOCK_TIMESTAMP in metadata
        assert not EDIT_LOCK_ADDR in metadata
        assert not EDIT_LOCK_HOSTNAME in metadata
        assert not EDIT_LOCK_USERID in metadata

    def test_deleted(self):
        metadata = self.backend.get_metadata_backend(self.items[0], self.items_revisions[0][0])
        metadata[DELETED] = None
        metadata.save()
        assert self.backend.current_revision(self.items[0]) == self.items_revisions[0][0]
        #assert not os.path.isfile(os.path.join(self.backend._get_item_path(""), self.items[0], "revisions", "00000002"))
        metadata = self.backend.get_metadata_backend(self.items[0], self.items_revisions[0][0])
        del metadata[DELETED]
        metadata.save()
        #assert os.path.isfile(os.path.join(self.backend._get_item_path(""), self.items[0], "revisions", "00000002"))

    def test_edit_log(self):
        metadata = self.backend.get_metadata_backend(self.items[0], 1)
        metadata[EDIT_LOG_EXTRA] = ''
        metadata[EDIT_LOG_ACTION] = 'SAVE/NEW'
        metadata[EDIT_LOG_ADDR] = '127.0.0.1'
        metadata[EDIT_LOG_HOSTNAME] = 'localhost'
        metadata[EDIT_LOG_COMMENT] = ''
        metadata[EDIT_LOG_USERID] = '1180352194.13.59241'
        metadata[EDIT_LOG_MTIME] = '1186237890.110'
        metadata.save()
        metadata = self.backend.get_metadata_backend(self.items[0], 1)
        assert EDIT_LOG_USERID in metadata and metadata[EDIT_LOG_USERID] == '1180352194.13.59241'

        metadata = self.backend.get_metadata_backend(self.items[0], 2)
        metadata[EDIT_LOG_EXTRA] = ''
        metadata[EDIT_LOG_ACTION] = 'SAVE/NEW'
        metadata[EDIT_LOG_ADDR] = '127.0.0.1'
        metadata[EDIT_LOG_HOSTNAME] = 'localhost'
        metadata[EDIT_LOG_COMMENT] = ''
        metadata[EDIT_LOG_USERID] = '1180352194.13.59241'
        metadata[EDIT_LOG_MTIME] = '1186237890.111'
        metadata.save()
        metadata = self.backend.get_metadata_backend(self.items[0], 2)
        assert EDIT_LOG_MTIME in metadata and metadata[EDIT_LOG_MTIME] == '1186237890.111'

        self.backend.create_revision(self.items[0], 3)
        metadata = self.backend.get_metadata_backend(self.items[0], 3)
        metadata[EDIT_LOG_EXTRA] = ''
        metadata[EDIT_LOG_ACTION] = 'SAVE/NEW'
        metadata[EDIT_LOG_ADDR] = '127.0.0.1'
        metadata[EDIT_LOG_HOSTNAME] = 'localhost'
        metadata[EDIT_LOG_COMMENT] = ''
        metadata[EDIT_LOG_USERID] = '1180352194.13.59241'
        metadata[EDIT_LOG_MTIME] = '1186237890.110'
        metadata.save()
        metadata = self.backend.get_metadata_backend(self.items[0], 3)
        assert EDIT_LOG_USERID in metadata and metadata[EDIT_LOG_USERID] == '1180352194.13.59241'

        self.backend.create_revision(self.items[0], 5)
        metadata = self.backend.get_metadata_backend(self.items[0], 5)
        metadata[EDIT_LOG_EXTRA] = ''
        metadata[EDIT_LOG_ACTION] = 'SAVE/NEW'
        metadata[EDIT_LOG_ADDR] = '127.0.0.1'
        metadata[EDIT_LOG_HOSTNAME] = 'localhost'
        metadata[EDIT_LOG_COMMENT] = ''
        metadata[EDIT_LOG_USERID] = '1180352194.13.59241'
        metadata[EDIT_LOG_MTIME] = '1186237890.110'
        metadata.save()
        metadata = self.backend.get_metadata_backend(self.items[0], 5)
        assert EDIT_LOG_USERID in metadata and metadata[EDIT_LOG_USERID] == '1180352194.13.59241'

class TestPageData(AbstractDataTest):

    def setup_class(self):
        AbstractDataTest.init(get_page_backend())
        create_data(self)

