"""
    MoinMoin 1.6 compatible storage backend tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.storage._tests import get_user_dir, get_page_dir, DummyConfig, pages, names, setup, teardown, BackendTest

from MoinMoin.storage.backends.moin16 import UserBackend, PageBackend
from MoinMoin.storage.backends.meta import LayerBackend, NamespaceBackend
from MoinMoin.storage.error import NoSuchItemError


def setup_module(module):
    setup(module)

def teardown_module(module):
    teardown(module)


class TestLayerBackend(BackendTest):
    """
    This class tests the layer backend. It only tests the basic three methods,
    all other methods are like the remove_item method using call.
    """

    def setup_class(self):
        self.backend = LayerBackend([PageBackend("pages", get_page_dir(), DummyConfig()), UserBackend("user", get_user_dir(), DummyConfig())])

    def test_list_items(self):
        items = pages + names
        items.sort()
        assert self.backend.list_items() == items

    def test_has_item(self):
        assert self.backend.has_item(pages[0]).name == "pages"
        assert self.backend.has_item(names[0]).name == "user"
        assert not self.backend.has_item("ad")
        BackendTest.test_has_item(self)

    def test_remove_item(self):
        py.test.raises(NoSuchItemError, self.backend.remove_item, "asdf")


class TestNamespaceBackend(BackendTest):
    """
    This class Tests the namespace backend. It only tests the basic three methods,
    all other methods are like the remove_item method using call.
    """

    def setup_class(self):
        self.backend = NamespaceBackend({'/': PageBackend("pages", get_page_dir(), DummyConfig()), '/usr': UserBackend("user", get_user_dir(), DummyConfig())})

        self.new_names = []
        for item in names:
            self.new_names.append('usr/' + item)

    def test_list_items(self):
        items = pages + self.new_names
        items.sort()
        assert self.backend.list_items() == pages + self.new_names

    def test_has_item(self):
        assert self.backend.has_item(pages[0]).name == "pages"
        assert self.backend.has_item(self.new_names[0]).name == "user"
        assert not self.backend.has_item("ad")
        BackendTest.test_has_item(self)

    def test_remove_item(self):
        py.test.raises(NoSuchItemError, self.backend.remove_item, "asdf")

