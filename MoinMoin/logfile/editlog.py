"""
    MoinMoin edit log class

    This is used for accessing the global edit-log (e.g. by RecentChanges) as
    well as for the local edit-log (e.g. PageEditor, info action).

    @copyright: 2006 MoinMoin:ThomasWaldmann
                2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import wikiutil, user
from MoinMoin.storage.external import ItemCollection
from MoinMoin.storage.error import NoSuchItemError
from MoinMoin.Page import Page


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
        user = request.user
        if user.id:
            return user.id == self.userid
        return request.remote_addr == self.addr

    def getInterwikiEditorData(self, request):
        """ Return a tuple of type id and string or Page object
            representing the user that did the edit.

            The type id is one of 'ip' (DNS or numeric IP), 'user' (user name)
            or 'homepage' (Page instance of user's homepage).
        """
        return user.get_editor(request, self.userid, self.addr, self.hostname)

    def getEditor(self, request):
        """ Return a HTML-safe string representing the user that did the edit.
        """
        return user.get_printable_editor(request, self.userid, self.addr, self.hostname)


class LocalEditLog(object):
    """
    Used for accessing the local edit-log.
    """

    def __init__(self, request, rootpagename):
        """
        Init stuff.
        """
        self.pagename = rootpagename
        self.item = ItemCollection(request.cfg.data_backend, request)[rootpagename]
        self.pos = self.item.current

    def __iter__(self):
        """
        Iterator.
        """
        return self

    def next(self):
        """
        Returns the next edit-log entry.
        """
        if self.pos <= 0:
            raise StopIteration

        result = EditLogLine()
        result.mtime = self.item[self.pos].mtime
        result.rev = self.pos
        result.action = self.item[self.pos].action or "SAVE"
        result.pagename = self.pagename
        result.addr = self.item[self.pos].addr
        result.hostname = self.item[self.pos].hostname
        result.userid = self.item[self.pos].userid
        result.extra = self.item[self.pos].extra
        result.comment = self.item[self.pos].comment
# XXX most likely bad merge
#        if request.cfg.show_hosts:
#            title = " @ %s[%s]" % (self.hostname, self.addr)
#        else:
#            title = ""
#        kind, info = self.getInterwikiEditorData(request)
#        if kind == 'interwiki':
#            name = self._usercache[self.userid].name
#            aliasname = self._usercache[self.userid].aliasname
#            if not aliasname:
#                aliasname = name
#            title = aliasname + title
#            text = (request.formatter.interwikilink(1, title=title, generated=True, *info) +
#                    request.formatter.text(name) +
#                    request.formatter.interwikilink(0, title=title, *info))
#        elif kind == 'email':
#            name = self._usercache[self.userid].name
#            aliasname = self._usercache[self.userid].aliasname
#            if not aliasname:
#                aliasname = name
#            title = aliasname + title
#            url = 'mailto:%s' % info
#            text = (request.formatter.url(1, url, css='mailto', title=title) +
#                    request.formatter.text(name) +
#                    request.formatter.url(0))
#        elif kind == 'ip':
#            try:
#                idx = info.index('.')
#            except ValueError:
#                idx = len(info)
#            title = '???' + title
#            text = request.formatter.text(info[:idx])
#        else:
#            raise Exception("unknown EditorData type")
#        return (request.formatter.span(1, title=title) +
#                text +
#                request.formatter.span(0))
#>>>>>>> /tmp/editlog.py~other.b65oV4

        self.pos = self.pos - 1

        return result

    def add(self, request, mtime, rev, action, pagename, host, extra=u'', comment=u'', uid_override=None):
        """ Generate (and add) a line to the edit-log.

        @deprecated: drop that as fast as possible, only used by attachements.
        """
        hostname = wikiutil.get_hostname(request, host)
        user_id = request.user.valid and request.user.id or ''

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
        self.backend = request.cfg.data_backend
        self.item_collection = ItemCollection(request.cfg.data_backend, request)
        self.items = self.backend.news()
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
        if self.pos >= len(self.items):
            raise StopIteration

        mtime, rev, name = self.items[self.pos]

        result = EditLogLine()

        try:
            item = self.item_collection[name]
            result.action = item[rev].action
            result.addr = item[rev].addr
            result.hostname = item[rev].hostname
            result.userid = item[rev].userid
            result.extra = item[rev].extra
            result.comment = item[rev].comment
        except NoSuchItemError:
            result.action = ""
            result.addr = ""
            result.hostname = ""
            result.userid = ""
            result.extra = ""
            result.comment = ""

        result.mtime = mtime
        result.rev = rev
        result.pagename = name

        self.pos = self.pos + 1

        return result

    def lines(self):
        """
        Returns the number of edit-log entries.
        """
        return len(self.items)

    def date(self):
        """
        Returns the date of the newest edit-log entry.
        """
        return self.items[0][2]
