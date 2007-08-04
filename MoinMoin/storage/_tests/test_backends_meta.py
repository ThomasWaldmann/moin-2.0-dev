"""
    MoinMoin 1.6 compatible storage backend tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.storage._tests import AbstractBackendTest, items
from MoinMoin.storage._tests.test_backends_moin16 import get_page_backend, get_user_backend, setup_module, teardown_module, user

from MoinMoin.storage.backends.meta import LayerBackend, NamespaceBackend


class TestLayerBackend(AbstractBackendTest):

    def setup_class(self):
        self.backend = LayerBackend([get_page_backend(), get_user_backend()])

    def test_name(self):
        pass

    def test_list_items(self):
        new_items = items + user
        new_items.sort()
        assert self.backend.list_items() == new_items

    def test_has_item(self):
        assert self.backend.has_item(items[0]).name == "pages"
        assert self.backend.has_item(user[0]).name == "user"
        AbstractBackendTest.test_has_item(self)


class TestNamespaceBackend(AbstractBackendTest):

    def setup_class(self):
        self.backend = NamespaceBackend({'/': get_page_backend(), '/usr': get_user_backend()})

        self.new_names = []
        for item in user:
            self.new_names.append('usr/' + item)

    def test_name(self):
        pass

    def test_list_items(self):
        new_items = items + self.new_names
        new_items.sort()
        assert self.backend.list_items() == new_items

    def test_has_item(self):
        assert self.backend.has_item(items[0]).name == "pages"
        assert self.backend.has_item(self.new_names[0]).name == "user"
        AbstractBackendTest.test_has_item(self)

