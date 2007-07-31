"""
    Abstract classes for file system storages.

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import bsddb
import copy
import errno
import os
import shutil
import tempfile

from MoinMoin import wikiutil
from MoinMoin.storage.interfaces import StorageBackend, DataBackend, MetadataBackend
from MoinMoin.storage.error import BackendError, LockingError, NoSuchItemError, NoSuchRevisionError
from MoinMoin.util import lock, pickle


class Indexes(object):
    """
    This class provides access to the indexes.
    """

    def __init__(self, backend, cfg):
        """
        Initialises the class.
        """
        if not os.path.isdir(cfg.indexes_dir):
            raise BackendError(_("Invalid path %r.") % cfg.indexes_dir)
        self._backend = backend
        self._path = cfg.indexes_dir
        self._indexes = cfg.indexes

    def _rebuild_indexes(self):
        """
        Rebuilds all indexes.
        """
        indexes = dict()

        for item in self._backend.list_items():
            # get metadata
            metadata = _get_last_metadata(self._backend, item)

            # set metadata
            for index in self._indexes:
                if index in metadata:
                    for key in _parse_value(metadata[index]):
                        indexes.setdefault(index, {}).setdefault(key, []).append(item)

        # write indexes
        for index, values in indexes.iteritems():
            db = bsddb.hashopen(self._get_filename(index), "n")
            for key, value in values.iteritems():
                pkey = unicode(key).encode("utf-8")
                db[pkey] = pickle.dumps(value)
            db.close()

    def get_items(self, key, value):
        """
        Returns the items that have a key which maches the value.
        """
        db = bsddb.hashopen(self._get_filename(key, create=True))

        pvalue = unicode(value).encode("utf-8")
        if pvalue in db:
            values = pickle.loads(db[pvalue])
        else:
            values = []

        db.close()

        return values

    def update_indexes(self, item, oldmetadata, newmetadata):
        """
        Updates the index values for item from oldmetadata to the newmetadata.

        This is not the nicest code, but it works.
        """
        for index in self._indexes:

            if index in oldmetadata and index in newmetadata:
                if oldmetadata[index] == newmetadata[index]:
                    continue

                db = bsddb.hashopen(self._get_filename(index, create=True))
                for key in _parse_value(oldmetadata[index]):
                    pkey = unicode(key).encode("utf-8")
                    data = pickle.loads(db[pkey])
                    try:
                        data.remove(item)
                    except ValueError:
                        pass
                    db[pkey] = pickle.dumps(data)
                for key in _parse_value(newmetadata[index]):
                    pkey = unicode(key).encode("utf-8")
                    if not pkey in db:
                        db[pkey] = pickle.dumps([])
                    data = pickle.loads(db[pkey])
                    data.append(item)
                    db[pkey] = pickle.dumps(data)
                db.close()

            elif index in oldmetadata:
                # remove old values
                db = bsddb.hashopen(self._get_filename(index, create=True))
                for key in _parse_value(oldmetadata[index]):
                    pkey = unicode(key).encode("utf-8")
                    data = pickle.loads(db[pkey])
                    try:
                        data.remove(item)
                    except ValueError:
                        pass
                    db[pkey] = pickle.dumps(data)
                db.close()

            elif index in newmetadata:
                # set new values
                db = bsddb.hashopen(self._get_filename(index, create=True))
                for key in _parse_value(newmetadata[index]):
                    pkey = unicode(key).encode("utf-8")
                    if not pkey in db:
                        db[pkey] = pickle.dumps([])
                    data = pickle.loads(db[pkey])
                    data.append(item)
                    db[pkey] = pickle.dumps(data)
                db.close()

    def _get_filename(self, index, create=False):
        """
        Returns the filename and rebuilds the index when it does not exist yet.
        """
        filename = os.path.join(self._path, self._backend.name + "-" + index)
        if create and not os.path.isfile(filename):
            self._rebuild_indexes()
        return filename


class AbstractStorage(StorageBackend):
    """
    Abstract Storage Implementation for common methods.
    """

    locks = dict()

    def __init__(self, name, path, cfg, quoted=True):
        """
        Init the Backend with the correct path.
        """
        StorageBackend.__init__(self, name)
        if not os.path.isdir(path):
            raise BackendError(_("Invalid path %r.") % path)
        self._path = path
        self._cfg = cfg
        self._indexes = Indexes(self, cfg)
        self._quoted = quoted

    def list_items(self, items, filters=None):
        """
        @see MoinMoin.interfaces.StorageBackend.list_items
        """
        if self._quoted:
            items = [wikiutil.unquoteWikiname(f) for f in items]
        items.sort()
        if filters is None:
            return items
        else:
            filtered_files = []
            for key, value in filters.iteritems():
                if key not in self._cfg.indexes:
                    for item in items:
                        metadata = _get_last_metadata(self, item)
                        if key in metadata:
                            if unicode(value) in _parse_value(metadata[key]):
                                filtered_files.append(item)
                else:
                    items = self._indexes.get_items(key, value)
                    filtered_files.extend(items)

            return filtered_files

    def _get_page_path(self, name, *args):
        """
        Returns the full path with fs quoted page name.
        """
        if self._quoted:
            name = wikiutil.quoteWikinameFS(name)
        return os.path.join(self._path, name, *args)

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


class AbstractMetadata(MetadataBackend):
    """
    Abstract metadata class.
    """
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
        self._backend._indexes.update_indexes(self._name, self._org_metadata, self._metadata)
        self._metadata_property = None

    def _parse_metadata(self, name, revno):
        """
        @see MoinMoin.fs_moin16.AbstractStorage._parse_metadata
        """
        raise NotImplementedError

    def _save_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.fs_moin16.AbstractStorage._save_metadata
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


class AbstractData(DataBackend):
    """
    This class implements a read only, file like object.
    Changes will only be saved on close().
    """

    def __init__(self, backend, name, revno):
        """
        Init stuff and open the file.
        """
        self._backend = backend
        self._name = name
        self._revno = revno

        self._read_file_name = self._backend._get_page_path(self._name, "revisions", _get_rev_string(self._revno))

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
            self._tmp = tempfile.mkstemp(dir=self._backend._cfg.tmp_dir)
            self._write_property = os.fdopen(self._tmp[0], "wb")
        return self._write_property

    _write_file = property(_get_write_file)

    def read(self, size=None):
        """
        @see MoinMoin.storage.interfaces.DataBackend.read
        """
        if size:
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
            shutil.move(self._tmp[1], self._read_file_name)
            self._write_property = None


def _get_last_metadata(backend, item):
    """
    Returns the metadata of revisions -1 and if exists 0 of an item.
    """
    metadata = dict()
    metadata_all = backend.get_metadata_backend(item, -1)
    metadata.update(metadata_all)
    if backend.has_revision(item, 0):
        metadata_last = backend.get_metadata_backend(item, 0)
        metadata.update(metadata_last)
    return metadata


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


def _handle_error(backend, err, name, revno=None, message=""):
    """
    Handle error messages.
    """
    if err.errno == errno.ENOENT:
        if not backend.has_item(name):
            raise NoSuchItemError(_("Item %r does not exist.") % name)
        elif revno is not None and not backend.has_revision(name, revno):
            raise NoSuchRevisionError(_("Revision %r of item %r does not exist.") % (revno, name))
    raise BackendError(message)


_ = lambda x: x
