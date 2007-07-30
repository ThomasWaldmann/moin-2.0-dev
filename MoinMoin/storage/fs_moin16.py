"""
    MoinMoin 1.6 compatible storage backend

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.

    TODO: edit log

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
"""

import codecs
import os
import re
import shutil
import tempfile

from MoinMoin import config
from MoinMoin.storage.fs_storage import AbstractStorage, AbstractData, AbstractMetadata, _handle_error, get_rev_string, create_file
from MoinMoin.storage.interfaces import DELETED, SIZE, LOCK_TIMESTAMP, LOCK_USER, MTIME, USERID, ADDR, HOSTNAME, COMMENT, EXTRA, ACTION
from MoinMoin.storage.error import BackendError
from MoinMoin.wikiutil import version2timestamp, timestamp2version

user_re = re.compile(r'^\d+\.\d+(\.\d+)?$')


class UserStorage(AbstractStorage):
    """
    Class that implements the 1.6 compatible storage backend for users.
    """

    def __init__(self, name, path, cfg):
        """
        Init the Backend with the correct path.
        """
        AbstractStorage.__init__(self, name, path, cfg, False)

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
            data = codecs.open(self._backend.get_page_path(name), "r", config.charset)
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

        data.close()

        return user_data

    def _save_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.fs_moin16.AbstractMetadata._save_metadata
        """

        tmp = tempfile.mkstemp(dir=self._backend.cfg.tmp_dir)

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
            shutil.move(tmp[1], self._backend.get_page_path(name))
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
        files = [f for f in os.listdir(self.path) if os.path.exists(os.path.join(self.path, f, "current"))]

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
            raise BackendError(_("You cannot rename to an empty item name."))

        if self.has_item(newname):
            raise BackendError(_("Failed to rename item because an item with name %r already exists.") % newname)

        try:
            shutil.move(self.get_page_path(name), self.get_page_path(newname))
        except OSError, err:
            _handle_error(self, err, name, message=_("Failed to rename item %r to %r.") % (name, newname))

    def list_revisions(self, name, real=False):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_revisions
        """
        if real:
            try:
                revs = os.listdir(self.get_page_path(name, "revisions"))
            except OSError, err:
                _handle_error(self, err, name, message=_("Failed to list revisions for item %r.") % name)

            revs = [int(rev) for rev in revs if not rev.endswith(".tmp")]
            revs.sort()

        else:
            last = self.current_revision(name, includeEmpty=True)
            revs = range(1, last + 1)

        revs.reverse()
        return revs

    def current_revision(self, name, includeEmpty=False):
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

        if rev == 0:
            return rev

        # Don't return revisions which are empty
        def get_latest_not_empty(rev):
            if rev == 0:
                return rev
            filename = self.get_page_path(name, "revisions", get_rev_string(rev))
            if os.path.isfile(filename) and os.path.getsize(filename) == 0L:
                return get_latest_not_empty(rev - 1)
            return rev

        if not includeEmpty:
            return get_latest_not_empty(rev)

        return rev

    def has_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_revision
        """
        if revno == 0:
            revno = self.current_revision(name, includeEmpty=True)

        return revno <= self.current_revision(name, includeEmpty=True)

    def create_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.create_revisions
        """
        if revno == 0:
            revno = self.current_revision(name, includeEmpty=True) + 1

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
            revno = self.current_revision(name, includeEmpty=True)

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
            revnos = self.list_revisions(name, real=True)
            if revnos:
                revno = revnos[0]

        tmp = tempfile.mkstemp(dir=self.cfg.tmp_dir)

        try:
            tmp_file = os.fdopen(tmp[0], "w")
            tmp_file.write(get_rev_string(revno) + "\n")
            tmp_file.close()
        except IOError, err:
            _handle_error(self, err, name, message=_("Failed to set current revision for item %r.") % name)

        try:
            shutil.move(tmp[1], self.get_page_path(name, "current"))
        except OSError, err:
            _handle_error(self, err, name, message=_("Failed to set current revision for item %r.") % name)

    def get_data_backend(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.get_data_backend
        """
        if revno == 0:
            revno = self.current_revision(name, includeEmpty=True)

        if revno != -1 and not os.path.exists(self.get_page_path(name, "revisions", get_rev_string(revno))):
            return DeletedPageData(self, name, revno)
        else:
            return PageData(self, name, revno)

    def get_metadata_backend(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.get_metadata_backend
        """
        if revno == 0:
            revno = self.current_revision(name, includeEmpty=True)

        if revno != -1 and not os.path.exists(self.get_page_path(name, "revisions", get_rev_string(revno))):
            return DeletedPageMetadata(self, name, revno)
        else:
            return PageMetadata(self, name, revno)


class PageData(AbstractData):
    """
    This class implements a read only, file like object for MoinMoin 1.6 Page stuff.
    Changes will only be saved on close().
    """
    pass


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

            # Emulate edit-lock
            if os.path.exists(self._backend.get_page_path(name, "edit-lock")):
                data_file = file(self._backend.get_page_path(name, "edit-lock"), "r")
                line = data_file.read()
                data_file.close()

                values = _parse_log_line(line)
                metadata[LOCK_TIMESTAMP] = values[0]
                if values[6]:
                    metadata[LOCK_USER] = values[6]
                else:
                    metadata[LOCK_USER] = values[4]

        else:

            try:
                data_file = codecs.open(self._backend.get_page_path(name, "revisions", get_rev_string(revno)), "r", config.charset)
            except IOError, err:
                _handle_error(self._backend, err, name, revno, message=_("Failed to parse metadata for item %r with revision %r.") % (name, revno))

            started = False
            for line in data_file:
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

            # add size and mtime
            try:
                metadata[SIZE] = os.path.getsize(self._backend.get_page_path(name, "revisions", get_rev_string(revno)))
            except OSError:
                metadata[SIZE] = 0L

            user, ip, host, comment, mtime, action, extra = "", "", "", "", "", "", ""

            try:
                data_file = file(self._backend.get_page_path(name, "edit-log"), "r")

                for line in data_file:
                    values = _parse_log_line(line)
                    mtime = version2timestamp(int(values[0]))
                    action = values[2]
                    ip = values[4]
                    host = values[5]
                    user = values[6]
                    extra = values[7]
                    comment = values[8]

            except IOError:
                pass

            data_file.close()
            metadata[MTIME] = mtime
            metadata[ACTION] = action
            metadata[USERID] = user
            metadata[ADDR] = ip
            metadata[HOSTNAME] = host
            metadata[EXTRA] = extra
            metadata[COMMENT] = comment
            metadata[DELETED] = False

        return metadata

    def _save_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.fs_moin16.AbstractMetadata._save_metadata
        """

        if revno == -1:
            # Emulate edilock
            if LOCK_TIMESTAMP in metadata and LOCK_USER in metadata:
                data_file = file(self._backend.get_page_path(name, "edit-lock"), "w")
                line = "\t".join([metadata[LOCK_TIMESTAMP], "0", "0", "0", "0", "0", metadata[LOCK_USER], "0", "0"])
                data_file.write(line + "\n")
                data_file.close()
            elif os.path.isfile(self._backend.get_page_path(name, "edit-lock")):
                os.remove(self._backend.get_page_path(name, "edit-lock"))

        else:

            tmp = tempfile.mkstemp(dir=self._backend.cfg.tmp_dir)
            read_filename = self._backend.get_page_path(name, "revisions", get_rev_string(revno))

            try:
                data = codecs.open(read_filename, "r", config.charset)
            except IOError, err:
                _handle_error(self._backend, err, name, revno, message=_("Failed to save metadata for item %r with revision %r.") % (name, revno))

            # remove metadata
            new_data = [line for line in data if not line.startswith('#') and not line == '#' and not line == '##']

            data.close()

            # add metadata
            metadata_data = ""
            for key, value in metadata.iteritems():

                # remove size metadata
                if key in [SIZE, MTIME, ACTION, USERID, ADDR, HOSTNAME, EXTRA, COMMENT, DELETED]:
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
                shutil.move(tmp[1], read_filename)
            except OSError, err:
                _handle_error(self._backend, err, name, revno, message=_("Failed to save metadata for item %r with revision %r.") % (name, revno))

            # save edit-log
            try:
                edit_log = codecs.open(self._backend.get_page_path(name, "edit-log"), "r")
            except IOError, err:
                _handle_error(self._backend, err, name, revno, message=_("Failed to save metadata for item %r with revision %r.") % (name, revno))

            result = []
            newline = "\t".join((str(timestamp2version(metadata[MTIME])), get_rev_string(revno), metadata[ACTION], name, metadata[ADDR], metadata[HOSTNAME], metadata[USERID], metadata[EXTRA], metadata[COMMENT])) + "\n"
            for line in edit_log:
                values = _parse_log_line(line)
                rev = int(values[1])
                if revno == rev:
                    continue
                if rev > revno:
                    result.append(newline)
                result.append(line)
            if not newline in result:
                result.append(newline)
            edit_log.close()

            try:
                edit_log = codecs.open(self._backend.get_page_path(name, "edit-log"), "w")
                edit_log.writelines(result)
                edit_log.close()
            except IOError, err:
                _handle_error(self._backend, err, name, revno, message=_("Failed to save metadata for item %r with revision %r.") % (name, revno))

            # Emulate deleted
            exists = os.path.exists(self._backend.get_page_path(name, "revisions", get_rev_string(revno)))
            if metadata[DELETED] and exists:
                os.remove(self._backend.get_page_path(name, "revisions", get_rev_string(revno)))


class DeletedPageMetadata(AbstractMetadata):
    """
    Metadata implementation of a deleted item.
    """

    def _parse_metadata(self, name, revno):
        """
        @see MoinMoin.fs_moin16.AbstractMetadata._parse_metadata
        """
        metadata = {}
        metadata[DELETED] = True
        metadata[SIZE] = 0
        metadata[MTIME] = 0
        metadata[ACTION] = ""
        metadata[USERID] = ""
        metadata[ADDR] = ""
        metadata[HOSTNAME] = ""
        metadata[EXTRA] = ""
        metadata[COMMENT] = ""
        return metadata

    def _save_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.fs_moin16.AbstractMetadata._save_metadata
        """
        if not metadata[DELETED]:
            self._backend.create_revision(revno)


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

