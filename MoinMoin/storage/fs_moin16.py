"""
    MoinMoin 1.6 compatible storage backend

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.

    TODO: indexes
    TODO: item wide metadata
    TODO: wiki wide metadata

    NOTE: This implementation is not really thread safe on windows. Some
          operations will fail if there are still open file descriptors
          on one of the files belonging to the item. These operations are
          filesys.rename, os.rename and filesys.rmtree which are used by...

          _save_metadata: Not critical since the operation will simply fail.

          delete_item: Though this will end in an unconsistent state, because
                       some of the files of an item are removed and some not,
                       this is not critical, because the method is not called
                       by the user of the wiki, but only by the administrator.

          rename_item: Not critical since the operation will simply fail.

          _update_current: This will lead to an inconsistent state since
                           create_revision and remove_revision will first
                           create / remove the revision file and after
                           that try to update the current file which is then
                           not in sync with the real revisions.

          To make this really thread safe on windows a better locking mechanism
          or retrying of some operations must be implemented.
"""

import codecs
import errno
import os
import re
import shutil
import tempfile

from MoinMoin import config
from MoinMoin.util import filesys, lock
from MoinMoin.storage.interfaces import DataBackend, StorageBackend, MetadataBackend, DELETED, SIZE, LOCK_TIMESTAMP, LOCK_USER
from MoinMoin.storage.error import BackendError, NoSuchItemError, NoSuchRevisionError, LockingError
from MoinMoin.wikiutil import unquoteWikiname, quoteWikinameFS

user_re = re.compile(r'^\d+\.\d+(\.\d+)?$')


class AbstractStorage(StorageBackend):
    """
    Abstract Storage Implementation for common methods.
    """

    locks = dict()
    lockdir = tempfile.mkdtemp()

    def __init__(self, path, cfg, name):
        """
        Init the Backend with the correct path.
        """
        if not os.path.isdir(path):
            raise BackendError(_("Invalid path %r.") % path)
        self.path = path
        self.cfg = cfg
        self.name = name

    def list_items(self, items, filters=None):
        """
        @see MoinMoin.interfaces.StorageBackend.list_items
        """
        items.sort()
        if filters is None:
            return items
        else:
            filtered_files = []
            for key, value in filters.iteritems():
                expression = re.compile(value)
                if key not in self.cfg.indexes:
                    for name in items:
                        metadata = self.get_metadata_backend(name, 0)
                        if metadata.has_key(key) and expression.match(metadata[key]):
                            filtered_files.append(name)
                else:
                    pass
            return filtered_files

    def get_page_path(self, name, *args):
        """
        Returns the full path with fs quoted page name.
        """
        return os.path.join(self.path, name, *args)

    def lock(self, identifier, timeout=1, lifetime=60):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.lock
        """
        write_lock = lock.ExclusiveLock(os.path.join(self.lockdir, identifier), lifetime)
        if not write_lock.acquire(timeout):
            raise LockingError(_("There is already a lock for %r") % identifier)
        self.locks[identifier] = write_lock

    def unlock(self, identifier):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.unlock
        """
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
        self._metadata = self._parse_metadata(name, revno)

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


class UserStorage(AbstractStorage):
    """
    Class that implements the 1.6 compatible storage backend for users.
    """

    def list_items(self, filters=None):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_items
        """
        files = [f for f in os.listdir(self.path) if user_re.match(f)]

        return super(UserStorage, self).list_items(files, filters)

    def has_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_item
        """
        if os.path.isfile(os.path.join(self.path, name)):
            return self
        return None

    def create_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.create_item
        """
        create_file(self.path, name)
        return self

    def remove_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.remove_item
        """
        try:
            os.remove(os.path.join(self.path, name))
        except OSError, err:
            _handle_error(self, err, name, message=_("Failed to remove item %r.") % name)

    def list_revisions(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_revisions

        Users have no revisions.
        """
        return [1]

    def current_revision(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.current_revision
        """
        return 1

    def has_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_revision
        """
        return revno == 0 or revno in self.list_revisions(name)

    def get_metadata_backend(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.get_metadata_backend
        """
        return UserMetadata(self, name, revno)


class UserMetadata(AbstractMetadata):
    """
    Metadata class for the user backend.
    """

    def _parse_metadata(self, name, revno):
        """
        @see MoinMoin.fs_moin16.AbstractMetadata._parse_metadata
        """
        try:
            data_file = codecs.open(self._backend.get_page_path(name), "r", config.charset)
            data = data_file.readlines()
            data_file.close()
        except IOError, err:
            _handle_error(self._backend, err, name, revno, message=_("Failed to parse metadata for item %r with revision %r.") % (name, revno))

        user_data = {}
        for line in data:
            if line.startswith('#') or line.strip() == "":
                continue

            try:
                key, val = line.strip().split('=', 1)
                # Decode list values
                if key.endswith('[]'):
                    key = key[:-2]
                    val = decode_list(val)
                # Decode dict values
                elif key.endswith('{}'):
                    key = key[:-2]
                    val = decode_dict(val)
                user_data[key] = val
            except ValueError:
                pass

        return user_data

    def _save_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.fs_moin16.AbstractMetadata._save_metadata
        """

        tmp = tempfile.mkstemp()

        try:
            data_file = codecs.getwriter(config.charset)(os.fdopen(tmp[0], "w"))
        except IOError, err:
            _handle_error(self._backend, err, name, revno, message=_("Failed to save metadata for item %r with revision %r.") % (name, revno))

        for key, value in metadata.iteritems():
            # Encode list values
            if isinstance(value, list):
                key += '[]'
                value = encode_list(value)
            # Encode dict values
            elif isinstance(value, dict):
                key += '{}'
                value = encode_dict(value)
            line = u"%s=%s\n" % (key, unicode(value))
            data_file.write(line)
        data_file.close()

        try:
            filesys.rename(tmp[1], self._backend.get_page_path(name))
        except IOError, err:
            _handle_error(self._backend, err, name, revno, message=_("Failed to save metadata for item %r with revision %r.") % (name, revno))


class PageStorage(AbstractStorage):
    """
    This class implements the MoinMoin 1.6 compatible Page Storage Stuff.
    """

    def list_items(self, filters=None):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_items
        """
        files = [unquoteWikiname(f) for f in os.listdir(self.path) if os.path.exists(os.path.join(self.path, f, "current"))]

        return super(PageStorage, self).list_items(files, filters)

    def has_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_item
        """
        if os.path.isdir(self.get_page_path(name, "revisions")):
            return self
        return None

    def create_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.create_item
        """
        if not self.has_item(name):
            if not os.path.isdir(self.get_page_path(name)):
                os.mkdir(self.get_page_path(name))
            if not os.path.isdir(self.get_page_path(name, "cache")):
                os.mkdir(self.get_page_path(name, "cache"))
            if not os.path.isdir(self.get_page_path(name, "cache", "__lock__")):
                os.mkdir(self.get_page_path(name, "cache", "__lock__"))
            create_file(self.get_page_path(name, "current"))
            if not os.path.isfile(self.get_page_path(name, "edit-log")):
                create_file(self.get_page_path(name, "edit-log"))
            if not os.path.isdir(self.get_page_path(name, "revisions")):
                os.mkdir(self.get_page_path(name, "revisions"))
        else:
            raise BackendError(_("Item %r already exists") % name)

        return self

    def remove_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.remove_item
        """
        try:
            shutil.rmtree(self.get_page_path(name))
        except OSError, err:
            _handle_error(self, err, name, message=_("Failed to remove item %r.") % name)

    def rename_item(self, name, newname):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.rename_item
        """
        if name == newname:
            raise BackendError(_("Failed to rename item because name and newname are equal."))

        if not newname:
            raise BackendError(_("You cannot rename to an empty page name."))

        if self.has_item(newname):
            raise BackendError(_("Failed to rename item because an item with name %r already exists.") % newname)

        try:
            shutil.move(self.get_page_path(name), self.get_page_path(newname))
        except OSError, err:
            _handle_error(self, err, name, message=_("Failed to rename item %r to %r.") % (name, newname))

    def list_revisions(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_revisions
        """
        try:
            revs = os.listdir(self.get_page_path(name, "revisions"))
        except OSError, err:
            _handle_error(self, err, name, message=_("Failed to list revisions for item %r.") % name)

        revs = [int(rev) for rev in revs if not rev.endswith(".tmp")]
        revs.sort()
        revs.reverse()
        return revs

    def current_revision(self, name, real=True):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.current_revision
        """
        try:
            data_file = file(self.get_page_path(name, "current"), "r")
            rev = data_file.read().strip()
            data_file.close()
        except IOError, err:
            _handle_error(self, err, name, message=_("Failed to get current revision for item %r.") % name)

        rev = int(rev or 0)

        # Emulate deleted
        if not real or rev == 0:
            return rev

        # Don't return revisions which are empty
        def get_latest_not_empty(rev):
            if rev == 0:
                return rev
            filename = self.get_page_path(name, "revisions", get_rev_string(rev))
            if not os.path.isfile(filename) or os.path.getsize(filename) == 0L:
                return get_latest_not_empty(rev - 1)
            return rev

        return get_latest_not_empty(int(rev))

    def has_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_revision
        """
        if revno == 0:
            revno = self.current_revision(name)

        return os.path.isfile(self.get_page_path(name, "revisions", get_rev_string(revno)))

    def create_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.create_revisions
        """
        if revno == 0:
            revno = self.current_revision(name) + 1

        try:
            create_file(self.get_page_path(name, "revisions", get_rev_string(revno)))
        except IOError, err:
            _handle_error(self, err, name, revno, message=_("Failed to create revision for item %r with revision %r.")  % (name, revno))

        self._update_current(name)

        return revno

    def remove_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.remove_revisions
        """
        if revno == 0:
            revno = self.current_revision(name)

        try:
            os.remove(self.get_page_path(name, "revisions", get_rev_string(revno)))
        except OSError, err:
            _handle_error(self, err, name, revno, message=_("Failed to remove revision %r for item %r.") % (revno, name))

        self._update_current(name)

        return revno

    def _update_current(self, name, revno=0):
        """
        Update the current file.
        """
        if revno == 0:
            revno = self.list_revisions(name)[0]

        tmp = tempfile.mkstemp()

        try:
            tmp_file = os.fdopen(tmp[0], "w")
            tmp_file.write(get_rev_string(revno) + "\n")
            tmp_file.close()
        except IOError, err:
            _handle_error(self, err, name, message=_("Failed to set current revision for item %r.") % name)

        try:
            filesys.rename(tmp[1], self.get_page_path(name, "current"))
        except OSError, err:
            _handle_error(self, err, name, message=_("Failed to set current revision for item %r.") % name)

    def get_data_backend(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.get_data_backend
        """
        if revno == 0:
            revno = self.current_revision(name)

        if self.has_revision(name, revno):
            return PageData(self, name, revno)

        else:
            if not self.has_item(name):
                raise NoSuchItemError(_("Item %r does not exist.") % name)
            else:
                raise NoSuchRevisionError(_("Revision %r of item %r does not exist.") % (revno, name))

    def get_metadata_backend(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.get_metadata_backend
        """
        if revno == 0:
            revno = self.current_revision(name)

        return PageMetadata(self, name, revno)

    def get_page_path(self, name, *args):
        """
        @see MoinMoin.storage.fs_moin16.AbstractStorage.get_page_path

        TODO: cache the quoted name?
        """
        return AbstractStorage.get_page_path(self, quoteWikinameFS(name), *args)


class PageData(DataBackend):
    """
    This class implements a read only, file like object for MoinMoin 1.6 Page stuff.
    Changes will only be saved on close().
    """

    def __init__(self, backend, name, revno):
        """
        Init stuff and open the file.
        """
        self._backend = backend
        self._name = name
        self._revno = revno

        self._read_file_name = self._backend.get_page_path(self._name, "revisions", get_rev_string(self._revno))

        self._read_property = None
        self._write_property = None

    def _get_read_file(self):
        """
        Lazy load read_file.
        """
        if self._read_property is None:
            self._read_property = codecs.open(self._read_file_name, "r", config.charset)
        return self._read_property

    _read_file = property(_get_read_file)

    def _get_write_file(self):
        """
        Lazy load write file.
        """
        if self._write_property is None:
            self._tmp = tempfile.mkstemp()
            self._write_property = codecs.getwriter(config.charset)(os.fdopen(self._tmp[0], "w"))
        return self._write_property

    _write_file = property(_get_write_file)

    def read(self, size=None):
        """
        @see MoinMoin.storage.interfaces.DataBackend.read
        """
        return self._read_file.read(size)

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
        if not self._write_property is None:
            self._write_file.close()
            filesys.rename(self._tmp[1], self._read_file_name)


class PageMetadata(AbstractMetadata):
    """
    Metadata implementation of the page backend.
    """

    def _parse_metadata(self, name, revno):
        """
        @see MoinMoin.fs_moin16.AbstractMetadata._parse_metadata
        """
        metadata = {}

        if revno == -1:

            # Emulate the deleted status via a metadata flag
            current = self._backend.current_revision(name, real=False)
            if not os.path.exists(self._backend.get_page_path(name, "revisions", get_rev_string(current))):
                metadata[DELETED] = True

            # Emulate edit-lock
            if os.path.exists(self._backend.get_page_path(name, "edit-lock")):
                data_file = file(self._backend.get_page_path(name, "edit-lock"), "r")
                line = data_file.read().strip()
                data_file.close()
                if line:
                    values = line.split("\t")
                    metadata[LOCK_TIMESTAMP] = values[0]
                    if len(values) >= 7:
                        metadata[LOCK_USER] = values[6]
                    else:
                        metadata[LOCK_USER] = values[4]

        else:

            try:
                data_file = codecs.open(self._backend.get_page_path(name, "revisions", get_rev_string(revno)), "r", config.charset)
            except IOError, err:
                _handle_error(self._backend, err, name, revno, message=_("Failed to parse metadata for item %r with revision %r.") % (name, revno))

            started = False
            for line in data_file.readlines():
                if line.startswith('#'):
                    started = True
                    if line[1] == '#': # two hash marks are a comment
                        continue
                    elif line == "#":
                        break

                    verb, args = (line[1:] + ' ').split(' ', 1) # split at the first blank

                    verb = verb.lower().strip()
                    args = args.strip()

                    # metadata can be multiline
                    if verb == 'acl':
                        metadata.setdefault(verb, []).append(args)
                    else:
                        metadata[verb] = args

                elif started is True:
                    break
            data_file.close()

            # add size metadata
            metadata[SIZE] = os.path.getsize(self._backend.get_page_path(name, "revisions", get_rev_string(revno)))

        return metadata

    def _save_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.fs_moin16.AbstractMetadata._save_metadata
        """

        if revno == -1:

            # Emulate deleted
            if DELETED in metadata and metadata[DELETED]:
                self._backend._update_current(name, self._backend.current_revision(name) + 1)
            else:
                self._backend._update_current(name)

            # Emulate edilock
            if LOCK_TIMESTAMP in metadata and LOCK_USER in metadata:
                data_file = file(self._backend.get_page_path(name, "edit-lock"), "w")
                line = "\t".join([metadata[LOCK_TIMESTAMP], "0", "0", "0", "0", "0", metadata[LOCK_USER], "0", "0"])
                data_file.write(line + "\n")
                data_file.close()
            elif os.path.isfile(self._backend.get_page_path(name, "edit-lock")):
                os.remove(self._backend.get_page_path(name, "edit-lock"))

        else:

            tmp = tempfile.mkstemp()
            read_filename = self._backend.get_page_path(name, "revisions", get_rev_string(revno))

            try:
                data_file = codecs.open(read_filename, "r", config.charset)
                data = data_file.readlines()
                data_file.close()
            except IOError, err:
                _handle_error(self._backend, err, name, revno, message=_("Failed to save metadata for item %r with revision %r.") % (name, revno))

            # remove metadata
            new_data = [line for line in data if not line.startswith('#') and not line == '#' and not line == '##']

            # add metadata
            metadata_data = ""
            for key, value in metadata.iteritems():

                # remove size metadata
                if key == SIZE:
                    continue

                # special handling for list metadata like acls
                if isinstance(value, list):
                    for line in value:
                        metadata_data += "#%s %s\n" % (key, line)
                else:
                    metadata_data += "#%s %s\n" % (key, value)

            new_data.insert(0, metadata_data)

            # save data
            try:
                data_file = codecs.getwriter(config.charset)(os.fdopen(tmp[0], "w"))
            except IOError, err:
                _handle_error(self._backend, err, name, revno, message=_("Failed to save metadata for item %r with revision %r.") % (name, revno))

            data_file.writelines(new_data)
            data_file.close()

            try:
                filesys.rename(tmp[1], read_filename)
            except OSError, err:
                _handle_error(self._backend, err, name, revno, message=_("Failed to save metadata for item %r with revision %r.") % (name, revno))

            # update size
            metadata[SIZE] = os.path.getsize(self._backend.get_page_path(name, "revisions", get_rev_string(revno)))


def encode_list(items):
    """
    Encode list of items in user data file

    Items are separated by '\t' characters.

    @param items: list unicode strings
    @rtype: unicode
    @return: list encoded as unicode
    """
    line = []
    for item in items:
        item = item.strip()
        if not item:
            continue
        line.append(item)

    line = '\t'.join(line)
    return line

def decode_list(line):
    """
    Decode list of items from user data file

    @param line: line containing list of items, encoded with encode_list
    @rtype: list of unicode strings
    @return: list of items in encoded in line
    """
    items = []
    for item in line.split('\t'):
        item = item.strip()
        if not item:
            continue
        items.append(item)
    return items

def encode_dict(items):
    """
    Encode dict of items in user data file

    Items are separated by '\t' characters.
    Each item is key:value.

    @param items: dict of unicode:unicode
    @rtype: unicode
    @return: dict encoded as unicode
    """
    line = []
    for key, value in items.items():
        item = u'%s:%s' % (key, value)
        line.append(item)
    line = '\t'.join(line)
    return line

def decode_dict(line):
    """
    Decode dict of key:value pairs from user data file

    @param line: line containing a dict, encoded with encode_dict
    @rtype: dict
    @return: dict  unicode:unicode items
    """
    items = {}
    for item in line.split('\t'):
        item = item.strip()
        if not item:
            continue
        key, value = item.split(':', 1)
        items[key] = value
    return items


def get_rev_string(revno):
    """
    Returns the string for a given revision integer.
    e.g. 00000001 for 1
    """
    return '%08d' % revno


def create_file(*path):
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
