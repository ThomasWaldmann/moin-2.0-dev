# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - SQLAlchemyBackend

    This defines tests for the SQLAlchemyBackend.

    @copyright: 2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

from StringIO import StringIO

import py

from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.sqla import SQLAlchemyBackend, SQLARevision, Data


class TestSQLABackend(BackendTest):
    def __init__(self):
        BackendTest.__init__(self, None)

    def create_backend(self):
        return SQLAlchemyBackend(verbose=True)

    def kill_backend(self):
        pass


class TestChunkedRevDataStorage(object):
    raw_data = "This is a very long sentence so I can properly test my program. I hope it works."

    def setup_method(self, meth):
        self.sqlabackend = SQLAlchemyBackend('sqlite:///:memory:')
        self.item = self.sqlabackend.create_item(u"test_item")
        self.rev = self.item.create_revision(0)
        self.rev.write(self.raw_data)
        self.item.commit()
        self.rev = self.item.get_revision(0)

    def test_read_empty(self):
        item = self.sqlabackend.create_item(u"empty_item")
        rev = item.create_revision(0)
        assert rev.read() == ''
        item.commit()
        rev = item.get_revision(0)
        assert rev.read() == ''

    def test_write_many_times(self):
        item = self.sqlabackend.create_item(u"test_write_many_times")
        rev = item.create_revision(0)
        rev._data._last_chunk.chunksize = 4
        rev.write("foo")
        rev.write("b")
        rev._data._last_chunk.chunksize = 4
        rev.write("aaar")
        item.commit()
        rev = item.get_revision(0)
        assert [chunk.data for chunk in rev._data._chunks] == ["foob", "aaar"]

    def test_read_more_than_is_there(self):
        assert self.rev.read(len(self.raw_data) + 1) == self.raw_data

    def test_full_read(self):
        assert self.rev.read() == self.raw_data

    def test_read_first_bytes(self):
        assert self.rev.read(5) == self.raw_data[:5]

    def test_read_successive(self):
        assert self.rev.read(5) == self.raw_data[:5]
        assert self.rev.read(5) == self.raw_data[5:10]
        assert self.rev.read(5) == self.raw_data[10:15]
        assert self.rev.read() == self.raw_data[15:]

    def test_with_different_chunksizes(self):
        # mainly a write() test
        for chunksize in range(1, len(self.raw_data) + 2):
            Data.chunksize = chunksize
            data = Data()
            data.write(self.raw_data)
            data.close()
            assert data.read() == self.raw_data

    def test_with_different_offsets(self):
        offsets = range(self.rev._data._last_chunk.chunksize)
        for offset in offsets:
            data = Data()
            data.write(self.raw_data)
            data.close()
            assert data.read(offset) == self.raw_data[:offset]
            assert data.read() == self.raw_data[offset:]

    def test_seek_and_tell(self):
        data_len = len(self.raw_data)
        half = data_len / 2
        tests = [
            (0, 0),
            (0, 1),
            (0, data_len-1),
            (0, data_len),
            (0, data_len+1), # beyond EOF
            (0, half),
            (1, 0),
            (1, half),
            (1, -half),
            (1, 0),
            (2, 0),
            (2, -1),
            (2, -data_len+1),
            (2, -data_len),
        ]
        sio = StringIO(self.raw_data)
        for mode, pos in tests:
            if mode == 1: # relative
                sio.seek(half, 0)
                self.rev._data.seek(half, 0)
            sio.seek(pos, mode)
            self.rev._data.seek(pos, mode)
            assert sio.tell() == self.rev._data.tell()
            assert sio.read() == self.rev._data.read()

