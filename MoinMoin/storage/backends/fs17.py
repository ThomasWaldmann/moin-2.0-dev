"""
    MoinMoin - Backend for moin 1.6/1.7 compatible filesystem data storage.
    
    This backend is needed because we need to be able to read existing data
    to convert them to the more powerful new backend(s).
    
    This backend is neither intended for nor capable of being used for production.

    XXX currently the code here is rather pseudo-code than executable one.

    @copyright: 2008 MoinMoin:JohannesBerg,
                2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import os

from MoinMoin.storage import Backend, Item, StoredRevision
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError


class FsItem(Item):
    def __init__(self, itemname, currentpath):
        Item.__init__(self, itemname)
        self._fs_meta = {} # 'current' is the only page metadata and handled elsewhere
        try:
            current = int(open(currentpath, 'r').read().strip()) - 1 # new api is 0-based, old is 1-based
        except (OSError, IOError):
            # no current file means no item
            raise NoSuchItemError("No such item, %r" % itemname)
        except ValueError:
            # we have a current file, but its content is damaged
            raise # TODO: current = determine_current(revdir, editlog)
        self._fs_current = current


class FsRevision(StoredRevision):
    def __init__(self, item, revno, revpath=None):
        StoredRevision.__init__(self, item, revno)
        # we just read the page and parse it here, makes the rest of the code simpler:
        try:
            meta, data = read_split(revpath) # TODO
        except RevisionDataFileNotFound: # XXX fix exception
            # handle deleted revisions (for all revnos with 0<=revno<=current) here
            meta = {deleted: True} # XXX fix key
            data = ''
            try:
                editlog_data = find_in_editlog(revno) # TODO
            except NoEditLogEntry:
                if 0 <= revno <= item._fs_current:
                    # if such a revision file is not there, it means that the revision was deleted
                    editlog_data = ... # XXX make something up
                else:
                    raise NoSuchRevisionError('Item %r has no revision %d (not even a deleted one)!' %
                            (item.name, revno))
        else:
            editlog_data = get them out of edit-log # XXX
        meta.update(With editlog_data) # XXX
        self._fs_metadata['__timestamp'] = editlog_data['edit_mtime'] # XXX fix index
        self._fs_metadata['__size'] = 0 # not needed for converter
        self._fs_meta = meta
        self._fs_data_file = StringIO(data)



class FSBackend(Backend):
    """
    MoinMoin 1.7 compatible, read-only, "just for the migration" filesystem backend.

    Everything not needed for the migration will likely just raise a NotImplementedError.
    """
    def __init__(self, path):
        """
        Initialise filesystem backend.

        @param path: storage path (data_dir)
        """
        self._path = path

    def _get_item_path(self, name, *args):
        """
        Returns the full path to the page directory.
        """
        name = wikiutil.quoteWikinameFS(name)
        return os.path.join(self._path, name, *args)

    def _get_rev_path(self, itemname, revno):
        """
        Returns the full path to the revision's data file.

        Revno 0 from API will get translated into "00000001" filename.
        """
        return self._get_item_path(itemname, "revisions", "%08d" % (revno+1))

    def _current_path(self, itemname):
        return self._get_item_path(itemname, "current")

    def has_item(self, itemname):
        return os.path.isfile(self._current_path(itemname))

    def iteritems(self):
        for f in os.listdir(self._path):
            itemname = wikiutil.unquoteWikiname(f)
            try:
                item = FsItem(self, itemname, currentpath=self._current_path(itemname))
            except NoSuchItemError:
                continue
            else:
                yield item

    def get_item(self, itemname):
        return FsItem(self, itemname, currentpath=self._current_path(itemname))

    def _get_item_metadata(self, item):
        return item._fs_meta

    def _list_revisions(self, item):
        # we report ALL revision numbers:
        # - zero-based (because the new storage api works zero based)
        # - we even included deleted revisions' revnos
        return range(item._fs_current)

    def _get_revision(self, item, revno):
        return FsRevision(item, revno, revpath=self._get_rev_path(item.name, revno))

    def _get_revision_metadata(self, rev):
        return rev._fs_meta

    def _read_revision_data(self, rev, chunksize):
        if chunksize < 0: # XXX is that needed, can't we just use read(chunksize) with chunksize < 0?
            return rev._fs_data_file.read()
        return rev._fs_data_file.read(chunksize)

    def _seek_revision_data(self, rev, position, mode):
        return rev._fs_data_file.seek(position, mode)

    def _get_revision_timestamp(self, rev):
        return rev._fs_metadata['__timestamp']

    def _get_revision_size(self, rev):
        return rev._fs_metadata['__size']

