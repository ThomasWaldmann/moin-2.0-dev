"""
    MoinMoin storage interfaces

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import UserDict

"""
First define some constants.
"""

DELETED = "deleted"
SIZE = "size"
ACL = "acl"
LOCK_TIMESTAMP = "lock_timestamp"
LOCK_USER = "lock_user"

"""
Then the actual interface.
"""

class StorageBackend(object):
    """
    This class describes the main interface a StorageBackend must implement.
    """

    def list_items(self, filters=None):
        """ 
        Returns a list of all item names that match the given filters.
        If filters is None all items will be returned. Filters is a
        dictionary. One entry specifies a metadata key and a regular expression
        that the metadata key must match.
        
        For faster access the backend may use indexes which are defined in the
        the configuration. Indexes specify metadata keys for which the backend
        will hold special caches for faster access. This can be compared
        with indexes in SQL or LDAP.
        """
        raise NotImplementedError

    def has_item(self, name):
        """
        Checks whether the item exists, even if the current revision is deleted.
        Returns the backend the item belongs to on success, None on error.
        """
        raise NotImplementedError

    def create_item(self, name):
        """
        Creates a new item. Returns the backend in which it was created.
        """
        raise NotImplementedError

    def remove_item(self, name):
        """
        Removes (nukes) an item.
        """
        raise NotImplementedError

    def rename_item(self, name, newname):
        """
        Renames an item to newname.
        """
        raise NotImplementedError

    def list_revisions(self, name):
        """
        Returns a list of integers of all revision numbers of an item.
        """
        raise NotImplementedError

    def current_revision(self, name):
        """
        Returns the last revision number of an item as integer. If there is
        no revision it returns 0. It only returns the revision if there is
        already data in it otherwise it will return the revision before.
        """
        raise NotImplementedError

    def has_revision(self, name, revno):
        """
        Returns whether the given revision number exists for the given item.
        """
        raise NotImplementedError

    def create_revision(self, name, revno):
        """
        Creates a new revision. If revno is 0 the next possible revision
        will be created. The return value is the newly created revision
        number.
        """
        raise NotImplementedError

    def remove_revision(self, name, revno):
        """
        Removes a specified revision. If revno is 0 the last revision
        will be deleted (nuked). The return value is the removed revision
        number.
        """
        raise NotImplementedError

    def get_metadata_backend(self, name, revno):
        """
        Returns a metadata backend object which behaves like a dictionary.
        If revno is 0 the current revision will be used. If revno is -1 the
        item-wide metadata will be used.
        """
        raise NotImplementedError

    def get_data_backend(self, name, revno):
        """
        Get the data of an item-revision.
        """
        raise NotImplementedError
    
    def lock(self, identifier, timeout, lifetime):
        """
        Removes a lock for the given identifier.
        """
        raise NotImplementedError

    def unlock(self, identifier):
        """
        Creates a lock for the given identifier.
        """
        raise NotImplementedError


class DataBackend(object):
    """
    The DataBackend interface provides functionality to access the data of a
    backend via file like operations.
    """

    def read(self, size=None):
        """
        Read a data block of a specified size from the stream.
        If size is ommitted all data will be read.
        """
        raise NotImplementedError

    def seek(self, offset):
        """
        Set the reader to a specified position in the stream.
        """
        raise NotImplementedError

    def tell(self):
        """
        Returns the current position in the stream. 
        """
        raise NotImplementedError

    def write(self, data):
        """
        Write new data into the stream.
        """
        raise NotImplementedError

    def close(self):
        """
        Close the stream.
        """
        raise NotImplementedError

class MetadataBackend(UserDict.DictMixin, object):
    """ 
    The metadata of an Item. Access will be via a dict like interface.
    All metadata will be loaded on the first access to one key.
    On every access the ACLs will be checked. After changing values you
    have to call save() to persist the changes to disk.
    """
        
    def __contains__(self, key):
        """
        Checks if a key exists.
        """
        raise NotImplementedError

    def __getitem__(self, key):
        """
        Returns a specified value.
        """
        raise NotImplementedError

    def __setitem__(self, key, value):
        """
        Adds a value.
        """
        raise NotImplementedError

    def __delitem__(self, key):
        """
        Deletes a value.
        """
        raise NotImplementedError

    def keys(self):
        """
        Return sa list of all metadata keys.
        """
        raise NotImplementedError

    def save(self):
        """
        Saves the metadata.
        """
        raise NotImplementedError
    