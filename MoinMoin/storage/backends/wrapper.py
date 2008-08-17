# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Read-Only Wrapper Backend

    The backend class defined in this module serves as wrapper around two other
    backends, one of which writable, the other read-only.
    All operations that aim to manipulate items or revisions are deferred to the
    writable backend. The read-only backend only comes in, if information requested
    is not found in the writable backend but in the read-only backend.

    This module was written with MoinMoins underlay in mind, which, by using
    the appropriate backend (fs17) as read-only backend and another of the new
    backends as writable backend, can be used to obtain a full wiki without
    converting (i.e. copying) the underlay information to the productive backend.

    ---

    @copyright: 2008 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.storage import Backend
from MoinMoin.storage.error import NoSuchItemError

# TODO
# Problems: What happens if an Item of the second_backend is renamed? Think deeper about such problems and add behaviour where missing

class ROWrapperBackend(Backend):
    def __init__(self, writable_backend, readonly_backend):
        self.first = writable_backend
        self.second = readonly_backend

    def get_item(self, itemname):
        """
        Returns Item object or raises Exception if that Item does not exist.
        """
        try:
            return self.first.get_item(itemname)
        except NoSuchItemError:
            # This may itself raise NoSuchItemError in which case we don't want to catch it
            return self.second.get_item(itemname)

    def create_item(self, itemname):
        """
        Creates an item with a given itemname. If that Item already exists,
        raise an Exception.
        """
        # This may itself raise ItemAlreadyExistsError in which case we don't want to catch it
        return self.first.create_item(itemname)

    def iteritems(self):
        """
        Returns an iterator over all items available in this backend.
        (Like the dict method).
        """
        items = []
        names = {}
        for item in self.first.iteritems():
            names[item.name] = True
            yield item
        for item in self.second.iteritems():
            if not names[item.name]:
                yield item

    def history(self, reverse=True):
        """
        Returns an iterator over ALL revisions of ALL items stored in the
        backend.

        If reverse is True (default), give history in reverse revision
        timestamp order, otherwise in revision timestamp order.

        Note: some functionality (e.g. completely cloning one storage into
              another) requires that the iterator goes over really every
              revision we have).
        """
        revisions = []
        item_revs = []

        for revision in self.first.history(reverse):
            revisions.append(revision)
            item_revs.append((revision.revno, revision.item.name))
        for revision in self.second.history(reverse):
            if not (revision.revno, revision.item.name) in item_revs:
                revisions.append(revision)

        # TODO: SORT THIS ACCORDINGLY!
        return iter(revisions)
