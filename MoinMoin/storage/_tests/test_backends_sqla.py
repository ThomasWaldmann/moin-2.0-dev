# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - MemoryBackend

    This defines tests for the MemoryBackend.

    @copyright: 2008 MoinMoin:ChristopherDenter,
                2008 MoinMoin:JohannesBerg,
                2008 MoinMoin:AlexanderSchremmer
    @license: GNU GPL, see COPYING for details.
"""

import py

try:
    import sqlalchemy
except ImportError:
    py.test.skip('Cannot test without sqlalchemy installed.')

from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.sqla import SQLAlchemyBackend


class TestSQLABackend(BackendTest):
    def __init__(self):
        BackendTest.__init__(self, None)

    def create_backend(self):
        return SQLAlchemyBackend(verbose=True)

    def kill_backend(self):
        pass


    def test_item_reading_chunks(self):
        py.test.skip("Makes all tests hang. Find out why.")

