# -*- coding: utf-8 -*- 
"""
    MoinMoin - Test - storage API


    @copyright: 2008 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.storage import Backend
from MoinMoin.storage.error import NoSuchItemError

class TestBackendAPI(object):
    def test_has_item(self):
        class HasNoItemsBackend(Backend):
            def get_item(self, name):
                raise NoSuchItemError('should not be visible')
        be = HasNoItemsBackend()
        assert not be.has_item('asdf')
