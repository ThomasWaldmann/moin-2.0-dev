"""
    MoinMoin 1.6 compatible storage backend

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.storage.interfaces import StorageBackend

class UserStorage(StorageBackend):
    """
    Class that implements the 1.6 compatible storage backend for users.
    """
    
    def list_items(self, filters=None):
        """ 
        @see MoinMoin.interfaces.StorageBackend.list_items
        """
        raise NotImplementedError

    def has_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.has_item
        """
        raise NotImplementedError

    def create_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.create_item
        """
        raise NotImplementedError

    def remove_item(self, name):
        """
        @see MoinMoin.interfaces.StorageBackend.remove_item
        """
        raise NotImplementedError

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
        raise NotImplementedError

    def set_metadata(self, name, revno, key, value):
        """
        @see MoinMoin.interfaces.StorageBackend.get_data_backend
        """
        raise NotImplementedError

    def remove_metadata(self, name, revno, key):
        """
        @see MoinMoin.interfaces.StorageBackend.get_data_backend
        """
        raise NotImplementedError