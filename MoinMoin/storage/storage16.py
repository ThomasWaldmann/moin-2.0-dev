"""
    MoinMoin 1.6 compatible storage backend

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.storage.interfaces import StorageBackend
from MoinMoin.storage.error import StorageError
from MoinMoin.storage import config

import MoinMoin.config

import codecs
import os
import os.path
import re

class UserStorage(StorageBackend):
    """
    Class that implements the 1.6 compatible storage backend for users.
    """
    
    path = None
    
    def __init__(self, path):
        """
        Init the Backend with the correct path.
        """
        if not os.path.isdir(path):
            raise StorageError("Invalid path '%s'." % path)
        self.path = path
    
    def list_items(self, filters=None):
        """ 
        @see MoinMoin.interfaces.StorageBackend.list_items
        
        TODO: indexes
        """
        files = os.listdir(self.path)
        if not filters:
            return files
        else:
            real_files = []
            for key, value in filters.iteritems():
                expression = re.compile(value)
                if key not in config.indexes:
                    for name in files:
                        metadata = self.get_metadata(name, 0)
                        if metadata.has_key(key) and expression.match(metadata[key]):
                            real_files.append(name)
                else:
                    pass
            return real_files

    def has_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.has_item
        """
        return os.path.isfile(os.path.join(self.path, name))

    def create_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.create_item
        """
        if not self.has_item(name):
            fd = open(os.path.join(self.path, name), "w")
            fd.close()
        else:
            raise StorageError("Item '%s' already exists" % name)

    def remove_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.remove_item
        """
        if self.has_item(name):
            os.remove(os.path.join(self.path, name))
        else:
            raise StorageError("Item '%s' does not exist" % name)
        
    def list_revisions(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.list_revisions
        
        Users have no revisions.
        """
        return [1]

    def current_revision(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.current_revision
        
        Users have no revisions.
        """
        return 1

    def get_metadata(self, name, revno):
        """
        @see MoinMoin.interfaces.StorageBackend.get_metadata
        """
        return self.__parseMetadata(name)

    def set_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.interfaces.StorageBackend.get_data_backend
        """
        old_metadata = self.__parseMetadata(name)
        for key, value in metadata.iteritems():
            old_metadata[key] = value
        self.__saveMetadata(name, old_metadata)

    def remove_metadata(self, name, revno, keylist):
        """
        @see MoinMoin.interfaces.StorageBackend.get_data_backend
        """
        metadata = self.__parseMetadata(name)
        for key in keylist:
            del metadata[key]
        self.__saveMetadata(name, metadata)

    def __parseMetadata(self, name):
        """
        Read the metadata fromt the file.
        
        TODO: caching
        """
        data = codecs.open(os.path.join(self.path, name), "r", MoinMoin.config.charset).readlines()
        user_data = {}
        for line in data:
            if line[0] == '#':
                continue

            try:
                key, val = line.strip().split('=', 1)
                # Decode list values
                if key.endswith('[]'):
                    key = key[:-2]
                    val = decodeList(val)
                # Decode dict values
                elif key.endswith('{}'):
                    key = key[:-2]
                    val = decodeDict(val)
                user_data[key] = val
            except ValueError:
                pass
        return user_data
    
    def __saveMetadata(self, name, metadata):
        """
        Save the data to the file.
        
        TODO: update indexes
        """
        data = codecs.open(os.path.join(self.path, name), "w", MoinMoin.config.charset)
        for key, value in metadata.iteritems():
            # Encode list values
            if isinstance(value, list):
                key += '[]'
                value = encodeList(value)
            # Encode dict values
            elif isinstance(value, dict):
                key += '{}'
                value = encodeDict(value)
            line = u"%s=%s\n" % (key, unicode(value))
            data.write(line)
        data.close()

def encodeList(items):
    """ Encode list of items in user data file

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

def decodeList(line):
    """ Decode list of items from user data file
    
    @param line: line containing list of items, encoded with encodeList
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

def encodeDict(items):
    """ Encode dict of items in user data file

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

def decodeDict(line):
    """ Decode dict of key:value pairs from user data file
    
    @param line: line containing a dict, encoded with encodeDict
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