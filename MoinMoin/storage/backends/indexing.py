# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Indexing Middleware (IMW)

    This backend is a middleware implementing metadata (later maybe also data)
    indexing. It does not store any data, but uses a given backend for this.
    This middleware is injected between the ACL middleware and the actual
    backend used for storage. It is independent of the backend being used.

    XXX is this needed: Instances of the IMW are bound to individual request objects.

    The backend itself (and the objects it returns) need to be wrapped in order
    to make sure that no object of the real backend is (directly or indirectly)
    modified by the user of the API.

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from UserDict import DictMixin

from MoinMoin import log
logging = log.getLogger(__name__)


class IndexingWrapperBackend(object):
    """
    The IMW is bound to a specific request.
    The actual backend is retrieved from the config upon request initialization.
    Note: This may *not* inherit from MoinMoin.storage.Backend because that would
    break our __getattr__ attribute 'redirects' (which are necessary because a backend
    implementor may decide to use his own helper functions which the items and revisions
    will still try to call).
    """
    def __init__(self, request, backend):
        """
        @type request: MoinMoin request object
        @param request: The request that the user issued.
        @type backend: Some object that implements the storage API.
        @param backend: The backend that we want to index.
        """
        self.request = request
        self.backend = backend

    def __getattr__(self, attr):
        # Pass through any attribute lookup that is not subject to indexing.
        return getattr(self.backend, attr)

    def create_item(self, itemname):
        """
        create new item and wrap for indexing
        """
        real_item = self.backend.create_item(itemname)
        return IndexingWrapperItem(real_item, self)

    def get_item(self, itemname):
        """
        get existing item and wrap for indexing
        """
        real_item = self.backend.get_item(itemname)
        return IndexingWrapperItem(real_item, self)


class IndexingWrapperItem(object):
    """
    Similar to IndexingWrapperBackend. Wraps a storage item for indexing.
    """
    def __init__(self, item, indexingbackend):
        """
        @type item: Object adhering to the storage item API.
        @param item: The item we want to index.
        @type indexingbackend: Instance of IndexingWrapperBackend.
        @param indexingbackend: The IMW this item belongs to.
        """
        self.backend = indexingbackend
        self.item = item
        self._uncommitted_revision = None

    def __getattr__(self, attr):
        # Pass through any attribute lookup that is not subject to indexing.
        return getattr(self.item, attr)

    def get_revision(self, revno):
        """
        get an existing (wrapped-for-indexing) revision
        """
        revision = self.item.get_revision(revno)
        return IndexingWrapperRevision(self, revno, revision)

    def create_revision(self, revno):
        """
        create a new (wrapped-for-indexing) revision
        """
        revision = self.item.create_revision(revno)
        self._uncommitted_revision = IndexingWrapperRevision(self, revno, revision)
        return self._uncommitted_revision

    # TODO implement index update for item-level metadata
    def commit(self):
        """
        commit and index
        """
        self._uncommitted_revision.update_index()
        self._uncommitted_revision = None
        return self.item.commit()

    def rollback(self):
        self._uncommitted_revision = None
        return self.item.rollback()


class IndexingWrapperRevision(DictMixin):
    """
    Wrapper for revision classes. We need to wrap NewRevisions because they allow altering data.
    We need to wrap StoredRevisions since they offer a destroy() method and access to their item.
    The caller should know what kind of revision he gets. Hence, we just implement the methods of
    both, StoredRevision and NewRevision. If a method is invoked that is not defined on the
    kind of revision we wrap, we will see an AttributeError one level deeper anyway, so this is ok.
    """
    def __init__(self, item, revno, revision):
        """
        @type revision: Object adhering to the storage revision API.
        @param revision: The revision we want to index.
        @type item: Object adhering to the storage item API.
        @param item: The item this revision belongs to
        """
        self.revision = revision
        self._revno = revno # TODO: some code outside this class relies on ._revno
        self.item = item

    def __getattr__(self, attr):
        # Pass through any attribute lookup that is not subject to indexing.
        return getattr(self.revision, attr)

    def update_index(self):
        """
        update the index with metadata of this revision

        this is automatically called by item.commit() and can be used by a indexer script also.
        """
        logging.debug("item %r revno %d update index:" % (self['name'], self._revno))
        for k, v in self.items():
            logging.debug(" * rev meta %r: %r" % (k, v))
        # TODO implement real index update

    def remove_index(self):
        """
        update the index, removing everything related to this revision
        """
        logging.debug("item %r revno %d remove index!" % (self['name'], self._revno))
        # TODO implement real index removal


    def destroy(self):
        self.remove_index()
        return self.revision.destroy()

    # TODO maybe use this class later for data indexing also,
    # TODO by intercepting write() to index data written to a revision

