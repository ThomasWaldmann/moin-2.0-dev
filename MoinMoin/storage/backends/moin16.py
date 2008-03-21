"""
    MoinMoin 1.6 compatible storage backend

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.

    NOTE: This implementation is not really thread safe on windows. Some
          operations will fail if there are still open file descriptors
          on one of the files belonging to the item. These operations are
          os.remove, shutil.move and shutil.rmtree which are used by...

          _save_metadata: Not critical since the operation will simply fail.

          delete_item: Though this will end in an unconsistent state, because
                       some of the files of an item are removed and some not,
                       this is not critical, because the method is not called
                       by the user of the wiki, but only by the administrator.

          rename_item: This could lead to a copy of the item and a not completly
                       deleted old version.

          _update_current: This will lead to an inconsistent state since
                           create_revision and remove_revision will first
                           create / remove the revision file and after
                           that try to update the current file which is then
                           not in sync with the real revisions.

          To make this really thread safe on windows a better locking mechanism
          or retrying of some operations must be implemented.

    HOW DELETED WORKS:
        To be compatible with the 1.6 deleted procedure a few tricks had to be made.
        If a page will be deleted a new revision will be created for it. This revision
        will have no file in the revisions dir or the file will be empty. The current
        file will list this revision. When parsing such an empty or not-existant revision
        a DeletedPageData and DeletedPageMetadata file will be created.
"""

import codecs
import os
import re
import shutil
import tempfile

from MoinMoin.support.python_compatibility import sorted

from MoinMoin import config, wikiutil
from MoinMoin.storage.backends.common import _get_item_metadata_cache
from MoinMoin.storage.backends.filesystem import BaseFilesystemBackend, AbstractData, AbstractMetadata, _get_rev_string, _create_file, _parse_log_line
from MoinMoin.storage.external import DELETED, SIZE, EDIT_LOG, EDIT_LOCK
from MoinMoin.storage.external import EDIT_LOCK_TIMESTAMP, EDIT_LOCK_ADDR, EDIT_LOCK_HOSTNAME, EDIT_LOCK_USERID
from MoinMoin.storage.external import EDIT_LOG_MTIME, EDIT_LOG_USERID, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME, EDIT_LOG_COMMENT, EDIT_LOG_EXTRA, EDIT_LOG_ACTION


user_re = re.compile(r'^\d+\.\d+(\.\d+)?$')


class UserBackend(BaseFilesystemBackend):
    """
    Class that implements the 1.6 compatible storage backend for users.
    """

    def __init__(self, name, path, cfg):
        """
        Init the Backend with the correct path.
        """
        BaseFilesystemBackend.__init__(self, name, path, cfg, False)

    def list_items(self, filter):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_items
        """
        for f in os.listdir(self._path):
            if not user_re.match(f):
                continue
            if self._quoted:
                f = wikiutil.unquoteWikiname(f)
            filter.reset()
            if not filter.evaluate(self, f, _get_item_metadata_cache(self, f)):
                continue
            yield f

    def has_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_item
        """
        return os.path.isfile(os.path.join(self._path, name))

    def create_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.create_item
        """
        _create_file(self._path, name)

    def remove_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.remove_item
        """
        os.remove(os.path.join(self._path, name))

    def rename_item(self, name, newname):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.rename_item
        """
        shutil.move(self._get_item_path(name), self._get_item_path(newname))

    def list_revisions(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_revisions

        Users have only one revision.
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
        return revno in self.list_revisions(name)

    def get_metadata_backend(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.get_metadata_backend
        """
        return UserMetadata(self, name, revno)

    def _get_rev_path(self, name, revno, kind):
        """
        @see MoinMoin.storage.backends.filesystem.BaseFilesystemBackend._get_rev_path

        1.6 has only a single file (single rev) for a user.
        """
        return self._get_item_path(name)


class UserMetadata(AbstractMetadata):
    """
    Metadata class for the user backend.
    """

    def _parse_metadata(self, name, revno):
        """
        @see MoinMoin.storage.backends.filesystem.AbstractMetadata._parse_metadata
        """
        data_file = codecs.open(self._backend._get_item_path(name), "r", config.charset)

        metadata = {}
        for line in data_file:
            if line.startswith('#') or line.strip() == "":
                continue

            try:
                key, value = line.strip().split('=', 1)
                # Decode list values
                if key.endswith('[]'):
                    key = key[:-2]
                    value = _decode_list(value)
                # Decode dict values
                elif key.endswith('{}'):
                    key = key[:-2]
                    value = _decode_dict(value)
                metadata[key] = value
            except ValueError:
                pass

        data_file.close()

        return metadata

    def _save_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.storage.backends.filesystem.AbstractMetadata._save_metadata
        """

        tmp_handle, tmp_name = tempfile.mkstemp(dir=self._backend._cfg.tmp_dir)

        data_file = codecs.getwriter(config.charset)(os.fdopen(tmp_handle, "w"))

        for key, value in metadata.iteritems():
            # Encode list values
            if isinstance(value, list):
                key += '[]'
                value = _encode_list(value)
            # Encode dict values
            elif isinstance(value, dict):
                key += '{}'
                value = _encode_dict(value)
            line = u"%s=%s\n" % (key, unicode(value))
            data_file.write(line)
        data_file.close()

        shutil.move(tmp_name, self._backend._get_item_path(name))


class PageBackend(BaseFilesystemBackend):
    """
    This class implements the MoinMoin 1.6 compatible Page Storage Stuff.
    """

    def __init__(self, name, path, cfg):
        """
        Init the Backend with the correct path.
        """
        BaseFilesystemBackend.__init__(self, name, path, cfg, True)

    def list_items(self, filter):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_items
        """
        for f in os.listdir(self._path):
            if not os.path.isfile(os.path.join(self._path, f, "current")):
                continue
            if self._quoted:
                f = wikiutil.unquoteWikiname(f)
            filter.reset()
            if not filter.evaluate(self, f, _get_item_metadata_cache(self, f)):
                continue
            yield f

    def has_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_item
        """
        return os.path.isfile(self._get_item_path(name, "current"))

    def create_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.create_item
        """
        os.mkdir(self._get_item_path(name))
        os.mkdir(self._get_item_path(name, "cache"))
        os.mkdir(self._get_item_path(name, "cache", "__lock__"))
        _create_file(self._get_item_path(name, "current"))
        _create_file(self._get_item_path(name, "edit-log"))
        os.mkdir(self._get_item_path(name, "revisions"))

    def remove_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.remove_item
        """
        shutil.rmtree(self._get_item_path(name))

    def rename_item(self, name, newname):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.rename_item
        """
        shutil.move(self._get_item_path(name), self._get_item_path(newname))

    def list_revisions(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_revisions
        """
        revs = os.listdir(self._get_item_path(name, "revisions"))
        revs = [int(rev) for rev in revs if not rev.endswith(".tmp")]

        return sorted(revs, reverse=True)

    def current_revision(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.current_revision
        """
        current_file = file(self._get_item_path(name, "current"), "r")
        rev = current_file.read().strip()
        current_file.close()

        rev = int(rev or 0)

        return rev

    def has_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_revision
        """
        return -1 <= revno <= self.current_revision(name)

    def create_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.create_revisions
        """
        _create_file(self._get_rev_path(name, revno, 'data'))
        self._update_current(name)

    def remove_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.remove_revisions
        """
        os.remove(self._get_rev_path(name, revno, 'data'))
        self._update_current(name)

    def _update_current(self, name):
        """
        Update the current file.
        """
        revnos = self.list_revisions(name)
        if revnos:
            revno = revnos[0]
        else:
            revno = 0

        tmp_handle, tmp_name = tempfile.mkstemp(dir=self._cfg.tmp_dir)

        tmp_file = os.fdopen(tmp_handle, "w")
        tmp_file.write(_get_rev_string(revno) + "\n")
        tmp_file.close()

        shutil.move(tmp_name, self._get_item_path(name, "current"))

    def get_data_backend(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.get_data_backend
        """
        if revno == -1 or not os.path.exists(self._get_rev_path(name, revno, 'data')):
            return DeletedPageData(self, name, revno)
        else:
            return PageData(self, name, revno)

    def get_metadata_backend(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.get_metadata_backend
        """
        if revno != -1 and not os.path.exists(self._get_rev_path(name, revno, 'meta')): # gives same result as 'data'
            return DeletedPageMetadata(self, name, revno)
        else:
            return PageMetadata(self, name, revno)

    def _get_rev_path(self, name, revno, kind):
        """
        @see MoinMoin.storage.backends.filesystem.BaseFilesystemBackend._get_rev_path

        1.6 uses same file for 'meta' and 'data' kind.
        """
        return self._get_item_path(name, "revisions", _get_rev_string(revno))


class PageData(AbstractData):
    """
    This class implements a file like object for MoinMoin 1.6 Page stuff.
    """

    def read(self, size=None):
        """
        @see MoinMoin.storage.interfaces.DataBackend.read
        """
        data = AbstractData.read(self, size)
        metadata, data = wikiutil.split_body(data)
        return data


class PageMetadata(AbstractMetadata):
    """
    Metadata implementation of the page backend.
    """

    def _parse_metadata(self, name, revno):
        """
        @see MoinMoin.storage.backends.filesystem.AbstractMetadata._parse_metadata
        """
        metadata = {}

        if revno == -1:

            # emulate edit-lock
            if os.path.exists(self._backend._get_item_path(name, "edit-lock")):
                lock_file = file(self._backend._get_item_path(name, "edit-lock"), "r")
                line = lock_file.read()
                lock_file.close()

                values = _parse_log_line(line)
                metadata[EDIT_LOCK_TIMESTAMP] = str(wikiutil.version2timestamp(long(values[0])))
                metadata[EDIT_LOCK_ADDR] = values[4]
                metadata[EDIT_LOCK_HOSTNAME] = values[5]
                metadata[EDIT_LOCK_USERID] = values[6]

        else:

            data_file = codecs.open(self._backend._get_rev_path(name, revno, 'meta'), "r", config.charset)
            data = data_file.read()
            data_file.close()

            metadata, data = wikiutil.split_body(data)

            # emulated size
            try:
                metadata[SIZE] = str(os.path.getsize(self._backend._get_rev_path(name, revno, 'data')))
            except OSError:
                pass

            # emulate edit-log
            try:
                data_file = file(self._backend._get_item_path(name, "edit-log"), "r")

                for line in data_file:
                    values = _parse_log_line(line)
                    rev = int(values[1])
                    if rev == revno:
                        metadata[EDIT_LOG_MTIME] = str(wikiutil.version2timestamp(long(values[0])))
                        metadata[EDIT_LOG_ACTION] = values[2]
                        metadata[EDIT_LOG_ADDR] =  values[4]
                        metadata[EDIT_LOG_HOSTNAME] = values[5]
                        metadata[EDIT_LOG_USERID] = values[6]
                        metadata[EDIT_LOG_EXTRA] = values[7]
                        metadata[EDIT_LOG_COMMENT] = values[8]
                        break

                data_file.close()
            except IOError:
                pass

        return metadata

    def _save_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.storage.backends.filesystem.AbstractMetadata._save_metadata
        """

        if revno == -1:

            # emulate editlock
            for key in EDIT_LOCK:
                if not key in metadata:
                    if os.path.isfile(self._backend._get_item_path(name, "edit-lock")):
                        os.remove(self._backend._get_item_path(name, "edit-lock"))
                    break
            else:
                data_file = file(self._backend._get_item_path(name, "edit-lock"), "w")
                line = "\t".join([str(wikiutil.timestamp2version(float(metadata[EDIT_LOCK_TIMESTAMP]))), "0", "0", "0", metadata[EDIT_LOCK_ADDR], metadata[EDIT_LOCK_HOSTNAME], metadata[EDIT_LOCK_USERID], "0", "0"])
                data_file.write(line + "\n")
                data_file.close()

        else:

            tmp_handle, tmp_name = tempfile.mkstemp(dir=self._backend._cfg.tmp_dir)
            read_filename = self._backend._get_rev_path(name, revno, 'data')

            data = codecs.open(read_filename, "r", config.charset)
            old_metadata, new_data = wikiutil.split_body(data.read())
            data.close()

            new_data = wikiutil.add_metadata_to_body(metadata, new_data)

            data_file = codecs.getwriter(config.charset)(os.fdopen(tmp_handle, "w"))
            data_file.writelines(new_data)
            data_file.close()

            shutil.move(tmp_name, read_filename)

            # save edit-log
            for key in EDIT_LOG:
                if not key in metadata:
                    break
            else:
                result = []
                newline = "\t".join((str(wikiutil.timestamp2version(float(metadata[EDIT_LOG_MTIME]))), _get_rev_string(revno), metadata[EDIT_LOG_ACTION], name, metadata[EDIT_LOG_ADDR], metadata[EDIT_LOG_HOSTNAME], metadata[EDIT_LOG_USERID], metadata[EDIT_LOG_EXTRA], metadata[EDIT_LOG_COMMENT])) + "\n"

                try:
                    edit_log = codecs.open(self._backend._get_item_path(name, "edit-log"), "r", config.charset)
                    for line in edit_log:
                        values = _parse_log_line(line)
                        rev = int(values[1])
                        if revno == rev or rev == 99999999:
                            continue
                        if rev > revno:
                            result.append(newline)
                        result.append(line)
                    edit_log.close()
                except IOError:
                    pass

                if not newline in result:
                    result.append(newline)

                edit_log = codecs.open(self._backend._get_item_path(name, "edit-log"), "w", config.charset)
                edit_log.writelines(result)
                edit_log.close()

            # emulate deleted
            exists = os.path.exists(self._backend._get_rev_path(name, revno, 'data'))
            if DELETED in metadata and exists:
                os.remove(self._backend._get_rev_path(name, revno, 'data'))


class DeletedPageMetadata(AbstractMetadata):
    """
    Metadata implementation of a deleted item.
    """

    def _parse_metadata(self, name, revno):
        """
        @see MoinMoin.storage.backends.filesystem.AbstractMetadata._parse_metadata
        """
        metadata = {}
        metadata[DELETED] = None
        return metadata

    def _save_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.storage.backends.filesystem.AbstractMetadata._save_metadata
        """
        if not DELETED in metadata:
            self._backend.create_revision(self._name, revno)


class DeletedPageData(AbstractData):
    """
    This class implements the Data of a deleted item.
    """

    def __init__(self, backend, name, revno):
        """
        Init stuff and open the file.
        """
        pass

    def read(self, size=None):
        """
        @see MoinMoin.storage.interfaces.DataBackend.read
        """
        return ""

    def seek(self, offset):
        """
        @see MoinMoin.storage.interfaces.DataBackend.seek
        """
        pass

    def tell(self):
        """
        @see MoinMoin.storage.interfaces.DataBackend.tell
        """
        return 0

    def write(self, data):
        """
        @see MoinMoin.storage.interfaces.DataBackend.write
        """
        pass

    def close(self):
        """
        @see MoinMoin.storage.interfaces.DataBackend.close
        """
        pass


def _encode_list(items):
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


def _decode_list(line):
    """
    Decode list of items from user data file

    @param line: line containing list of items, encoded with _encode_list
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


def _encode_dict(items):
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


def _decode_dict(line):
    """
    Decode dict of key:value pairs from user data file

    @param line: line containing a dict, encoded with _encode_dict
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


_ = lambda x: x

