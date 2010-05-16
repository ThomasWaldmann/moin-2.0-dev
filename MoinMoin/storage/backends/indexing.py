# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Indexing Middleware (IMW)

    This backend is a middleware implementing metadata (later maybe also data)
    indexing. It does not store any data, but uses a given target backend for
    this. This middleware is injected directly above the real storage backend.
    It is independent of the backend being used.

    The target backend itself (and the items / revisions it returns) need to
    be all proxied (wrapped in a proxy object) in order to make sure that no
    object of the target backend is (directly or indirectly) modified by the
    user of the API.

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from objectproxy import Proxy

from MoinMoin import log
logging = log.getLogger(__name__)


class IndexingProxyBackend(Proxy):
    """
    Gives proxy items, not the target items.
    """
    def create_item(self, itemname):
        s = super(self.__class__, self)
        real_item = s.create_item(itemname)
        return IndexingProxyItem(real_item, self)

    def get_item(self, itemname):
        s = super(self.__class__, self)
        real_item = s.get_item(itemname)
        return IndexingProxyItem(real_item, self)


class IndexingProxyItem(Proxy):
    """
    Gives proxy revisions, not the real revisions.

    When a commit happens, index stuff.
    """
    def __init__(self, backend):
        self.__backend = backend
        self.__unindexed_revision = None

    def get_revision(self, revno):
        s = super(self.__class__, self)
        real_revision = s.get_revision(revno)
        return IndexingProxyRevision(real_revision, self)

    def create_revision(self, revno):
        s = super(self.__class__, self)
        real_revision = s.create_revision(revno)
        self.__unindexed_revision = IndexingProxyRevision(real_revision, self)
        return self.__unindexed_revision

    def commit(self):
        self.__unindexed_revision.update_index()
        self.__unindexed_revision = None
        s = super(self.__class__, self)
        return s.commit()

    def rollback(self):
        self.__unindexed_revision = None
        s = super(self.__class__, self)
        return s.rollback()

    def publish_metadata(self):
        self.update_index()
        s = super(self.__class__, self)
        return s.publish_metadata()

    def destroy(self):
        self.remove_index()
        s = super(self.__class__, self)
        return s.destroy()

    def update_index(self):
        """
        update the index with metadata of this item

        this is automatically called by item.publish_metadata() and can be used by a indexer script also.
        """
        logging.debug("item %r update index:" % (self.name, ))
        for k, v in self.items():
            logging.debug(" * item meta %r: %r" % (k, v))
        # TODO implement real index update

    def remove_index(self):
        """
        update the index, removing everything related to this item
        """
        logging.debug("item %r remove index!" % (self.name, ))
        # TODO implement real index removal


class IndexingProxyRevision(Proxy):
    """
    Proxied Revision with indexing support in the Proxy.
    """
    def __init__(self, item):
        self.__item = item

    def destroy(self):
        self.remove_index()
        s = super(self.__class__, self)
        return s.destroy()

    # TODO maybe use this class later for data indexing also,
    # TODO by intercepting write() to index data written to a revision

    def update_index(self):
        """
        update the index with metadata of this revision

        this is automatically called by item.commit() and can be used by a indexer script also.
        """
        logging.debug("item %r revno %d update index:" % (self.item.name, self.revno))
        for k, v in self.items():
            logging.debug(" * rev meta %r: %r" % (k, v))
        # TODO implement real index update

    def remove_index(self):
        """
        update the index, removing everything related to this revision
        """
        logging.debug("item %r revno %d remove index!" % (self.item.name, self.revno))
        # TODO implement real index removal

