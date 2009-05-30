"""
    MoinMoin storage errors

    @copyright: 2007 MoinMoin:HeinrichWendel,
                2008 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.error import CompositeError


class StorageError(CompositeError):
    """
    General class for exceptions on the storage layer.
    """
    pass

class AccessError(StorageError):
    """
    Raised if the action could not be commited because of access problems.
    """
    pass

class AccessDeniedError(AccessError):
    """
    Raised if the required rights are not available to commit the action.
    """
    pass

class LockingError(AccessError):
    """
    Raised if the action could not be commited because the Item is locked
    or the if the item could not be locked.
    """
    pass

class BackendError(StorageError):
    """
    Raised if the backend couldn't commit the action.
    """
    pass

class NoSuchItemError(BackendError):
    """
    Raised if the requested item does not exist.
    """
    pass

class ItemAlreadyExistsError(BackendError):
    """
    Raised if the Item you are trying to create already exists.
    """
    pass

class NoSuchRevisionError(BackendError):
    """
    Raised if the requested revision of an item does not exist.
    """
    pass

class RevisionAlreadyExistsError(BackendError):
    """
    Raised if the Revision you are trying to create already exists.
    """
    pass

class RevisionNumberMismatchError(BackendError):
    """
    Raised if a revision number that is not greater than the most recent revision
    number was passed or if the backend does not yet support non-contiguous or
    non-zero-based revision numbers and the operation violated these
    requirements.
    """
    pass
