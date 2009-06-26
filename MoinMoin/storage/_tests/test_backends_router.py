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
        self.child = MemoryBackend()
        self.mapping = {'/': self.root, 'child/': self.child}
        return RouterBackend(self.mapping)

    def kill_backend(self):
        pass


    def test_correct_backend(self):
        mymap = {'rootitem': self.root,         # == /rootitem
                 'child/joe': self.child,       # Direct child of namespace.
                 'child/': self.child,          # Root of namespace itself (!= root)
                 '': self.root,
                }

        for itemname, backend in mymap.iteritems():
            assert self.backend._get_backend(itemname)[0] is backend
