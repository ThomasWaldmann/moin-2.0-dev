"""
    MoinMoin 1.6 compatible storage backend tests

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""


from MoinMoin.storage._tests import AbstractBackendTest, default_items, default_items_metadata, default_items_filters, default_items_revisions, default_items_data
from MoinMoin.storage._tests.test_backends_moin16 import get_page_backend, setup_module, teardown_module

from MoinMoin.storage.backends.meta import LayerBackend, NamespaceBackend


class TestLayerBackend(AbstractBackendTest):

    def setup_class(self):
        self.items = default_items
        self.items_revisions = default_items_revisions
        self.items_filters = default_items_filters
        self.items_metadata = default_items_metadata
        self.items_data = default_items_data
        
        add = len(self.items)
        self.items.append("Zet")
        self.items_revisions[add] = [2, 1]
        self.items_metadata[add] = {}
        self.items_metadata[add][1] = {}
        self.items_metadata[add][2] = {}
        self.items_data[add] = {}
        self.items_data[add][1] = "hallo"
        self.items_data[add][2] = "hallos"

        AbstractBackendTest.init("", LayerBackend([get_page_backend(), get_page_backend("pages2")]), self.items, self.items_revisions, self.items_data, self.items_metadata, self.items_revisions)

    def test_name(self):
        pass

    def test_list_items(self):
        assert self.backend.list_items() == self.items

    def test_has_item(self):
        assert self.backend.has_item(self.items[0]).name == "pages"
        assert self.backend.has_item(self.items[2]).name == "pages2"
        AbstractBackendTest.test_has_item(self)


"""
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
"""
