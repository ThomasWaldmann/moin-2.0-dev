"""
    MoinMoin storage errors

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

class StorageError(Exception):
    """
    General class for exceptions on the storage layer.
    """
    pass

class AccessError(StorageError):
    """
    Raised if the action could not be commited because of access problems.
    """
    pass

class ACLError(AccessError):
    """
    Raised if the required rights are not available to commit the action.
    """
    pass

class LockedError(AccessError):
    """
    Raised if the action could not be commited because the Item is locked.
    """
    pass

class BackendError(StorageError):
    """
    Raised if the backend couldn't commit the action.
    """
    pass

class ItemNotExistsError(BackendError):
    """
    Raised if the requested item does not exist.
    """

class RevisionNotExistsError(BackendError):
    """
    Raised if the requested revision of an item does not exist.
    """

