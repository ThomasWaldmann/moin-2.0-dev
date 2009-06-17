"""
    MoinMoin - flat file backend

    This backend is not useful for a wiki that you actually keep online.
    Instead, it is intended to be used for MoinMoin internally to keep
    the documentation that is part of the source tree editable via the
    wiki server locally.

    This backend stores no item metadata and no old revisions, as such
    you cannot use it safely for a wiki. Inside the MoinMoin source tree,
    however, the wiki content is additionally kept under source control,
    therefore this backend is actually useful to edit documentation that
    is part of MoinMoin.

    The backend _does_ store some revision metadata, namely that which
    used to traditionally be part of the page header.

    @copyright: 2008 MoinMoin:JohannesBerg,
                2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import os, re
from cStringIO import StringIO

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.storage import Backend, Item, StoredRevision, NewRevision
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, \
                                   ItemAlreadyExistsError, \
                                   RevisionAlreadyExistsError
from MoinMoin.wikiutil import add_metadata_to_body, split_body, quoteWikinameFS, unquoteWikiname
from MoinMoin.items import MIMETYPE, EDIT_LOG, EDIT_LOG_ACTION

class FlatFileBackend(Backend):
    def __init__(self, path):
        """
        Initialise filesystem backend, creating initial files and some internal structures.

        @param path: storage path
        """
        self._path = path

    def _quote(self, name):
        return quoteWikinameFS(name)

    def _unquote(self, name):
        return unquoteWikiname(name)

    def _rev_path(self, name):
        return os.path.join(self._path, self._quote(name))

    def _exists(self, name):
        revpath = self._rev_path(name)
        return os.path.exists(revpath)

    def history(self, reverse=True):
        rev_list = [i.get_revision(-1) for i in self.iteritems()]
        rev_list.sort(lambda x, y: cmp(x.timestamp, y.timestamp))
        if reverse:
            rev_list.reverse()
        return iter(rev_list)

    def get_item(self, itemname):
        if not self._exists(itemname):
            raise NoSuchItemError("No such item, %r" % (itemname))
        return Item(self, itemname)

    def has_item(self, itemname):
        return self._exists(itemname)

    def create_item(self, itemname):
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Item names must have string type, not %s" % (type(itemname)))
        elif self.has_item(itemname):
            raise ItemAlreadyExistsError("An Item with the name %r already exists!" % (itemname))
        return Item(self, itemname)

    def iteritems(self):
        filenames = os.listdir(self._path)
        for filename in filenames:
            yield Item(self, self._unquote(filename))

    def _get_revision(self, item, revno):
        if revno > 0:
            raise NoSuchRevisionError("No Revision #%d on Item %s" % (revno, item.name))

        revpath = self._rev_path(item.name)
        if not os.path.exists(revpath):
            raise NoSuchRevisionError("No Revision #%d on Item %s" % (revno, item.name))

        rev = StoredRevision(item, 0)
        data = open(revpath, 'rb').read()
        rev._metadata, data = split_body(data)
        # XXX: HACK!!!
        for e in EDIT_LOG:
            rev._metadata[e] = ''
        rev._metadata[EDIT_LOG_ACTION] = 'SAVE'
        rev._metadata[MIMETYPE] = 'text/moin-wiki' # XXX get this from PI
        rev._data = StringIO(data)
        rev._data_size = len(data)
        return rev

    def _list_revisions(self, item):
        if self._exists(item.name):
            return [0]
        else:
            return []

    def _create_revision(self, item, revno):
        assert revno <= 1
        rev = NewRevision(item, 0)
        rev._data = StringIO()
        return rev

    def _rename_item(self, item, newname):
        try:
            os.rename(self._rev_path(item.name), self._rev_path(newname))
        except OSError:
            raise ItemAlreadyExistsError('')

    def _commit_item(self, rev):
        revpath = self._rev_path(rev.item.name)
        f = open(revpath, 'wb')
        rev._data.seek(0)
        data = rev._data.read()
        data = add_metadata_to_body(rev, data)
        f.write(data)
        f.close()

    def _rollback_item(self, rev):
        pass

    def _change_item_metadata(self, item):
        pass

    def _publish_item_metadata(self, item):
        pass

    def _read_revision_data(self, rev, chunksize):
        return rev._data.read(chunksize)

    def _write_revision_data(self, rev, data):
        rev._data.write(data)

    def _get_item_metadata(self, item):
        return {}

    def _get_revision_timestamp(self, rev):
        revpath = self._rev_path(rev.item.name)
        return os.stat(revpath).st_ctime

    def _get_revision_size(self, rev):
        return rev._data_size

    def _seek_revision_data(self, rev, position, mode):
        rev._data.seek(position, mode)

