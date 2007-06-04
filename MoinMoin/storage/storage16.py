"""
    MoinMoin 1.6 compatible storage backend

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""


import codecs
import os
import re

import MoinMoin.config

from MoinMoin.storage.interfaces import StorageBackend
from MoinMoin.storage.error import StorageError

user_re = re.compile(r'^\d+\.\d+(\.\d+)?$')


class UserStorage(StorageBackend):
    """
    Class that implements the 1.6 compatible storage backend for users.
    """
    
    def __init__(self, path, cfg):
        """
        Init the Backend with the correct path.
        """
        if not os.path.isdir(path):
            raise StorageError("Invalid path '%s'." % path)
        self.path = path
        self.cfg = cfg
        
    def list_items(self, filters=None):
        """ 
        @see MoinMoin.interfaces.StorageBackend.list_items
        
        TODO: indexes
        """
        files = os.listdir(self.path)
        user_files = [f for f in files if user_re.match(f)]
        if filters is None:
            return user_files
        else:
            filtered_files = []
            for key, value in filters.iteritems():
                expression = re.compile(value)
                if key not in self.cfg.indexes:
                    for name in user_files:
                        metadata = self.get_metadata(name, 0)
                        if metadata.has_key(key) and expression.match(metadata[key]):
                            filtered_files.append(name)
                else:
                    pass
            return filtered_files

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
            file_descriptor = open(os.path.join(self.path, name), "w")
            file_descriptor.close()
        else:
            raise StorageError("Item '%s' already exists" % name)

    def remove_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.remove_item
        """
        try:
            os.remove(os.path.join(self.path, name))
        except:
            raise StorageError("Item '%s' does not exist" % name)
        
    def list_revisions(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.list_revisions
        
        Users have no revisions.
        """
        return [1]

    def get_metadata(self, name, revno):
        """
        @see MoinMoin.interfaces.StorageBackend.get_metadata
        """
        return self.__parse_metadata(name)

    def set_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.interfaces.StorageBackend.get_data_backend
        """
        old_metadata = self.__parse_metadata(name)
        old_metadata.update(metadata)
        self.__save_metadata(name, old_metadata)

    def remove_metadata(self, name, revno, keylist):
        """
        @see MoinMoin.interfaces.StorageBackend.get_data_backend
        """
        metadata = self.__parse_metadata(name)
        for key in keylist:
            del metadata[key]
        self.__save_metadata(name, metadata)

    def __parse_metadata(self, name):
        """
        Read the metadata fromt the file.
        
        TODO: caching
        """
        
        try:
            data = codecs.open(os.path.join(self.path, name), "r", MoinMoin.config.charset).readlines()
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
    
    def __save_metadata(self, name, metadata):
        """
        Save the data to the file.
        
        TODO: update indexes
        """
        data = codecs.open(os.path.join(self.path, name), "w", MoinMoin.config.charset)
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

def encode_list(items):
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

def decode_list(line):
    """ Decode list of items from user data file
    
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

def decode_dict(line):
    """ Decode dict of key:value pairs from user data file
    
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
