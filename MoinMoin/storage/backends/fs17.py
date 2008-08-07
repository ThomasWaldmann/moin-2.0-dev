"""
    MoinMoin - Backend for moin 1.6/1.7 compatible filesystem data storage.

    This backend is needed because we need to be able to read existing data
    to convert them to the more powerful new backend(s).

    This backend is neither intended for nor capable of being used for production.

    TODO: support attachments via action.AttachFile

    @copyright: 2008 MoinMoin:JohannesBerg,
                2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import os
from StringIO import StringIO

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.storage import Backend, Item, StoredRevision, DELETED, \
                             EDIT_LOG_MTIME, EDIT_LOG_ACTION, EDIT_LOG_ADDR, \
                             EDIT_LOG_HOSTNAME, EDIT_LOG_USERID, EDIT_LOG_EXTRA, EDIT_LOG_COMMENT
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError


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
        return self._get_item_path(itemname, "revisions", "%08d" % (revno + 1))

    def _current_path(self, itemname):
        return self._get_item_path(itemname, "current")

    def has_item(self, itemname):
        return os.path.isfile(self._current_path(itemname))

    def iteritems(self):
        for f in os.listdir(self._path):
            itemname = wikiutil.unquoteWikiname(f)
            try:
                item = FsItem(self, itemname)
            except NoSuchItemError:
                continue
            else:
                yield item

    def get_item(self, itemname):
        return FsItem(self, itemname)

    def _get_item_metadata(self, item):
        return item._fs_meta

    def _list_revisions(self, item):
        # we report ALL revision numbers:
        # - zero-based (because the new storage api works zero based)
        # - we even included deleted revisions' revnos
        return range(item._fs_current)

    def _get_revision(self, item, revno):
        return FsRevision(item, revno)

    def _get_revision_metadata(self, rev):
        return rev._fs_meta

    def _read_revision_data(self, rev, chunksize):
        return rev._fs_data_file.read(chunksize)

    def _seek_revision_data(self, rev, position, mode):
        return rev._fs_data_file.seek(position, mode)

    def _get_revision_timestamp(self, rev):
        return rev._fs_meta['__timestamp']

    def _get_revision_size(self, rev):
        return rev._fs_meta['__size']


# Specialized Items/Revisions

class FsItem(Item):
    """ A moin 1.7 filesystem item (page) """
    def __init__(self, backend, itemname):
        Item.__init__(self, backend, itemname)
        currentpath = self._backend._current_path(itemname)
        editlogpath = self._backend._get_item_path(itemname, 'edit-log')
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
        self._fs_editlog = EditLog(editlogpath)


class FsRevision(StoredRevision):
    """ A moin 1.7 filesystem combined meta+data revision """
    def __init__(self, item, revno):
        StoredRevision.__init__(self, item, revno)
        revpath = item._backend._get_rev_path(item.name, revno)
        editlog = item._fs_editlog
        # we just read the page and parse it here, makes the rest of the code simpler:
        try:
            content = file(revpath, 'r').read()
        except (IOError, OSError):
            # handle deleted revisions (for all revnos with 0<=revno<=current) here
            meta = {DELETED: True}
            data = ''
            try:
                editlog_data = editlog.find_rev(revno)
            except KeyError:
                if 0 <= revno <= item._fs_current:
                    editlog_data = { # make something up
                        EDIT_LOG_MTIME: 0,
                        EDIT_LOG_ACTION: 'SAVE/DELETE',
                        EDIT_LOG_ADDR: '0.0.0.0',
                        EDIT_LOG_HOSTNAME: '0.0.0.0',
                        EDIT_LOG_USERID: '',
                        EDIT_LOG_EXTRA: '',
                        EDIT_LOG_COMMENT: '',
                    }
                else:
                    raise NoSuchRevisionError('Item %r has no revision %d (not even a deleted one)!' %
                            (item.name, revno))
        else:
            try:
                editlog_data = editlog.find_rev(revno)
            except KeyError:
                if 0 <= revno <= item._fs_current:
                    editlog_data = { # make something up
                        EDIT_LOG_MTIME: os.path.getmtime(revpath),
                        EDIT_LOG_ACTION: 'SAVE',
                        EDIT_LOG_ADDR: '0.0.0.0',
                        EDIT_LOG_HOSTNAME: '0.0.0.0',
                        EDIT_LOG_USERID: '',
                        EDIT_LOG_EXTRA: '',
                        EDIT_LOG_COMMENT: '',
                    }
            meta, data = wikiutil.split_body(content)
        meta.update(editlog_data)
        meta['__timestamp'] = editlog_data[EDIT_LOG_MTIME]
        meta['__size'] = 0 # not needed for converter
        self._fs_meta = meta
        self._fs_data_file = StringIO(data)


from MoinMoin.logfile import LogFile
from MoinMoin import wikiutil

class EditLog(LogFile):
    """ Access the edit-log and return metadata as the new api wants it. """
    def __init__(self, filename, buffer_size=4096):
        LogFile.__init__(self, filename, buffer_size)
        self._NUM_FIELDS = 9

    def parser(self, line):
        """ Parse edit-log line into fields """
        fields = line.strip().split('\t')
        fields = (fields + [''] * self._NUM_FIELDS)[:self._NUM_FIELDS]
        keys = (EDIT_LOG_MTIME, '__rev', EDIT_LOG_ACTION, '__pagename', EDIT_LOG_ADDR,
                EDIT_LOG_HOSTNAME, EDIT_LOG_USERID, EDIT_LOG_EXTRA, EDIT_LOG_COMMENT)
        result = dict(zip(keys, fields))
        # do some conversions/cleanups/fallbacks:
        result[EDIT_LOG_MTIME] = int(result[EDIT_LOG_MTIME] or 0) / 1000000 # convert usecs to secs
        result['__rev'] = int(result['__rev']) - 1 # old storage is 1-based, we want 0-based
        del result['__pagename']
        if not result[EDIT_LOG_HOSTNAME]:
            result[EDIT_LOG_HOSTNAME] = result[EDIT_LOG_ADDR]
        return result

    def find_rev(self, revno):
        """ Find metadata for some revno revision in the edit-log. """
        for meta in self:
            if meta['__rev'] == revno:
                break
        else:
            raise KeyError
        del meta['__rev']
        return meta

