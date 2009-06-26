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
        root = MemoryBackend()
        child = MemoryBackend()
        mapping = {'/': root, 'child/': child}
        return RouterBackend(mapping)

    def kill_backend(self):
        pass
