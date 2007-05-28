"""
    MoinMoin storage errors

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

class StorageError(Exception):
    """
    General class for exceptions on the storage layer.
    """

class AccessError(StorageError):
    """
    Raised if the action could not be commited because of access problems.
    """

class ACLError(AccessError):
    """
    Raised if the required rights are not available to commit the action.
    """

class LockedError(AccessError):
    """
    Raised if the action could not be commited because the Item is locked.
    """

class BackendError(StorageError):
    """
    Raised if the backend couldn't commit the action.
    """

class ConsistencyError(BackendError):
    """
    Raised if the action violates the consistency rules, e.g. when a second Item
    with the same name will be created.
    """
    
class NotImplementedError(StorageError):
    """
    Raised if a function from an interface was not implemented.
    """