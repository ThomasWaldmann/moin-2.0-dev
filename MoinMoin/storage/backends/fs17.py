"""
    MoinMoin - Backend for moin 1.6/1.7 compatible filesystem data storage.

    This backend is needed because we need to be able to read existing data
    to convert them to the more powerful new backend(s).

    This backend is neither intended for nor capable of being used for production.

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

class FSPageBackend(Backend):
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
        path = os.path.join(self._path, 'pages', name, *args)
        return path

    def _get_rev_path(self, itemname, revno):
        """
        Returns the full path to the revision's data file.

        Revno 0 from API will get translated into "00000001" filename.
        """
        return self._get_item_path(itemname, "revisions", "%08d" % (revno + 1))

    def _get_att_path(self, itemname, attachname):
        """
        Returns the full path to the attachment file.
        """
        return self._get_item_path(itemname, "attachments", attachname.encode('utf-8'))

    def _current_path(self, itemname):
        return self._get_item_path(itemname, "current")

    def has_item(self, itemname):
        return os.path.isfile(self._current_path(itemname))

    def iteritems(self):
        pages_dir = os.path.join(self._path, 'pages')
        for f in os.listdir(pages_dir):
            itemname = wikiutil.unquoteWikiname(f)
            try:
                item = FsPageItem(self, itemname)
            except NoSuchItemError:
                continue
            else:
                yield item
                for attachitem in item.iter_attachments():
                    yield attachitem

    def get_item(self, itemname):
        try:
            # first try to get a page:
            return FsPageItem(self, itemname)
        except NoSuchItemError:
            # do a second try, interpreting it as attachment:
            return FsAttachmentItem(self, itemname)

    def search_item(self, searchterm):
        return [] # just here to not have it crash when rendering a normal page

    def _get_item_metadata(self, item):
        return item._fs_meta

    def _list_revisions(self, item):
        # we report ALL revision numbers:
        # - zero-based (because the new storage api works zero based)
        # - we even included deleted revisions' revnos
        return range(item._fs_current + 1)

    def _get_revision(self, item, revno):
        if isinstance(item, FsPageItem):
            return FsPageRevision(item, revno)
        elif isinstance(item, FsAttachmentItem):
            return FsAttachmentRevision(item, revno)
        else:
            raise

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

class FsPageItem(Item):
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

    def iter_attachments(self):
        attachmentspath = self._backend._get_item_path(self.name, 'attachments')
        for f in os.listdir(attachmentspath):
            attachname = f.decode('utf-8')
            try:
                name = '%s/%s' % (self.name, attachname)
                item = FsAttachmentItem(self._backend, name)
            except NoSuchItemError:
                continue
            else:
                yield item


class FsPageRevision(StoredRevision):
    """ A moin 1.7 filesystem item revision (page, combines meta+data) """
    def __init__(self, item, revno):
        StoredRevision.__init__(self, item, revno)
        if revno == -1: # not used by converter, but nice to try a life wiki
            revno = item._fs_current
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


class FsAttachmentItem(Item):
    """ A moin 1.7 filesystem item (attachment) """
    def __init__(self, backend, name):
        Item.__init__(self, backend, name)
        try:
            itemname, attachname = name.rsplit('/')
        except ValueError: # no '/' in there
            raise NoSuchItemError("No such attachment item, %r" % name)
        editlogpath = self._backend._get_item_path(itemname, 'edit-log')
        self._fs_current = 0 # attachments only have 1 revision with revno 0
        self._fs_meta = {} # no attachment item level metadata
        self._fs_editlog = EditLog(editlogpath)
        attachpath = self._backend._get_att_path(itemname, attachname)
        if not os.path.isfile(attachpath):
            # no attachment file means no item
            raise NoSuchItemError("No such attachment item, %r" % name)
        self._fs_attachname = attachname
        self._fs_attachpath = attachpath

class FsAttachmentRevision(StoredRevision):
    """ A moin 1.7 filesystem item revision (attachment) """
    def __init__(self, item, revno):
        if revno != 0:
            raise NoSuchRevisionError('Item %r has no revision %d (attachments just have revno 0)!' %
                    (item.name, revno))
        StoredRevision.__init__(self, item, revno)
        attpath = item._fs_attachpath
        editlog = item._fs_editlog
        try:
            editlog_data = editlog.find_attach(item._fs_attachname)
        except KeyError:
            editlog_data = { # make something up
                EDIT_LOG_MTIME: os.path.getmtime(attpath),
                EDIT_LOG_ACTION: 'ATTNEW',
                EDIT_LOG_ADDR: '0.0.0.0',
                EDIT_LOG_HOSTNAME: '0.0.0.0',
                EDIT_LOG_USERID: '',
                EDIT_LOG_EXTRA: '',
                EDIT_LOG_COMMENT: '',
            }
        meta = editlog_data
        meta['__timestamp'] = editlog_data[EDIT_LOG_MTIME]
        meta['__size'] = 0 # not needed for converter
        self._fs_meta = meta
        self._fs_data_file = file(attpath, 'rb')


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

    def find_attach(self, attachname):
        """ Find metadata for some attachment name in the edit-log. """
        for meta in self:
            if (meta['__rev'] == 99999998 and  # 99999999-1 because of 0-based
                meta[EDIT_LOG_ACTION] =='ATTNEW' and
                meta[EDIT_LOG_EXTRA] == attachname):
                break
        else:
            raise KeyError
        del meta['__rev']
        return meta


