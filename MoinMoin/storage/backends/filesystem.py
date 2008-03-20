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

import UserDict

from MoinMoin import wikiutil
from MoinMoin.storage.external import UNDERLAY
from MoinMoin.storage.backends.common import CommonBackend, _get_metadata
from MoinMoin.storage.interfaces import StorageBackend, DataBackend, MetadataBackend
from MoinMoin.storage.external import EDIT_LOG_ACTION, EDIT_LOG_EXTRA
from MoinMoin.storage.error import BackendError, LockingError
from MoinMoin.support.python_compatibility import sorted, set
from MoinMoin.util import lock, pickle, records


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

    def __init__(self, name, path, cfg, quoted=True, is_underlay=False):
        """
        Init stuff.
        """
        if not os.path.isdir(path):
            raise BackendError(_("Invalid path %r.") % path)
        self.name = name
        self._path = path
        self._cfg = cfg
        self._quoted = quoted
        self.is_underlay = is_underlay

    def _filter(self, item, filters, filterfn):
        """
        Filter the given items with the given filters by searching the metadata.
        """
        if self._quoted:
            item = wikiutil.unquoteWikiname(item)

        if not filters and not filterfn:
            return True

        metadata = _get_metadata(self, item, [-1, 0])

        if filters:
            for key, value in filters.iteritems():
                if key == UNDERLAY:
                    if value != self.is_underlay:
                        return False
                elif key in metadata:
                    if not unicode(value) in _parse_value(metadata[key]):
                        return False
                else:
                    return False

        if filterfn:
            return filterfn(item, metadata)

        return True

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
        @see MoinMoin.storage.interfaces.MetadataBackend.__contains__
        """
        return key in self._metadata

    def __getitem__(self, key):
        """
        @see MoinMoin.storage.interfaces.MetadataBackend.__getitem__
        """
        return self._metadata[key]

    def __setitem__(self, key, value):
        """
        @see MoinMoin.storage.interfaces.MetadataBackend.__setitem__
        """
        self._metadata[key] = value

    def __delitem__(self, key):
        """
        @see MoinMoin.storage.interfaces.MetadataBackend.__delitem__
        """
        del self._metadata[key]

    def keys(self):
        """
        @see MoinMoin.storage.interfaces.MetadataBackend.keys
        """
        return self._metadata.keys()

    def save(self):
        """
        @see MoinMoin.storage.interfaces.MetadataBackend.save
        """
        self._save_metadata(self._name, self._revno, self._metadata)
        self._metadata_property = None

    def _parse_metadata(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.MetadataBackend._parse_metadata
        """
        raise NotImplementedError

    def _save_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.storage.interfaces.MetadataBackend._save_metadata
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
    This class implements a file like object.
    """

    __implements__ = DataBackend

    def __init__(self, backend, name, revno):
        """
        Init stuff and open the file.
        """
        self._backend = backend
        self._name = name
        self._revno = revno

        self._read_file_name = self._backend._get_rev_path(name, revno, 'data')

        self._read_property = None
        self._write_property = None

    def _get_read_file(self):
        """
        Lazy load read file.
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

    def __getattr__(self, name):
        """
        Get attribute from other backend if we don't have one.
        """
        return getattr(self._backend, name)

    def list_items(self, filters, filterfn):
        """
        @see MoinMoin.interfaces.StorageBackend.list_items

        This really is a pessimisation, building a complete list first
        and then filtering it... Should build a list from the index first
        and then filter it further!
        """
        if filters:
            index_filters = dict([(key, value) for key, value in filters.iteritems() if key in self._indexes])
            other_filters = dict([(key, value) for key, value in filters.iteritems() if key not in self._indexes])
        else:
            index_filters, other_filters = {}, {}

        items = set(self._backend.list_items(other_filters, filterfn))

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

        for item in self._backend.list_items(None, None):
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

        mtime_file = open(self._get_news_file(create=True, mtime=True))
        mtime = wikiutil.version2timestamp(float(mtime_file.read()))
        mtime_file.close()
        if mtime >= timestamp:
            news_file = self._get_record(create=True)
            for data in news_file.reverse():
                assert data['magic'] == "#\r\n"
                mtime = wikiutil.version2timestamp(float(data['timestamp']))
                if mtime >= timestamp:
                    yield ((mtime, int(data['revno']), wikiutil.unquoteWikiname(data['itemname'])))
                else:
                    break
            news_file.close()

    def _create_db(self):
        """
        Creates the news db.
        """
        items = []
        for item in self.list_items(None, None):
            try:
                log_file = open(self._backend._get_item_path(item, "edit-log"), "r")
                for line in log_file:
                    line = _parse_log_line(line)
                    if line[1] != "99999999":
                        items.append((line[0], line[1], line[3]))
                log_file.close()
            except IOError:
                pass
        news_file = self._get_record(create=False)
        news_file.open("ab")
        items.sort()
        for item in items:
            news_file.write(timestamp=item[0], revno=item[1], itemname=item[2], magic='#\r\n')
        news_file.close()
        mtime_file = open(self._get_news_file(create=False, mtime=True), "w")
        mtime_file.write(str(wikiutil.timestamp2version(time.time())))
        mtime_file.close()

    def _get_record(self, create=False):
        """
        Returns a cursor to use.
        """
        return records.FixedRecordLogFile(self._get_news_file(create=create), 512, [('timestamp', 24), ('revno', 8), ('itemname', 477), ('magic', 3)])

    def _get_news_file(self, create=False, mtime=False):
        """
        Returns the path of the newsfile.
        """
        if mtime:
            filename = os.path.join(self._cfg.tmp_dir, self.name + "-news.mtime")
        else:
            filename = os.path.join(self._cfg.tmp_dir, self.name + "-news")
        if create and not os.path.exists(filename):
            self._create_db()
        return filename

    def _update_news(self, item, revno):
        """
        Updates the news cache.
        """
        news_file = self._get_record(create=True)
        mtime = str(wikiutil.timestamp2version(time.time()))
        news_file.open("ab")
        news_file.write(timestamp=mtime, revno=str(revno), itemname=wikiutil.quoteWikinameFS(item), magic='#\r\n')
        news_file.close()
        mtime_file = open(self._get_news_file(create=True, mtime=True), "w")
        mtime_file.write(mtime)
        mtime_file.close()


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
        @see MoinMoin.storage.interfaces.MetadataBackend.save
        """
        if self._revno != -1:
            self._backend._update_news(self._item, self._revno)
            if EDIT_LOG_ACTION in self._metadata and self._metadata[EDIT_LOG_ACTION] == "SAVE/RENAME":
                self._backend._update_news(self._metadata[EDIT_LOG_EXTRA], self._revno)

        self._backend._remove_indexes(self._item, _get_metadata(self._backend, self._item, [self._revno]))
        self._metadata.save()
        self._backend._write_indexes(self._item, _get_metadata(self._backend, self._item, [self._revno]))


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


def _parse_log_line(line):
    """
    Parses a line from the edit-log or lock.
    """
    fields = line.strip().split("\t")
    missing = 9 - len(fields)
    if missing:
        fields.extend([''] * missing)
    return fields


_ = lambda x: x
