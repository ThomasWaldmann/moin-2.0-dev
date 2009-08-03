# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - RouterBackend

    This defines tests for the RouterBackend

    @copyright: 2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import py

from MoinMoin.error import ConfigurationError
from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.memory import MemoryBackend
from MoinMoin.storage.backends.router import RouterBackend

class TestRouterBackend(BackendTest):
    """
    Test the MemoryBackend
    """
    def __init__(self):
        BackendTest.__init__(self, None)

    def create_backend(self):
        self.root = MemoryBackend()
        self.ns_user = 'UserProfiles/'
        self.users = MemoryBackend()
        self.child = MemoryBackend()
        self.other = MemoryBackend()
        self.mapping = [('child', self.child), ('other/', self.other), (self.ns_user, self.users), ('/', self.root)]
        return RouterBackend(self.mapping)

    def kill_backend(self):
        pass


    def test_correct_backend(self):
        mymap = {'rootitem': self.root,         # == /rootitem
                 'child/joe': self.child,       # Direct child of namespace.
                 'other/jane': self.other,      # Direct child of namespace.
                 'child/': self.child,          # Root of namespace itself (!= root)
                 'other/': self.other,          # Root of namespace
                 '': self.root,                 # Due to lack of any namespace info
                }

        assert not (self.root is self.child is self.other)
        for itemname, backend in mymap.iteritems():
            assert self.backend._get_backend(itemname)[0] is backend

    def test_store_and_get(self):
        itemname = 'child/foo'
        item = self.backend.create_item(itemname)
        assert item.name == itemname
        assert item._backend is self.child
        item.change_metadata()
        item['just'] = 'testing'
        item.publish_metadata()

        item = self.backend.get_item(itemname)
        assert item._backend is self.child
        assert item['just'] == 'testing'
        assert item.name == itemname

    def test_traversal(self):
        mymap = {'rootitem': self.root,         # == /rootitem
                 'child/joe': self.child,       # Direct child of namespace.
                 'other/jane': self.other,      # Direct child of namespace.
                 'child/': self.child,          # Root of namespace itself (!= root)
                 'other/': self.other,          # Root of namespace
                 '': self.root,                 # Due to lack of any namespace info
                }

        items_in = []
        for itemname, backend in mymap.iteritems():
            item = self.backend.create_item(itemname)
            assert item.name == itemname
            rev = item.create_revision(0)
            rev.write("This is %s" % itemname)
            item.commit()
            items_in.append(item)
            assert self.backend.has_item(itemname)

        items_out = list(self.backend.iteritems())

        items_in = [item.name for item in items_in]
        items_out = [item.name for item in items_out]
        items_in.sort()
        items_out.sort()

        assert items_in == items_out

    def test_user_in_traversal(self):
        joes_name = 'joe_with_the_unique_name'
        user_backend = self.backend.get_backend(self.ns_user)
        joe = user_backend.create_item(joes_name)
        joe.change_metadata()
        joe["email"] = "joe@example.com"
        joe.publish_metadata()

        all_items = list(self.backend.iteritems())
        all_items = [item.name for item in all_items]
        assert joes_name in all_items

    def test_nonexisting_namespace(self):
        itemname = 'nonexisting/namespace/somewhere/deep/below'
        item = self.backend.create_item(itemname)
        rev = item.create_revision(0)
        item.commit()
        assert self.root.has_item(itemname)

    def test_cross_backend_rename(self):
        itemname = 'i_will_be_moved'
        item = self.backend.create_item('child/' + itemname)
        item.create_revision(0)
        item.commit()
        assert self.child.has_item(itemname)
        newname = 'i_was_moved'
        item.rename('other/' + newname)
        print [item.name for item in self.child.iteritems()]
        assert not self.child.has_item(itemname)
        assert not self.child.has_item(newname)
        assert not self.child.has_item('other/' + newname)
        assert self.other.has_item(newname)

    def test_itemname_equals_namespace(self):
        itemname = 'child'
        backend, name, mountpoint = self.backend._get_backend(itemname)
        assert backend is self.child
        assert name == ''
        assert mountpoint == 'child'
