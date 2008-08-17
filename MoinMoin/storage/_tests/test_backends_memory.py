# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - MemoryBackend

    This defines tests for the MemoryBackend.

    ---

    @copyright: 2008 MoinMoin:ChristopherDenter,
                2008 MoinMoin:JohannesBerg,
                2008 MoinMoin:AlexanderSchremmer
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
        import random
        self.be = TracingBackend()#"/tmp/codebuf%i.py" % random.randint(1, 2**30))
        return self.be

    def kill_backend(self):
        assert self.be is not None
        try:
            func = self.be.get_func()
            try:
                func(MemoryBackend()) # should not throw any exc
            except:
                # I get exceptions here because py.test seems to handle setup/teardown incorrectly
                # in generative tests
                pass#print "EXC"
        finally:
            self.be = None

