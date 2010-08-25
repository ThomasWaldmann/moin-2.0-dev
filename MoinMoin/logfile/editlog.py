"""
    MoinMoin edit log class

    This is used for accessing the global edit-log (e.g. by RecentChanges) as
    well as for the local edit-log (e.g. info action).

    @copyright: 2006 MoinMoin:ThomasWaldmann
                2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import log
logging = log.getLogger(__name__)

from flask import current_app as app

from flask import flaskg

from MoinMoin import wikiutil, user
from MoinMoin.storage.error import NoSuchItemError
from MoinMoin.Page import Page
from MoinMoin.items import EDIT_LOG_ACTION, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME, \
                           EDIT_LOG_USERID, EDIT_LOG_EXTRA, EDIT_LOG_COMMENT

class EditLogLine(object):
    """
    Has the following attributes

    mtime
    rev
    action
    pagename
    addr
    hostname
    userid
    extra
    comment
    """

    def __cmp__(self, other):
        try:
            return cmp(self.mtime, other.mtime)
        except AttributeError:
            return cmp(self.mtime, other)

    def is_from_current_user(self, request):
        user = flaskg.user
        if user.id:
            return user.id == self.userid
        return request.remote_addr == self.addr

    def getInterwikiEditorData(self, request):
        """ Return a tuple of type id and string or Page object
            representing the user that did the edit.

            The type id is one of 'ip' (DNS or numeric IP), 'user' (user name)
            or 'homepage' (Page instance of user's homepage) or 'anon' ('').
        """
        return user.get_editor(request, self.userid, self.addr, self.hostname)


class LocalEditLog(object):
    """
    Used for accessing the local edit-log.
    """

    def __init__(self, request, rootpagename):
        """
        Init stuff.
        """
        self.pagename = rootpagename
        self._iter = self.item.keys().__iter__()

    def __iter__(self):
        """
        Iterator.
        """
        return self

    def next(self):
        """
        Returns the next edit-log entry.
        """
        revno = self._iter.next()

        result = EditLogLine()
        result.mtime = self.item[revno].mtime
        result.rev = revno
        result.action = self.item[revno].action or "SAVE"
        result.pagename = self.pagename
        result.addr = self.item[revno].addr
        result.hostname = self.item[revno].hostname
        result.userid = self.item[revno].userid
        result.extra = self.item[revno].extra
        result.comment = self.item[revno].comment

        return result

    def add(self, request, mtime, rev, action, pagename, host, extra=u'', comment=u'', uid_override=None):
        """ Generate (and add) a line to the edit-log.

        @deprecated: drop that as fast as possible, only used by attachements.
        """
        if app.cfg.log_remote_addr:
            if host is None:
                host = request.remote_addr
            hostname = wikiutil.get_hostname(request, host)
        else:
            host = ''
            hostname = ''

        comment = wikiutil.clean_input(comment)
        user_id = flaskg.user.valid and flaskg.user.id or ''

        mtime = wikiutil.timestamp2version(mtime)

        if uid_override is not None:
            user_id = ''
            hostname = uid_override
            host = ''

        line = u"\t".join((str(mtime),
                           "%08d" % rev,
                           action,
                           wikiutil.quoteWikinameFS(pagename),
                           host,
                           hostname,
                           user_id,
                           extra,
                           comment,
                           )) + "\n"

        if self.pagename:
            filename = Page(request, pagename).getPagePath('edit-log', isfile=1)
        else:
            filename = request.rootpage.getPagePath('edit-log', isfile=1)

        log_file = open(filename, "a")
        log_file.write(line)
        log_file.close()


class GlobalEditLog(object):
    """
    Used for accessing the global edit-log.
    """

    def __init__(self, request):
        """
        Init stuff.
        """
        self.request = request
        self.backend = request.storage
        self.items = self.backend.history()
        self.pos = 0

    def __iter__(self):
        """
        Iterator.
        """
        return self

    def next(self):
        """
        Returns the next edit-log entry.
        """
        rev = self.items.next()

        result = EditLogLine()

        result.action = rev.get(EDIT_LOG_ACTION, '')
        result.addr = rev.get(EDIT_LOG_ADDR, '')
        result.hostname = rev.get(EDIT_LOG_HOSTNAME, '')
        result.userid = rev.get(EDIT_LOG_USERID, '')
        result.extra = rev.get(EDIT_LOG_EXTRA, '')
        result.comment = rev.get(EDIT_LOG_COMMENT, '')

        result.mtime = rev.timestamp
        result.rev = rev.revno
        result.revision = rev
        result.pagename = rev.item.name

        self.pos = self.pos + 1

        return result

    def lines(self):
        """
        Returns the number of edit-log entries.
        """
        return len(list(self.items))

    def date(self):
        """
        Returns the date of the newest edit-log entry.
        """
        return self.items[0][2]
