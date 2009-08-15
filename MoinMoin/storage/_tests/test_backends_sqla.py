# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - SQLAlchemyBackend

    This defines tests for the SQLAlchemyBackend.

    @copyright: 2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

from StringIO import StringIO

import py

try:
    import sqlalchemy
    if sqlalchemy.__version__ < '0.5.4':
        raise AssertionError
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
except ImportError:
    py.test.skip('Cannot test without sqlalchemy installed.')
except AssertionError:
    py.test.skip('You need at least version 0.5.4 of sqlalchemy.')

from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.sqla import SQLAlchemyBackend, SQLARevision, Data


class TestSQLABackend(BackendTest):
    def __init__(self):
        BackendTest.__init__(self, None)

    def create_backend(self):
        return SQLAlchemyBackend(verbose=True)

    def kill_backend(self):
        pass


raw_data = "This is a very long sentence so I can properly test my program. I hope it works."

class TestChunkedRevDataStorage(object):
    def setup_method(self, meth):
        self.sqlabackend = SQLAlchemyBackend()
        self.item = self.sqlabackend.create_item("test_item")
        self.rev = self.item.create_revision(0)
        self.rev.write(raw_data)

    def test_read_empty(self):
        item = self.sqlabackend.create_item("empty_item")
        rev = item.create_revision(0)
        assert rev.read() == ''
        item.commit()
        assert rev.read() == ''

    def test_write_many_times(self):
        item = self.sqlabackend.create_item("test_write_many_times")
        rev = item.create_revision(0)
        rev._data.chunksize = 4
        rev.write("foo")
        rev.write("baaaaaaar")
        item.commit()
        assert [chunk.data for chunk in rev._data._chunks] == ["foob", "aaaa", "aaar"]

    def test_read_more_than_is_there(self):
        assert self.rev.read(len(raw_data) + 1) == raw_data

    def test_full_read(self):
        assert self.rev.read() == raw_data

    def test_read_first_bytes(self):
        assert self.rev.read(5) == raw_data[:5]

    def test_read_successive(self):
        assert self.rev.read(5) == raw_data[:5]
        assert self.rev.read(5) == raw_data[5:10]
        assert self.rev.read(5) == raw_data[10:15]
        assert self.rev.read() == raw_data[15:]

    def test_with_different_chunksizes(self):
        # mainly a write() test
        length = len(raw_data)
        chunksizes = range(length)
        for chunksize in chunksizes:
            data = Data()
            # Don't test with chunksize == 0 but test with a chunksize larger than input data
            data._last_chunk.chunksize = chunksize + 1
            data.write(raw_data)
            assert data.read() == raw_data

    def test_with_different_offsets(self):
        offsets = range(self.rev._data._last_chunk.chunksize)
        for offset in offsets:
            data = Data()
            data.write(raw_data)
            assert data.read(offset) == raw_data[:offset]
            assert data.read() == raw_data[offset:]

    def test_seek_and_tell(self):
        sio = StringIO(raw_data)
        for mode in (0, 1, 2):
            for pos in xrange(2 * len(raw_data)):
                sio.seek(pos, mode)
                self.rev._data.seek(pos, mode)
                assert sio.tell() == self.rev._data.tell()
                assert sio.read() == self.rev._data.read()

