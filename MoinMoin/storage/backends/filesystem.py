"""
    Abstract classes for file system storages.

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import bsddb
import copy
import os
import shutil
import tempfile
import time
import sqlite3
import thread

import UserDict

from MoinMoin import wikiutil
from MoinMoin.storage.backends.common import CommonBackend, _get_metadata
from MoinMoin.storage.interfaces import StorageBackend, DataBackend, MetadataBackend
from MoinMoin.storage.error import BackendError, LockingError
from MoinMoin.support.python_compatibility import sorted, set
from MoinMoin.util import lock, pickle


class AbstractBackend(object):
    """
    Abstract Storage Implementation for common filesystem methods.
    """

    __implements__ = StorageBackend

    locks = dict()

    def __new__(self, name, path, cfg, quoted=True, *kw, **kwargs):
        """
        Automatically wrap common and index functionality Backend.
        """
        backend = object.__new__(self, *kw, **kwargs)
        backend.__init__(name, path, cfg, *kw, **kwargs)
        return CommonBackend(name, IndexedBackend(backend, cfg))

    def __init__(self, name, path, cfg, quoted=True):
        """
        Init stuff.
        """
        if not os.path.isdir(path):
            raise BackendError(_("Invalid path %r.") % path)
        self.name = name
        self._path = path
        self._cfg = cfg
        self._quoted = quoted

    def _filter_items(self, items, filters=None):
        """
        @see MoinMoin.interfaces.StorageBackend._filter_items
        """
        if self._quoted:
            items = [wikiutil.unquoteWikiname(f) for f in items]

        if filters:
            exclude = []
            for item in items:
                include = False
                metadata = _get_metadata(self, item, [-1, 0])
                for key, value in filters.iteritems():
                    if key in metadata:
                        if unicode(value) in _parse_value(metadata[key]):
                            include = True
                            break
                if not include:
                    exclude.append(item)
            items = set(items) - set(exclude)

        return sorted(list(items))

    def _get_item_path(self, name, *args):
        """
        Returns the full path with fs quoted page name.
        """
        if self._quoted:
            name = wikiutil.quoteWikinameFS(name)
        return os.path.join(self._path, name, *args)

    def _get_rev_path(self, name, revno):
        """
        Returns the path to a specified revision.
        """
        raise NotImplementedError

    def lock(self, identifier, timeout=1, lifetime=60):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.lock
        """
        if self._quoted:
            identifier = wikiutil.quoteWikinameFS(identifier)
        write_lock = lock.ExclusiveLock(os.path.join(self._cfg.tmp_dir, identifier), lifetime)
        if not write_lock.acquire(timeout):
            raise LockingError(_("There is already a lock for %r") % identifier)
        self.locks[identifier] = write_lock

    def unlock(self, identifier):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.unlock
        """
        if self._quoted:
            identifier = wikiutil.quoteWikinameFS(identifier)
        try:
            self.locks[identifier].release()
            del self.locks[identifier]
        except KeyError:
            pass


class AbstractMetadata(UserDict.DictMixin):
    """
    Abstract metadata class.
    """

    __implements__ = MetadataBackend

    def __init__(self, backend, name, revno):
        """"
        Initializes the metadata object with the required parameters.
        """
        self._backend = backend
        self._name = name
        self._revno = revno
        self._metadata_property = None
        self._org_metadata = None

    def __contains__(self, key):
        """
        @see MoinMoin.storage.external.Metadata.__contains__
        """
        return key in self._metadata

    def __getitem__(self, key):
        """
        @see MoinMoin.storage.external.Metadata.__getitem__
        """
        return self._metadata[key]

    def __setitem__(self, key, value):
        """
        @see MoinMoin.storage.external.Metadata.__setitem__
        """
        self._metadata[key] = value

    def __delitem__(self, key):
        """
        @see MoinMoin.storage.external.Metadata.__delitem__
        """
        del self._metadata[key]

    def keys(self):
        """
        @see MoinMoin.storage.external.Metadata.keys
        """
        return self._metadata.keys()

    def save(self):
        """
        @see MoinMoin.storage.external.Metadata.save
        """
        self._save_metadata(self._name, self._revno, self._metadata)
        self._metadata_property = None

    def _parse_metadata(self, name, revno):
        """
        @see MoinMoin.fs_moin16.AbstractBackend._parse_metadata
        """
        raise NotImplementedError

    def _save_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.fs_moin16.AbstractBackend._save_metadata
        """
        raise NotImplementedError

    def get_metadata(self):
        """
        Lazy load metadata.
        """
        if self._metadata_property is None:
            self._metadata_property = self._parse_metadata(self._name, self._revno)
            self._org_metadata = copy.copy(self._metadata_property)
        return self._metadata_property

    _metadata = property(get_metadata)


class AbstractData(object):
    """
    This class implements a read only, file like object.
    """

    __implements__ = DataBackend

    def __init__(self, backend, name, revno):
        """
        Init stuff and open the file.
        """
        self._backend = backend
        self._name = name
        self._revno = revno

        self._read_file_name = self._backend._get_rev_path(name, revno)

        self._read_property = None
        self._write_property = None

    def _get_read_file(self):
        """
        Lazy load read_file.
        """
        if self._read_property is None:
            self._read_property = file(self._read_file_name, "rb")
        return self._read_property

    _read_file = property(_get_read_file)

    def _get_write_file(self):
        """
        Lazy load write file.
        """
        if self._write_property is None:
            self._tmp_handle, self._tmp_name = tempfile.mkstemp(dir=self._backend._cfg.tmp_dir)
            self._write_property = os.fdopen(self._tmp_handle, "wb")
        return self._write_property

    _write_file = property(_get_write_file)

    def read(self, size=None):
        """
        @see MoinMoin.storage.interfaces.DataBackend.read
        """
        if size is not None:
            return self._read_file.read(size)
        else:
            return self._read_file.read()

    def seek(self, offset):
        """
        @see MoinMoin.storage.interfaces.DataBackend.seek
        """
        self._read_file.seek(offset)

    def tell(self):
        """
        @see MoinMoin.storage.interfaces.DataBackend.tell
        """
        return self._read_file.tell()

    def write(self, data):
        """
        @see MoinMoin.storage.interfaces.DataBackend.write
        """
        self._write_file.write(data)

    def close(self):
        """
        @see MoinMoin.storage.interfaces.DataBackend.close
        """
        if not self._read_property is None:
            self._read_file.close()
            self._read_property = None
        if not self._write_property is None:
            self._write_file.close()
            shutil.move(self._tmp_name, self._read_file_name)
            self._write_property = None


class IndexedBackend(object):
    """
    This backend provides access to indexes.
    """

    __implements__ = StorageBackend

    def __init__(self, backend, cfg):
        """
        Initialises the class.
        """
        if not os.path.isdir(cfg.indexes_dir):
            raise BackendError(_("Invalid path %r.") % cfg.indexes_dir)
        self._backend = backend

        # index stuff
        self._path = cfg.indexes_dir
        self._indexes = cfg.indexes

        # news stuff
        self._connections = {}

    def __getattr__(self, name):
        """
        Get attribute from other backend if we don't have one.
        """
        return getattr(self._backend, name)

    def list_items(self, filters=None):
        """
        @see MoinMoin.interfaces.StorageBackend._filter_items
        """
        if filters:
            index_filters = dict([(key, value) for key, value in filters.iteritems() if key in self._indexes])
            other_filters = dict([(key, value) for key, value in filters.iteritems() if key not in self._indexes])
        else:
            index_filters, other_filters = {}, {}

        items = set(self._backend.list_items(other_filters))

        for key, value in index_filters.iteritems():
            items = items & set(self._get_items(key, value))

        return sorted(list(items))

    def remove_item(self, item):
        """
        @see MoinMoin.interfaces.StorageBackend.remove_item
        """
        self._remove_indexes(item, _get_metadata(self._backend, item, [-1, 0]))
        self._backend.remove_item(item)

    def rename_item(self, oldname, newname):
        """
        @see MoinMoin.interfaces.StorageBackend.rename_item
        """
        self._remove_indexes(oldname, _get_metadata(self._backend, oldname, [-1, 0]))
        self._backend.rename_item(oldname, newname)
        self._write_indexes(newname, _get_metadata(self._backend, newname, [-1, 0]))

    def create_revision(self, item, revno):
        """
        @see MoinMoin.interfaces.StorageBackend.create_revision
        """
        self._remove_indexes(item, _get_metadata(self._backend, item, [0]))
        self._backend.create_revision(item, revno)

    def remove_revision(self, item, revno):
        """
        @see MoinMoin.interfaces.StorageBackend.remove_revision
        """
        self._remove_indexes(item, _get_metadata(self._backend, item, [revno]))
        self._backend.remove_revision(item, revno)
        self._write_indexes(item, _get_metadata(self._backend, item, [0]))

    def get_metadata_backend(self, item, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.get_metadata_backend
        """
        return IndexedMetadata(self._backend.get_metadata_backend(item, revno), self, item, revno)

    def _rebuild_indexes(self):
        """
        Rebuilds all indexes.
        """
        indexes = dict()

        for item in self._backend.list_items():
            # get metadata
            metadata = _get_metadata(self._backend, item, [-1, 0])

            # set metadata
            for index in self._indexes:
                if index in metadata:
                    for key in _parse_value(metadata[index]):
                        indexes.setdefault(index, {}).setdefault(key, []).append(item)

        # write indexes
        for index, values in indexes.iteritems():
            db = bsddb.hashopen(self._get_index_file(index), "n")
            for key, value in values.iteritems():
                pkey = unicode(key).encode("utf-8")
                db[pkey] = pickle.dumps(value)
            db.close()

    def _get_items(self, key, value):
        """
        Returns the items that have a key which maches the value.
        """
        db = bsddb.hashopen(self._get_index_file(key, create=True))

        pvalue = unicode(value).encode("utf-8")
        if pvalue in db:
            values = pickle.loads(db[pvalue])
        else:
            values = []

        db.close()

        return values

    def _remove_indexes(self, item, metadata):
        """
        Remove old index data.
        """
        for index in self._indexes:
            if index in metadata:
                db = bsddb.hashopen(self._get_index_file(index, create=True))
                for key in _parse_value(metadata[index]):
                    pkey = unicode(key).encode("utf-8")
                    data = pickle.loads(db[pkey])
                    try:
                        data.remove(item)
                    except ValueError:
                        pass
                    db[pkey] = pickle.dumps(data)
                db.close()

    def _write_indexes(self, item, metadata):
        """
        Write new index data.
        """
        for index in self._indexes:
            if index in metadata:
                db = bsddb.hashopen(self._get_index_file(index, create=True))
                for key in _parse_value(metadata[index]):
                    pkey = unicode(key).encode("utf-8")
                    if not pkey in db:
                        db[pkey] = pickle.dumps([])
                    data = pickle.loads(db[pkey])
                    data.append(item)
                    db[pkey] = pickle.dumps(data)
                db.close()

    def _get_index_file(self, index, create=False):
        """
        Returns the filename and rebuilds the index when it does not exist yet.
        """
        filename = os.path.join(self._path, self._backend.name + "-" + index)
        if create and not os.path.isfile(filename):
            self._rebuild_indexes()
        return filename

    def news(self, timestamp=0):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.news
        """
        mtime = os.path.getmtime(self._get_news_file(create=True))
        if mtime > timestamp:
            c = self._get_cursor(create=True)
            c.execute("select mtime, revno, item from news where mtime>=? order by mtime DESC", (timestamp, ))
            try:
                return c.fetchall()
            except:
                return []
        return []

    def _create_db(self):
        """
        Creates the news db.
        """
        c = self._get_cursor(create=False)
        c.execute("create table news (mtime real, revno integer, item text)")
        c.execute("create index index_mtime on news (mtime desc)")
        c.execute("create unique index prim on news (item, revno)")
        for item in self.list_items():
            for revno in self.list_revisions(item):
                try:
                    mtime = os.path.getmtime(self._get_rev_path(item, revno))
                except:
                    continue
                c.execute("insert into news values (?, ?, ?)", (mtime, revno, item))

    def _get_cursor(self, create=False):
        """
        Returns a cursor to use.
        """
        try:
            return self._connections[thread.get_ident()]
        except KeyError:
            self._connections[thread.get_ident()] = sqlite3.connect(self._get_news_file(create=create), isolation_level=None).cursor()
            return self._connections[thread.get_ident()]

    def _get_news_file(self, create=False):
        """
        Returns the path of the newsfile.
        """
        filename = os.path.join(self._cfg.tmp_dir, self.name + "-news")
        if create and not os.path.exists(filename):
            self._create_db()
        return filename

    def _update_news(self, item, revno):
        """
        Updates the news cache.
        """
        c = self._get_cursor(create=True)
        c.execute("delete from news where revno=? and item=?", (revno, item))
        c.execute("insert into news values (?, ?, ?)", (time.time(), revno, item))


class IndexedMetadata(UserDict.DictMixin):
    """
    Metadata class for indexed metadata.
    """

    __implements__ = MetadataBackend

    def __init__(self, metadata, backend, item, revno):
        """
        Initialises the class.
        """
        self._metadata = metadata
        self._backend = backend
        self._item = item
        self._revno = revno

        # forward underscore methods
        forward = ['__setitem__', '__delitem__', '__getitem__', '__contains__']

        for method in forward:
            setattr(self, method, getattr(metadata, method))

    def __getattr__(self, name):
        """
        Forward everything else as well.
        """
        return getattr(self._metadata, name)

    def save(self):
        """
        @see MoinMoin.storage.external.Metadata.save
        """
        self._backend._remove_indexes(self._item, _get_metadata(self._backend, self._item, [self._revno]))
        self._metadata.save()
        self._backend._write_indexes(self._item, _get_metadata(self._backend, self._item, [self._revno]))
        self._backend._update_news(self._item, self._revno)


def _parse_value(value):
    """
    Return all keys that should be added to an index depending on the value of an metadata key.
    """
    ttype = type(value)
    if ttype in ['list', 'tuple']:
        keys = value
    elif ttype in ['dict']:
        keys = value.keys()
    else:
        keys = [unicode(value)]
    return keys


def _get_rev_string(revno):
    """
    Returns the string for a given revision integer.
    e.g. 00000001 for 1
    """
    return '%08d' % revno


def _create_file(*path):
    """
    Creates a file and raises an error if creating failed or the path already exists.
    """
    real_path = os.path.join(*path)

    if not os.path.exists(real_path):
        file(real_path, "w").close()
    else:
        raise BackendError(_("Path %r already exists.") % real_path)


_ = lambda x: x
