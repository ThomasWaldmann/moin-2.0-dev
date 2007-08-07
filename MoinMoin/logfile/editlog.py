"""
    MoinMoin edit log class

    This is used for accessing the global edit-log (e.g. by RecentChanges) as
    well as for the local edit-log (e.g. PageEditor, info action).

    @copyright: 2006 MoinMoin:ThomasWaldmann
                2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""


from MoinMoin import wikiutil, user
from MoinMoin.logfile import LogFile
from MoinMoin.storage.external import ItemCollection
from MoinMoin.Page import Page


class EditLogLine(object):
    """
    Has the following attributes

    ed_time_usecs
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
            return cmp(self.ed_time_usecs, other.ed_time_usecs)
        except AttributeError:
            return cmp(self.ed_time_usecs, other)

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
        result = EditLogLine()
        result.ed_time_usecs = self.item[self.pos].mtime
        result.rev = self.pos
        result.action = self.item[self.pos].action
        result.pagename = self.pagename
        result.addr = self.item[self.pos].addr
        result.hostname = self.item[self.pos].hostname
        result.userid = self.item[self.pos].userid
        result.extra = self.item[self.pos].extra
        result.comment = self.item[self.pos].comment

        if self.pos == 1:
            raise StopIteration
        else:
            self.pos = self.pos - 1

        return result

    def add(self, request, mtime, rev, action, pagename, host, extra=u'', comment=u''):
        """ Generate (and add) a line to the edit-log.

        TODO: drop that as fast as possible, only used by attachements.
        """
        hostname = wikiutil.get_hostname(request, host)
        user_id = request.user.valid and request.user.id or ''

        if hasattr(request, "uid_override"):
            user_id = ''
            hostname = request.uid_override
            host = ''

        line = u"\t".join((str(long(mtime)), # has to be long for py 2.2.x
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


class GlobalEditLog(LogFile):
    """
    Used for accessing the global edit-log.
    """
    def __init__(self, request):
        filename = request.rootpage.getPagePath('edit-log', isfile=1)
        LogFile.__init__(self, filename, 4096)
        self._NUM_FIELDS = 9

    def parser(self, line):
        """ Parse edit-log line into fields """
        fields = line.strip().split('\t')
        # Pad empty fields
        missing = self._NUM_FIELDS - len(fields)
        if missing:
            fields.extend([''] * missing)
        result = EditLogLine()
        (result.ed_time_usecs, result.rev, result.action,
         result.pagename, result.addr, result.hostname, result.userid,
         result.extra, result.comment, ) = fields[:self._NUM_FIELDS]
        if not result.hostname:
            result.hostname = result.addr
        result.pagename = wikiutil.unquoteWikiname(result.pagename.encode('ascii'))
        result.ed_time_usecs = long(result.ed_time_usecs or '0') # has to be long for py 2.2.x
        return result

    def news(self, time):
        """
        TODO: implement that.
        """
        pass

