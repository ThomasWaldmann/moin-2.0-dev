"""
    MoinMoin 1.6 compatible storage backend tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.storage._tests import get_user_dir, get_page_dir, DummyConfig, pages, names, setup, teardown

from MoinMoin.storage.fs_moin16 import UserStorage, PageStorage
from MoinMoin.storage.backends import LayerBackend, NamespaceBackend
from MoinMoin.storage.error import NoSuchItemError


def setup_module(module):
    setup(module)

def teardown_module(module):
    teardown(module)


class TestLayerBackend:
    """
    This class tests the layer backend. It only tests the basic three methods,
    all other methods are like the remove_item method using call.
    """

    backend = None

    def setup_class(self):
        self.backend = LayerBackend([PageStorage(get_page_dir(), DummyConfig()), UserStorage(get_user_dir(), DummyConfig())])

    def teardown_class(self):
        self.backend = None

    def test_list_items(self):
        assert set(self.backend.list_items()) == set(pages + names)

    def test_has_item(self):
        assert self.backend.has_item(pages[0])
        assert self.backend.has_item(names[0])
        assert not self.backend.has_item("ad")
        assert not self.backend.has_item("")

    def test_remove_item(self):
        py.test.raises(NoSuchItemError, self.backend.remove_item, "asdf")


class TestNamespaceBackend:
    """
    This class Tests the namespace backend. It only tests the basic three methods,
    all other methods are like the remove_item method using call.
    """

    backend = None

    def setup_class(self):
        self.backend = NamespaceBackend({'/': PageStorage(get_page_dir(), DummyConfig()), '/usr': UserStorage(get_user_dir(), DummyConfig())})

        self.new_names = []
        for item in names:
            self.new_names.append('usr/' + item)

    def teardown_class(self):
        self.backend = None

    def test_list_items(self):
        assert set(self.backend.list_items()) == set(pages + self.new_names)

    def test_has_item(self):
        assert self.backend.has_item(pages[0])
        assert self.backend.has_item(self.new_names[0])
        assert not self.backend.has_item("ad")
        assert not self.backend.has_item("")

    def test_remove_item(self):
        py.test.raises(NoSuchItemError, self.backend.remove_item, "asdf")

