"""
    MoinMoin storage interfaces

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

class StorageBackend(object):
    """
    This class describes the main interface a StorageBackend must implement.
    """

    name = ""

    def list_items(self, filters=None):
        """
        Returns a list of all item names that match the given filters.
        If filters is None all items will be returned. Filters is a
        dictionary. One entry specifies a metadata key and a value
        that the metadata key must match.

        For faster access the backend may use indexes which are defined in the
        the configuration. Indexes specify metadata keys for which the backend
        will hold special caches for faster access. This can be compared
        with indexes in SQL or LDAP.
        """

    def has_item(self, name):
        """
        Checks whether the item exists, even if the current revision is deleted.
        Returns the backend the item belongs to on success, None on error.
        """

    def create_item(self, name):
        """
        Creates a new item. Returns the backend in which it was created.
        """

    def remove_item(self, name):
        """
        Removes (nukes) an item.
        """

    def rename_item(self, name, newname):
        """
        Renames an item to newname.
        """

    def list_revisions(self, name):
        """
        Returns a list of integers of all revision numbers of an item, -1 excluded.
        """

    def current_revision(self, name, includeEmpty=False):
        """
        Returns the last revision number of an item as integer. If there is
        no revision it returns 0. IncludeEmpty specifies wether a revision
        number should be return if there is no data in it. If False the first
        revision with data in it will be returend.
        """

    def has_revision(self, name, revno):
        """
        Returns whether the given revision number exists for the given item.
        It also returns True if the revision is empty. If revno is 0 it will
        be checked if there is any revision. -1 will return True.
        """

    def create_revision(self, name, revno):
        """
        Creates a new revision. If revno is 0 the next possible revision
        will be created. The return value is the newly created revision
        number. revno must be bigger than -1.
        """

    def remove_revision(self, name, revno):
        """
        Removes a specified revision. If revno is 0 the last revision
        will be deleted (nuked). The return value is the removed revision
        number. revno must be bigger than -1.
        """

    def get_metadata_backend(self, name, revno):
        """
        Returns a metadata backend object which behaves like a dictionary.
        If revno is 0 the current revision will be used. If revno is -1 the
        item-wide metadata will be used. Raises no error if the name or revno
        does not exists. The error will only be raised on access.
        """

    def get_data_backend(self, name, revno):
        """
        Get the data of an item-revision. If revno is 0 the current revision
        will be used. Raises no error if the name or revno does not exists. The
        error will only be raised on access.
        """

    def lock(self, identifier, timeout=1, lifetime=60):
        """
        Removes a lock for the given identifier.
        """

    def unlock(self, identifier):
        """
        Creates a lock for the given identifier.
        """


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

    def seek(self, offset):
        """
        Set the reader to a specified position in the stream.
        """

    def tell(self):
        """
        Returns the current position in the stream.
        """

    def write(self, data):
        """
        Write new data into the stream.
        """

    def close(self):
        """
        Close the stream.
        """


class MetadataBackend(object):
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

    def __getitem__(self, key):
        """
        Returns a specified value.
        """

    def __setitem__(self, key, value):
        """
        Adds a value.
        """

    def __delitem__(self, key):
        """
        Deletes a value.
        """

    def keys(self):
        """
        Return sa list of all metadata keys.
        """

    def save(self):
        """
        Saves the metadata.
        """
