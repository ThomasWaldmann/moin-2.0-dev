"""
    MoinMoin 1.6 compatible storage backend

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
    
    TODO: locking
    TODO: indexes
    TODO: item wide metadata
"""

import codecs
import errno
import os
import re
import shutil

from MoinMoin import config
from MoinMoin.util import filesys
from MoinMoin.storage.interfaces import DataBackend, StorageBackend
from MoinMoin.storage.error import BackendError, NoSuchItemError, NoSuchRevisionError

user_re = re.compile(r'^\d+\.\d+(\.\d+)?$')


class AbstractStorage(StorageBackend):
    """
    Abstract Storage Implementation for common methods.
    """

    def __init__(self, path, cfg, name):
        """
        Init the Backend with the correct path.
        """
        if not os.path.isdir(path):
            raise BackendError("Invalid path %r." % path)
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
                        metadata = self.get_metadata(name, 0)
                        if metadata.has_key(key) and expression.match(metadata[key]):
                            filtered_files.append(name)
                else:
                    pass
            return filtered_files

    def get_metadata(self, name, revno):
        """
        @see MoinMoin.interfaces.StorageBackend.get_metadata
        """
        if revno == 0:
            revno = self.current_revision(name)

        return self._parse_metadata(name, revno)

    def set_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.interfaces.StorageBackend.set_metadata
        """
        if revno == 0:
            revno = self.current_revision(name)

        old_metadata = self._parse_metadata(name, revno)
        old_metadata.update(metadata)
        self._save_metadata(name, revno, old_metadata)

    def remove_metadata(self, name, revno, keylist):
        """
        @see MoinMoin.interfaces.StorageBackend.remove_metadata
        """
        if revno == 0:
            revno = self.current_revision(name)

        metadata = self._parse_metadata(name, revno)
        for key in keylist:
            del metadata[key]
        self._save_metadata(name, revno, metadata)

    def _parse_metadata(self, name):
        """
        Read the metadata from the file.
        """
        raise NotImplementedError

    def _save_metadata(self, name, metadata):
        """
        Save the data to the file.
        """
        raise NotImplementedError


class UserStorage(AbstractStorage):
    """
    Class that implements the 1.6 compatible storage backend for users.
    """

    def list_items(self, filters=None):
        """ 
        @see MoinMoin.interfaces.StorageBackend.list_items
        """
        files = [f for f in os.listdir(self.path)[:] if user_re.match(f)]

        return super(UserStorage, self).list_items(files, filters)

    def has_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.has_item
        """
        if name and os.path.isfile(os.path.join(self.path, name)):
            return self
        return False

    def create_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.create_item
        """
        create_file(self.path, name)
        return self

    def remove_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.remove_item
        """
        try:
            os.remove(os.path.join(self.path, name))
        except OSError, err:
            _handle_error(self, err, name, message="Failed to remove item %r.")

    def list_revisions(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.list_revisions
        
        Users have no revisions.
        """
        return [1, 0]

    def current_revision(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.current_revision
        """
        return 1

    def has_revision(self, name, revno):
        """
        @see MoinMoin.interfaces.StorageBackend.has_revision
        """
        return revno in self.list_revisions(name)

    def _parse_metadata(self, name, revno):
        """
        @see MoinMoin.fs_moin16.AbstractStorage._parse_metadata
        """
        try:
            data = codecs.open(os.path.join(self.path, name), "r", config.charset).readlines()
        except IOError, err:
            _handle_error(self, err, name, revno, message="Failed to parse metadata for item %r with revision %r." % (name, revno))

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
        @see MoinMoin.fs_moin16.AbstractStorage._save_metadata
        """
        try:
            data_file = codecs.open(os.path.join(self.path, name), "w", config.charset)
        except IOError, err:
            _handle_error(self, err, name, revno, message="Failed to save metadata for item %r with revision %r." % (name, revno))

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


class PageStorage(AbstractStorage):
    """
    This class implements the MoinMoin 1.6 compatible Page Storage Stuff.
    """

    def list_items(self, filters=None):
        """ 
        @see MoinMoin.interfaces.StorageBackend.list_items
        """
        files = os.listdir(self.path)[:]

        return super(PageStorage, self).list_items(files, filters)

    def has_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.has_item
        """
        if name and os.path.isdir(os.path.join(self.path, name)):
            return self
        return False

    def create_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.create_item
        """
        if not self.has_item(name):
            os.mkdir(os.path.join(self.path, name))
            os.mkdir(os.path.join(self.path, name, "cache"))
            os.mkdir(os.path.join(self.path, name, "cache", "__lock__"))
            os.mkdir(os.path.join(self.path, name, "revisions"))
            create_file(self.path, name, "current")
            create_file(self.path, name, "edit-log")
        else:
            raise BackendError("Item %r already exists" % name)

        return self

    def remove_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.remove_item
        """
        try:
            shutil.rmtree(os.path.join(self.path, name))
        except OSError, err:
            _handle_error(self, err, name, message="Failed to remove item %r." % name)

    def list_revisions(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.list_revisions
        
        Users have no revisions.
        """
        try:
            revs = os.listdir(os.path.join(self.path, name, "revisions"))[:]
            revs.insert(0, "0")
            revs = [int(rev) for rev in revs if not rev.endswith(".tmp")]
            revs.sort()
            revs.reverse()
            return revs
        except OSError, err:
            _handle_error(self, err, name, message="Failed to list revisions for item %r." % name)

    def current_revision(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.current_revision
        """
        try:
            data_file = file(os.path.join(self.path, name, "current"), "r")
            rev = data_file.read()
            data_file.close()
            return int(rev)
        except IOError, err:
            _handle_error(self, err, name, message="Failed to get current revision for item %r." % name)

    def has_revision(self, name, revno):
        """
        @see MoinMoin.interfaces.StorageBackend.has_revision
        """
        if revno == 0:
            revno = self.current_revision(name)

        return os.path.isfile(os.path.join(self.path, name, "revisions", get_rev_string(revno)))

    def create_revision(self, name, revno):
        """
        @see MoinMoin.interfaces.StorageBackend.create_revisions
        """
        if revno == 0:
            revno = self.current_revision(name) + 1

        try:
            create_file(self.path, name, "revisions", get_rev_string(revno))
            self._update_current(name)
        except IOError, err:
            _handle_error(self, err, name, revno, message="Failed to create revision for item %r with revision %r."  % (name, revno))

    def remove_revision(self, name, revno):
        """
        @see MoinMoin.interfaces.StorageBackend.remove_revisions
        """
        if revno == 0:
            revno = self.current_revision(name)

        try:
            os.remove(os.path.join(self.path, name, "revisions", get_rev_string(revno)))
            self._update_current(name)
        except OSError, err:
            _handle_error(self, err, name, revno, message="Failed to remove revision %r for item %r." % (revno, name))

    def _update_current(self, name, revno=0):
        """
        Update the current file.
        """
        if revno == 0:
            revno = self.list_revisions(name)[0]
            
        try:
            data_file = file(os.path.join(self.path, name, "current"), "w")
            data_file.write(get_rev_string(revno) + "\n")
            data_file.close()
        except IOError, err:
            _handle_error(self, err, name, message="Failed to set current revision for item %r." % name)

    def _parse_metadata(self, name, revno):
        """
        @see MoinMoin.fs_moin16.AbstractStorage._parse_metadata
        """
        
        metadata = {}
        
        if revno == -1:
            
            # Emulate the deleted status via a metadata flag
            current = self.current_revision(name)
            if not os.path.exists(os.path.join(self.path, name, "revisions", get_rev_string(current))):
                metadata['Deleted'] = True
            
        else:
        
            try:
                data_file = codecs.open(os.path.join(self.path, name, "revisions", get_rev_string(revno)), "r", config.charset)
            except IOError, err:
                _handle_error(self, err, name, revno, message="Failed to parse metadata for item %r with revision %r." % (name, revno))
    
            started = False
            for line in data_file.readlines():
                if line.startswith('#'):
                    started = True
                    if line[1] == '#': # two hash marks are a comment
                        continue
                    elif line == "#":
                        break
    
                    verb, args = (line[1:] + ' ').split(' ', 1) # split at the first blank
                    metadata[verb.lower()] = args.strip()
    
                elif started is True:
                    break
            data_file.close()

        return metadata

    def _save_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.fs_moin16.AbstractStorage._save_metadata
        """
        
        if revno == -1:
            
            if metadata['Deleted'] == True:
                self._update_current(name, self.current_revision(name) + 1)
            else:
                self._update_current(name)

        else:
        
            try:
                data = codecs.open(os.path.join(self.path, name, "revisions", get_rev_string(revno)), "r", config.charset).readlines()
            except IOError, err:
                _handle_error(self, err, name, revno, message="Failed to save metadata for item %r with revision %r." % (name, revno))
    
            # remove metadata
            new_data = [line for line in data if not line.startswith('#') and not line == '#' and not line == '##']
    
            # add metadata
            for key, value in metadata.iteritems():
                new_data.insert(0, "#%s %s\n" % (key, value))
    
            # save data
            try:
                data_file = codecs.open(os.path.join(self.path, name, "revisions", get_rev_string(revno)), "w", config.charset)
            except IOError, err:
                _handle_error(self, err, name, revno, message="Failed to save metadata for item %r with revision %r." % (name, revno))
    
            data_file.writelines(new_data)
            data_file.close()

    def get_data_backend(self, name, revno):
        """
        @see MoinMoin.interfaces.StorageBackend.get_data_backend
        """
        if revno == 0:
            revno = self.current_revision(name)

        if self.has_revision(name, revno):
            return PageData(self.path, name, revno)
        else:
            if not self.has_item(name):
                raise NoSuchItemError("Item %r does not exist." % name)
            else:
                raise NoSuchRevisionError("Revision %r of item %r does not exist." % (revno, name))

class PageData(DataBackend):
    """
    This class implements a File like object for MoinMoin 1.6 Page stuff.
    """

    def __init__(self, path, name, revno):
        """
        Init stuff and open the file.
        """
        self.read_file_name = os.path.join(path, name, "revisions", get_rev_string(revno))
        self.write_file_name = os.path.join(path, name, "revisions", get_rev_string(revno) + ".tmp")

        self.__read_file = None
        self.__write_file = None

    def get_read_file(self):
        """
        Lazy load read_file.
        """
        if self.__read_file is None:
            self.__read_file = codecs.open(self.read_file_name, "r", config.charset)
        return self.__read_file

    read_file = property(get_read_file)

    def get_write_file(self):
        """
        Lazy load write file.
        """
        if self.__write_file is None:
            self.__write_file = codecs.open(self.write_file_name, "w", config.charset)
        return self.__write_file

    write_file = property(get_write_file)

    def read(self, size=None):
        """
        @see MoinMoin.interfaces.DataBackend.read
        """
        return self.read_file.read(size)

    def seek(self, offset):
        """
        @see MoinMoin.interfaces.DataBackend.seek
        """
        self.read_file.seek(offset)

    def tell(self):
        """
        @see MoinMoin.interfaces.DataBackend.tell
        """
        return self.read_file.tell()

    def write(self, data):
        """
        @see MoinMoin.interfaces.DataBackend.write
        """
        self.write_file.write(data)
        self.changed = True

    def close(self):
        """
        @see MoinMoin.interfaces.DataBackend.close
        """
        if not self.__read_file is None:
            self.read_file.close()
        if not self.__write_file is None:
            self.write_file.close()
            filesys.rename(self.write_file_name, self.read_file_name)


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
        raise BackendError("Path %r already exists." % real_path)


def _handle_error(backend, err, name, revno=None, message=""):
    """
    Handle error messages.
    """
    if err.errno == errno.ENOENT:
        if not backend.has_item(name):
            raise NoSuchItemError("Item %r does not exist." % name)
        elif revno is not None and not backend.has_revision(name, revno):
            raise NoSuchRevisionError("Revision %r of item %r does not exist." % (revno, name))
    raise BackendError(message)

