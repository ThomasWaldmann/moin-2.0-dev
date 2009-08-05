# -*- coding: utf-8 -*-
"""
    MoinMoin - Tests for our test environment

    @copyright: 2009 by MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import py

from MoinMoin.storage.error import NoSuchItemError

class TestStorageEnviron(object):
    def setup_method(self, method):
        self.class_level_value = 123

    def test_fresh_backends(self):
        assert self.class_level_value == 123

        storage = self.request.storage
        assert storage
        assert hasattr(storage, 'get_item')
        assert hasattr(storage, 'history')
        assert not list(storage.iteritems())
        assert not list(storage.history())
        assert py.test.raises(NoSuchItemError, storage.get_item, 'FrontPage')
        item = storage.create_item("FrontPage")
        rev = item.create_revision(0)
        item.commit()
        assert storage.has_item("FrontPage")

    # Run this test twice to see if something's changed
    test_twice = test_fresh_backends
