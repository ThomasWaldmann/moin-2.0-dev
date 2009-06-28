# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - RouterBackend

    This defines tests for the RouterBackend

    @copyright: 2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

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
        self.users = MemoryBackend()
        self.child = MemoryBackend()
        self.other = MemoryBackend()
        self.mapping = [('child/', self.child), ('other/', self.other), ('/', self.root)]
        return RouterBackend(self.mapping, self.users)

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
            assert backend.has_item(itemname)

        items_out = list(self.backend.iteritems())

        items_in = [item.name for item in items_in]
        items_out = [item.name for item in items_out]
        items_in.sort()
        items_out.sort()

        assert items_in == items_out
