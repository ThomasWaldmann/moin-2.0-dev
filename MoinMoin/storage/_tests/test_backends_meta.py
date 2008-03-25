"""
    MoinMoin 1.6 compatible storage backend tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import copy

from MoinMoin.storage._tests import AbstractBackendTest, default_items, default_items_metadata, default_items_filters, default_items_revisions, default_items_data, create_data
from MoinMoin.storage._tests.test_backends_moin16 import get_page_backend, setup_module, teardown_module

from MoinMoin.storage.backends.meta import LayerBackend, NamespaceBackend
from MoinMoin.search import term

new_items = ["Zet"]
new_revisions = {}
new_revisions[0] = [2, 1]
new_metadata = {}
new_metadata[0] = {}
new_metadata[0][1] = {}
new_metadata[0][2] = {}
new_data = {}
new_data[0] = {}
new_data[0][1] = "Hallo"
new_data[0][2] = "hallos"


class TestLayerBackend(AbstractBackendTest):

    def setup_class(self):
        first_backend = get_page_backend()
        AbstractBackendTest.init(first_backend, name="pages")
        create_data(self)

        second_backend = get_page_backend("pages2")
        AbstractBackendTest.init(second_backend, items=new_items, revisions=new_revisions, metadata=new_metadata, data=new_data, name="pages2")
        create_data(self)

        self.items = copy.copy(default_items)
        self.items_revisions = copy.copy(default_items_revisions)
        self.items_filters = copy.copy(default_items_filters)
        self.items_metadata = copy.copy(default_items_metadata)
        self.items_data = copy.copy(default_items_data)

        add = len(self.items)
        self.items = self.items + new_items
        self.items_revisions[add] = new_revisions[0]
        self.items_metadata[add] = new_metadata[0]
        self.items_data[add] = new_data[0]

        AbstractBackendTest.init(LayerBackend([first_backend, second_backend], False), self.items, self.items_revisions, self.items_data, self.items_metadata, self.items_revisions)

    def test_name(self):
        pass

    def test_list_items(self):
        assert list(self.backend.list_items(term.TRUE)) == self.items

    def test_has_item(self):
        assert self.backend.has_item(self.items[0]).name == "pages"
        assert self.backend.has_item(self.items[2]).name == "pages2"
        AbstractBackendTest.test_has_item(self)


class TestNamespaceBackend(AbstractBackendTest):

    def setup_class(self):
        self.items = copy.copy(default_items)
        self.items_revisions = copy.copy(default_items_revisions)
        self.items_filters = copy.copy(default_items_filters)
        self.items_metadata = copy.copy(default_items_metadata)
        self.items_data = copy.copy(default_items_data)

        add = len(self.items)
        self.items = self.items + ["XYZ/Zet"]
        self.items_revisions[add] = new_revisions[0]
        self.items_metadata[add] = new_metadata[0]
        self.items_data[add] = new_data[0]

        backend = NamespaceBackend({'/': get_page_backend(), '/XYZ': get_page_backend("pages2")})
        AbstractBackendTest.init(backend, self.items, self.items_revisions, self.items_data, self.items_metadata, self.items_revisions)
        create_data(self)

    def test_name(self):
        pass

    def test_list_items(self):
        assert sorted(list(self.backend.list_items(term.TRUE))) == self.items

    def test_has_item(self):
        assert self.backend.has_item(self.items[0]).name == "pages"
        assert self.backend.has_item(self.items[2]).name == "pages2"
        AbstractBackendTest.test_has_item(self)

