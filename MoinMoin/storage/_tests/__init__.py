"""
    Common stuff for storage unit tests.

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import os
import py
import shutil
import tempfile

from MoinMoin.support import tarfile
from MoinMoin.storage.error import BackendError, LockingError

test_dir = None

names = ["1180352194.13.59241", "1180424607.34.55818", "1180424618.59.18110", ]

pages = ["New", "Test", ]

metadata = {u'aliasname': u'',
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

def setup(module):
    """
    Extract test data to tmp.
    """
    global test_dir
    test_dir = tempfile.mkdtemp()
    tar_file = tarfile.open(os.path.join(str(py.magic.autopath().dirpath()), u"data.tar"))
    for tarinfo in tar_file:
        tar_file.extract(tarinfo, test_dir)
    tar_file.close()

def teardown(module):
    """
    Remove test data from tmp.
    """
    global test_dir
    shutil.rmtree(test_dir)
    test_dir = None

def get_user_dir():
    return os.path.join(test_dir, "data/user")

def get_page_dir():
    return os.path.join(test_dir, "data/pages")


class DummyConfig:
    tmp_dir = tempfile.gettempdir()
    indexes = ["name", "language", "format"]

    def __init__(self):
        self.indexes_dir = test_dir


class BackendTest:
    def test_has_item(self):
        assert not self.backend.has_item("")

    def test_rename_item(self):
        py.test.raises(BackendError, self.backend.rename_item, pages[0], "")
        py.test.raises(BackendError, self.backend.rename_item, pages[0], pages[0])

    def test_lock_unlock_item(self):
        self.backend.lock("id")
        py.test.raises(LockingError, self.backend.lock, "id")
        self.backend.unlock("id")
        self.backend.lock("id", timeout=1)
        py.test.raises(LockingError, self.backend.lock, "id", 1)
        self.backend.unlock("id")
