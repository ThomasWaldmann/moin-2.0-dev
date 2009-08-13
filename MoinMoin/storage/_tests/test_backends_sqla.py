# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - SQLAlchemyBackend

    This defines tests for the SQLAlchemyBackend.

    @copyright: 2009 MoinMoin:ChristopherDenter
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

