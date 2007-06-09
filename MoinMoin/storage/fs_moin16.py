"""
    MoinMoin 1.6 compatible storage backend

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
    
    TODO: locking
"""


import codecs
import os
import re
import shutil

from MoinMoin import config
from MoinMoin.storage.interfaces import DataBackend, StorageBackend
from MoinMoin.storage.error import StorageError

user_re = re.compile(r'^\d+\.\d+(\.\d+)?$')


class AbstractStorage(StorageBackend):
    """
    Abstract Storage Implementation for common methods.
    """
    
    def __init__(self, path, cfg):
        """
        Init the Backend with the correct path.
        """
        if not os.path.isdir(path):
            raise StorageError("Invalid path '%s'." % path)
        self.path = path
        self.cfg = cfg
    
    def list_items(self, items, filters=None):
        """ 
        @see MoinMoin.interfaces.StorageBackend.list_items
        
        TODO: indexes
        """
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
        return self._parse_metadata(name, revno)

    def set_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.interfaces.StorageBackend.set_metadata
        """
        old_metadata = self._parse_metadata(name, revno)
        old_metadata.update(metadata)
        self._save_metadata(name, revno, old_metadata)

    def remove_metadata(self, name, revno, keylist):
        """
        @see MoinMoin.interfaces.StorageBackend.remove_metadata
        """
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
        files = os.listdir(self.path)
        user_files = [f for f in files if user_re.match(f)]
        
        return super(UserStorage, self).list_items(user_files, filters)
                
    def has_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.has_item
        """
        return os.path.isfile(os.path.join(self.path, name))

    def create_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.create_item
        """
        create_file(self.path, name)

    def remove_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.remove_item
        """
        try:
            os.remove(os.path.join(self.path, name))
        except OSError:
            raise StorageError("Item '%s' does not exist" % name)
        
    def list_revisions(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.list_revisions
        
        Users have no revisions.
        """
        return [1]

    def _parse_metadata(self, name, revno):
        """
        @see MoinMoin.fs_moin16.AbstractStorage._parse_metadata
        """
        
        try:
            data = codecs.open(os.path.join(self.path, name), "r", config.charset).readlines()
        except IOError:
            raise StorageError("Item '%s' does not exist" % name)
            
        user_data = {}
        for line in data:
            if line[0] == '#':
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
        data = codecs.open(os.path.join(self.path, name), "w", config.charset)
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
            data.write(line)
        data.close()


class PageStorage(AbstractStorage):
    """
    This class implements the MoinMoin 1.6 compatible Page Storage Stuff.
    """
        
    def list_items(self, filters=None):
        """ 
        @see MoinMoin.interfaces.StorageBackend.list_items
        """
        files = os.listdir(self.path)
        
        return super(PageStorage, self).list_items(files, filters)

    def has_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.has_item
        """
        if name:
            return os.path.isdir(os.path.join(self.path, name))
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
            raise StorageError("Item '%s' already exists" % name)

    def remove_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.remove_item
        """
        try:
            shutil.rmtree(os.path.join(self.path, name))
        except OSError:
            raise StorageError("Item '%s' does not exist" % name)

    def list_revisions(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.list_revisions
        
        Users have no revisions.
        """
        try:
            revs = os.listdir(os.path.join(self.path, name, "revisions"))
            revs = [rev for rev in revs if rev[-3:] != "tmp"]
            return map(lambda rev: int(rev), revs)
        except OSError:
            raise StorageError("Item '%s' does not exist" % name)
    
    def create_revision(self, name, revno):
        """
        @see MoinMoin.interfaces.StorageBackend.create_revisions
        """
        create_file(self.path, name, "revisions", get_rev_string(revno))

    def remove_revision(self, name, revno):
        """
        @see MoinMoin.interfaces.StorageBackend.remove_revisions
        """
        try:
            os.remove(os.path.join(self.path, name, "revisions", get_rev_string(revno)))
        except OSError:
            raise StorageError("Item '%s' does not exist" % name)
    
    def _parse_metadata(self, name, revno):
        """
        @see MoinMoin.fs_moin16.AbstractStorage._parse_metadata
        """
        
        try:
            data_file = codecs.open(os.path.join(self.path, name, "revisions", get_rev_string(revno)), "r", config.charset)
        except IOError:
            raise StorageError("Item '%s' or revision '%s' does not exist." % (name, revno))
        
        metadata = {}
        
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
                
            elif started == True:
                break
        data_file.close()

        return metadata
    
    def _save_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.fs_moin16.AbstractStorage._save_metadata
        """
        try:
            data = codecs.open(os.path.join(self.path, name, "revisions", get_rev_string(revno)), "r", config.charset).readlines()
        except IOError:
            raise StorageError("Item '%s' or revision '%s' does not exist." % (name, revno))
        
        # remove metadata
        new_data = [line for line in data if not line.startswith('#') and not line == '#' and not line == '##']

        # add metadata
        for key, value in metadata.iteritems():
            new_data.insert(0, "#%s %s\n" % (key, value))

        # save data
        try:
            data_file = codecs.open(os.path.join(self.path, name, "revisions", get_rev_string(revno)), "w", config.charset)
        except IOError:
            raise StorageError("Item '%s' or revision '%s' does not exist." % (name, revno))
        
        data_file.writelines(new_data)
        data_file.close()
        
    def get_data_backend(self, name, revno):
        """
        @see MoinMoin.interfaces.StorageBackend.get_data_backend
        """
        return PageData(self.path, name, revno)
    
    
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
        
        self.changed = False
        
        try:
            self.read_file = codecs.open(self.read_file_name, "r", config.charset)
            self.write_file = codecs.open(self.write_file_name, "w", config.charset)
        except IOError:
            raise StorageError("Item '%s' or revision '%s' does not exist." % (name, revno))
    
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
        self.write_file.close()
        self.read_file.close()
        
        if self.changed is True:
            shutil.move(self.write_file_name, self.read_file_name)
        else:
            os.remove(self.write_file_name)
    

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
        try:
            file_descriptor = open(real_path, "w")
            file_descriptor.close()
        except IOError:
            raise StorageError("Could not create %s." % real_path)
    else:
        raise StorageError("Path %s already exists" % real_path)
    