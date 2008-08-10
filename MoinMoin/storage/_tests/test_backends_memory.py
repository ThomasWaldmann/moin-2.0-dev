# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - MemoryBackend

    This defines tests for the MemoryBackend.

    ---

    @copyright: 2008 MoinMoin:ChristopherDenter,
                2008 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.memory import MemoryBackend, TracingBackend

class TestMemoryBackend(BackendTest):
    """
    Test the MemoryBackend
    """
    def __init__(self):
        BackendTest.__init__(self, None)

    def create_backend(self):
        return MemoryBackend()

    def kill_backend(self):
        pass

class TestTracingBackend(BackendTest):
    def __init__(self):
        BackendTest.__init__(self, None)
        self.be = None

    def create_backend(self):
        assert self.be is None
        self.be = TracingBackend()
        return self.be

    def kill_backend(self):
        assert self.be is not None
        try:
            self.be.get_func() # lets see if it compiles
        finally:
            self.be = None

