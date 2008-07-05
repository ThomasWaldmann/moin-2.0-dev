# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - storage API


    @copyright: 2008 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.storage import Backend, Item
from MoinMoin.storage.error import NoSuchItemError

class TestBackendAPI(object):
    def test_has_item(self):
        class HasNoItemsBackend(Backend):
            def get_item(self, name):
                raise NoSuchItemError('should not be visible')
        be = HasNoItemsBackend()
        assert not be.has_item('asdf')

    def test_unicode_meta(self):
        class HasAnyItemBackend(Backend):
            def get_item(self, name):
                return Item(self, name)
            def _change_item_metadata(self, item):
                pass
            def _get_item_metadata(self, item):
                return {}
            def _publish_item_metadata(self, item):
                pass
        be = HasAnyItemBackend()
        item = be.get_item('a')
        item.change_metadata()
        item[u'a'] = u'b'
        item.publish_metadata()
