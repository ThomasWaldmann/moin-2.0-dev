# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - MemoryBackend

    This defines tests for the MemoryBackend.

    ---

    @copyright: 2008 MoinMoin:ChristopherDenter,
                2008 MoinMoin:JohannesBerg,
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.wrapper import ROWrapperBackend
from MoinMoin.storage.backends.memory import MemoryBackend

class TestROWrapperBackend(BackendTest):
    """
    Test the MemoryBackend
    """
    def __init__(self):
        BackendTest.__init__(self, None)

    def create_backend(self):
        return ROWrapperBackend(MemoryBackend(), MemoryBackend())

    def kill_backend(self):
        pass
