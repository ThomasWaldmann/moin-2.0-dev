"""
    MoinMoin storage interfaces

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""


from MoinMoin.storage.error import NotImplementedError


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
        Checks whether the item exists. Even if the current revision is deleted,
        this will return True.
        """
        raise NotImplementedError

    def create_item(self, name):
        """
        Creates a new item.
        """
        raise NotImplementedError

    def remove_item(self, name):
        """
        Removes (nukes) an item.
        """
        raise NotImplementedError

    def list_revisions(self, name):
        """
        Returns a list of integers of all revision-numbers of an item.
        """
        raise NotImplementedError

    def current_revision(self, name):
        """
        Returns the last revision-number of an item as integer.
        """
        raise NotImplementedError

    def create_revision(self, name, revno):
        """
        Creates a new revision. If revno is 0 the next possible revision
        raise NotImplementedError
        will be created.
        """
        raise NotImplementedError

    def remove_revision(self, name, revno):
        """
        Removes a specified revision. If revno is 0 the last revision
        will be deleted (nuked).
        """
        raise NotImplementedError

    def get_metadata(self, name, revno):
        """
        Returns a dictionary of all metadata of an item. If revno is 0 the current
        revision will be used. If revno is -1 the item-wide metadata will be
        used.
        """
        raise NotImplementedError

    def set_metadata(self, name, revno, metadata):
        """
        Sets metadata values. If revno is 0 the current revision will be
        used. If revno is -1 the item-wide metadata will be used. Metadata
        is a dict with key -> value pairs.
        """
        raise NotImplementedError

    def remove_metadata(self, name, revno, keylist):
        """
        Removes alls keys in keylist from the metadata. If revno is 0 the current
        revision will be used. If revno is -1 the item-wide metadata will be
        used.
        """
        raise NotImplementedError

    def get_data_backend(self, name, revno, mode):
        """
        Get the data of an item-revision.
        mode can be r(ead) or w(rite) or a(append).
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