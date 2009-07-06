# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Page class

    Page is used for read-only access to a wiki page.

    The RootPage is some virtual page located at / and is mainly used to do namespace
    operations like getting the page list.

    DEPRECATED - move stuff you need out of here, to MoinMoin.items or another
    place that makes sense.
"""

import os, re, codecs

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import config, caching, util, wikiutil, user
from MoinMoin.logfile import eventlog
from MoinMoin.storage import Backend
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, AccessDeniedError
from MoinMoin.support.python_compatibility import set
from MoinMoin.search import term

from MoinMoin.items import ACL, DELETED, MIMETYPE, SIZE, EDIT_LOG, \
                           EDIT_LOG_ACTION, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME, \
                           EDIT_LOG_USERID, EDIT_LOG_EXTRA, EDIT_LOG_COMMENT


def is_cache_exception(e):
    args = e.args
    return not (len(args) != 1 or args[0] != 'CacheNeedsUpdate')

class Page(object):
    """ Page - Manage an (immutable) page associated with a WikiName.
        To change a page's content, use the PageEditor class.
    """
    def __init__(self, request, page_name, formatter=None, **kw):
        """ Create page object.

        Note that this is a 'lean' operation, since the text for the page
        is loaded on demand. Thus, things like `Page(name).link_to()` are
        efficient.

        @param page_name: WikiName of the page
        @keyword rev: number of older revision
        @keyword formatter: mimetype str,
                            None or no kw arg will use default mimetype
        @keyword include_self: if 1, include current user (default: 0)
        """
        self.request = request
        self.cfg = request.cfg
        self.page_name = page_name
        self.rev = kw.get('rev', -1) # revision of this page
        self.include_self = kw.get('include_self', 0)

        if isinstance(formatter, basestring): # mimetype given
            mimetype = str(formatter)
        else:
            mimetype = 'text/html'

        self.output_mimetype = mimetype
        self.default_formatter = mimetype == "text/html"

        self.output_charset = config.charset # correct for wiki pages

        self._page_name_force = None
        self.hilite_re = None

        self._backend = request.storage

        self.reset()

    def reset(self, depth=0):
        """
        Reset page state.
        """
        self.__item = None
        self.__rev = None
        self._loaded = False
        self._body = None
        self._data = None
        self._meta = None
        self._pi = None
        self._body_modified = 0

        if depth == 0:
            try:
                self.request.page.reset(1)
            except AttributeError:
                pass

    def lazy_load(self):
        """
        Lazy load the page storage stuff.
        """
        if not self._loaded:
            self._loaded = True
        else:
            return

        try:
            self.__item = self._backend.get_item(self.page_name)
            self.__rev = self.__item.get_revision(self.rev)
            self._body = None
            self._meta = None
            self._data = None
        except (NoSuchItemError, AccessDeniedError):
            self.__item = None
            self.__rev = None
            self._body = u""
            self._meta = dict()
            self._data = u""
        except NoSuchRevisionError:
            self.__rev = None
            self._body = u""
            self._meta = dict()
            self._data = u""

    def set_item(self, item):
        """
        Set item method.
        """
        self.__item = item

    def get_item(self):
        """
        Get item method.
        """
        self.lazy_load()
        return self.__item

    _item = property(get_item, set_item)

    def get_rev(self):
        """
        Get rev method.
        """
        self.lazy_load()
        return self.__rev

    _rev = property(get_rev)

    # now we define some properties to lazy load some attributes on first access:

    def get_body(self):
        if self._body is None:
            if self.meta is not None and self.data is not None:
                self._body = wikiutil.add_metadata_to_body(self.meta, self.data)
        return self._body

    def set_body(self, body):
        self._body = body
        self._meta, self._data = wikiutil.split_body(body)

    body = property(fget=get_body, fset=set_body) # complete page text

    def get_meta(self):
        if self._meta is None:
            if self._rev is not None:
                self._meta = self._rev
        return self._meta
    meta = property(fget=get_meta) # processing instructions, ACLs (upper part of page text)

    def get_data(self):
        if self._data is None:
            if self._rev is not None:
                data = self._rev.read()
                data = data.decode(config.charset)
                self._data = self.decodeTextMimeType(data)
        return self._data
    data = property(fget=get_data) # content (lower part of page text)

    def get_pi(self):
        if self._pi is None:
            self._pi = self.parse_processing_instructions()
        return self._pi
    pi = property(fget=get_pi) # processed meta stuff

    def getlines(self):
        """ Return a list of all lines in body.

        @rtype: list
        @return: list of strs body_lines
        """
        return self.body.split('\n')

    def get_raw_body(self):
        """ Load the raw markup from the page file.

        @rtype: unicode
        @return: raw page contents of this page, unicode
        """
        return self.body

    def get_raw_body_str(self):
        """ Returns the raw markup from the page file, as a string.

        @rtype: str
        @return: raw page contents of this page, utf-8-encoded
        """
        return self.body.encode("utf-8")

    def set_raw_body(self, body, modified=0):
        """ Set the raw body text (prevents loading from disk).

        TODO: this should not be a public function, as Page is immutable.

        @param body: raw body text
        @param modified: 1 means that we internally modified the raw text and
            that it is not in sync with the page file on disk.  This is
            used e.g. by PageEditor when previewing the page.
        """
        self.body = body
        self._body_modified = modified

    # revision methods

    def getRevList(self):
        """
        Get a page revision list of this page, including the current version,
        sorted by revision number in descending order (current page first).

        @rtype: list of ints
        @return: page revisions
        """
        revisions = []
        if self._item is not None:
            revisions = self._item.list_revisions()
            revisions.reverse()

        return revisions

    def current_rev(self):
        """
        Return number of current revision.

        @return: int revision
        """
        if self._item is not None:
            return max(-1, -1, *self._item.list_revisions())
        return -1

    def get_real_rev(self):
        """
        Returns the real revision number of this page.
        A rev==-1 is translated to the current revision.

        @returns: revision number >= 0
        @rtype: int
        """
        if self.rev == -1:
            return self.current_rev()
        return self.rev

    def from_item(request, item, rev=-1):
        """
        TODO: Remove this method.

        Whenever you see this method used, you may want to consider refactoring its
        callers to use the storage API directly rather than using a Page object.
        """
        page = Page(request, item.name)
        page._item = item
        page.rev = rev
        return page

    from_item = staticmethod(from_item)

    def getPagePath(self, *args, **kw):
        """
        TODO: remove this

        Get full path to a page-specific storage area. `args` can
        contain additional path components that are added to the base path.

        @param args: additional path components
        @keyword check_create: if true, ensures that the path requested really exists
                               (if it doesn't, create all directories automatically).
                               (default true)
        @keyword isfile: is the last component in args a filename? (default is false)
        @rtype: string
        @return: the full path to the storage area
        """
        logging.debug("WARNING: The use of getPagePath (MoinMoin/Page.py) is DEPRECATED!")
        return "/tmp/"

    # Last Edit stuff

    def last_edit(self, printable=False):
        """
        Return the last edit.

        @param printable: whether to return the date in printable form
        @rtype: dict
        @return: timestamp and editor information
        """
        if not self.exists():
            return None

        result = {
            'timestamp': self.mtime(printable),
            'editor': self.last_editor(printable),
        }
        return result

    def last_edit_info(self):
        """
        Return the last edit info.

        @rtype: dict
        @return: timestamp and editor information
        """
        rev = self._item.get_revision(-1)
        try:
            time = rev['ed_time_usecs']
            time = wikiutil.version2timestamp(time)
            time = request.user.getFormattedDateTime(time) # Use user time format
            return {'editor': rev['editor'], 'time': time}
        except KeyError:
            return {}

    def editlog_entry(self):
        """ Return the edit-log entry for this Page object (can be an old revision).
        """
        from MoinMoin.logfile import editlog
        rev = self.get_real_rev()
        for line in editlog.LocalEditLog(self.request, rootpagename=self.page_name):
            if int(line.rev) == rev:
                break
        else:
            line = None
        return line

    def edit_info(self):
        """ Return timestamp/editor info for this Page object (can be an old revision).

            Note: if you ask about a deleted revision, it will report timestamp and editor
                  for the delete action (in the edit-log, this is just a SAVE).

        This is used by MoinMoin/xmlrpc/__init__.py.

        @rtype: dict
        @return: timestamp and editor information
        """
        line = self.editlog_entry()
        if line:
            editordata = line.getInterwikiEditorData(self.request)
            if editordata[0] == 'interwiki':
                editor = "%s:%s" % editordata[1]
            else:
                editor = editordata[1] # ip or email or anon
            result = {
                'timestamp': line.mtime,
                'editor': editor,
            }
            for a in dir(line):
                print a, getattr(line, a)
            del line
        else:
            result = None
        return result

    def last_editor(self, printable=False):
        """
        Return the last editor.

        @param printable: whether to return the date in printable form
        @rtype: string
        @return: the last editor, either printable or not.
        """
        if not printable:
            editordata = user.get_editor(self.request, self._rev[EDIT_LOG_USERID], self._rev[EDIT_LOG_ADDR], self._rev[EDIT_LOG_HOSTNAME])
            if editordata[0] == 'interwiki':
                return "%s:%s" % editordata[1]
            else:
                return editordata[1]
        else:
            try:
                return user.get_printable_editor(self.request, self._rev[EDIT_LOG_USERID], self._rev[EDIT_LOG_ADDR], self._rev[EDIT_LOG_HOSTNAME])
            except KeyError:
                logging.debug("Fix ErrorHandling in Page.py, Page.last_editor")

    def mtime(self, printable=False):
        """
        Get modification timestamp of this page.

        @param printable: whether to return the date in printable form
        @rtype: double
        @return: mtime of page (or 0 if page does not exist)
        """
        if self._rev is not None:
            timestamp = self._rev.timestamp
            if printable:
                timestamp = self.request.user.getFormattedDateTime(timestamp)
            return timestamp
        return 0

    def isUnderlayPage(self, includeDeleted=True):
        """
        Does this page live in the underlay dir?

        @param includeDeleted: include deleted pages
        @rtype: bool
        @return: true if page lives in the underlay dir
        """
        if not includeDeleted and DELETED in self._rev:
            return False
        elif not self._item:
            return False
        return hasattr(self._item._backend, '_layer_marked_underlay')

    def isStandardPage(self, includeDeleted=True):
        """
        Does this page live in the data dir?

        @param includeDeleted: include deleted pages
        @rtype: bool
        @return: true if page lives in the data dir
        """
        if not includeDeleted and DELETED in self._rev:
            return False
        elif not self._item:
            return False
        return not hasattr(self._item._backend, '_layer_marked_underlay')

    def exists(self, domain=None, includeDeleted=False):
        """
        Does this page exist?

        @param domain: where to look for the page. Default: look in all,
                       available values: 'underlay', 'standard'
        @param includeDeleted: include deleted pages?
        @rtype: bool
        @return: true if page exists otherwise false
        """
        if self._item is None or self._rev is None:
            return False

        try:
            if not includeDeleted and self._rev[DELETED]:
                return False
        except KeyError:
            pass

        if domain is None:
            return True
        elif domain == 'underlay':
            return hasattr(self._item._backend, '_layer_marked_underlay')
        else:
            return not hasattr(self._item._backend, '_layer_marked_underlay')

    def size(self, rev=-1):
        """
        Get Page size.

        @rtype: int
        @return: page size, -1 for non-existent pages.
        """
        if rev == self.rev: # same revision as self
            if self._body is not None:
                return len(self._body)

        try:
            revision = self._item.get_revision(rev)
            body = revision.read()
            return len(body)
        except NoSuchRevisionError:
            return -1

    def getACL(self):
        """
        Get ACLs of this page.

        @rtype: MoinMoin.security.AccessControlList
        @return: ACL of this page
        """
        from MoinMoin.security import AccessControlList
        # Empty ACLs are used for all cases except this case: we have an item
        # AND a item revision AND ACLs defined within that revision's metadata.
        acls = []
        if self._item is not None: # an item exists
            try:
                current_rev = self._item.get_revision(-1)
            except NoSuchRevisionError: # item has no revisions
                pass
            else:
                try:
                    acls = current_rev[ACL]
                except KeyError: # no ACLs defined on current revision
                    pass
        if not isinstance(acls, (list, tuple)):
            acls = (acls, )
        return AccessControlList(self.request.cfg, acls)

    def split_title(self, force=0):
        """ Return a string with the page name split by spaces, if the user wants that.

        @param force: if != 0, then force splitting the page_name
        @rtype: unicode
        @return: pagename of this page, splitted into space separated words
        """
        request = self.request
        if not force and not request.user.wikiname_add_spaces:
            return self.page_name

        # look for the end of words and the start of a new word,
        # and insert a space there
        splitted = config.split_regex.sub(r'\1 \2', self.page_name)
        return splitted

    def url(self, request, querystr=None, anchor=None, relative=False, **kw):
        """ Return complete URL for this page, including scriptname.
            The URL is NOT escaped, if you write it to HTML, use wikiutil.escape
            (at least if you have a querystr, to escape the & chars).

        @param request: the request object
        @param querystr: the query string to add after a "?" after the url
            (str or dict, see wikiutil.makeQueryString)
        @param anchor: if specified, make a link to this anchor
        @param relative: create a relative link (default: False), note that this
                         changed in 1.7, in 1.6, the default was True.
        @rtype: str
        @return: complete url of this page, including scriptname
        """
        assert(isinstance(anchor, (type(None), str, unicode)))
        # Create url, excluding scriptname
        url = wikiutil.quoteWikinameURL(self.page_name)
        if querystr:
            if isinstance(querystr, dict):
                action = querystr.get('action', None)
            else:
                action = None # we don't support getting the action out of a str

            querystr = wikiutil.makeQueryString(querystr)

            # make action URLs denyable by robots.txt:
            if action is not None and request.cfg.url_prefix_action is not None:
                url = "%s/%s/%s" % (request.cfg.url_prefix_action, action, url)
            url = '%s?%s' % (url, querystr)

        if not relative:
            url = '%s/%s' % (request.script_root, url)

        # Add anchor
        if anchor:
            fmt = getattr(self, 'formatter', request.html_formatter)
            if fmt:
                anchor = fmt.sanitize_to_id(anchor)
            url = "%s#%s" % (url, anchor)

        return url

    def link_to_raw(self, request, text, querystr=None, anchor=None, **kw):
        """ core functionality of link_to, without the magic """
        url = self.url(request, querystr, anchor=anchor, relative=True) # scriptName is added by link_tag
        # escaping is done by link_tag -> formatter.url -> ._open()
        link = wikiutil.link_tag(request, url, text,
                                 formatter=getattr(self, 'formatter', None), **kw)
        return link

    def link_to(self, request, text=None, querystr=None, anchor=None, **kw):
        """ Return HTML markup that links to this page.

        See wikiutil.link_tag() for possible keyword parameters.

        @param request: the request object
        @param text: inner text of the link - it gets automatically escaped
        @param querystr: the query string to add after a "?" after the url
        @param anchor: if specified, make a link to this anchor
        @keyword on: opening/closing tag only
        @keyword css_class: css class to use
        @rtype: string
        @return: formatted link
        """
        if not text:
            text = self.split_title()
        text = wikiutil.escape(text)

        # Add css class for non existing page
        if not self.exists():
            kw['css_class'] = 'nonexistent'

        link = self.link_to_raw(request, text, querystr, anchor, **kw)
        return link

    def getSubscribers(self, request, **kw):
        """ Get all subscribers of this page.

        @param request: the request object
        @keyword include_self: if 1, include current user (default: 0)
        @keyword return_users: if 1, return user instances (default: 0)
        @rtype: dict
        @return: lists of subscribed email addresses in a dict by language key
        """
        include_self = kw.get('include_self', self.include_self)
        return_users = kw.get('return_users', 0)

        # extract categories of this page
        pageList = self.getCategories(request)

        # add current page name for list matching
        pageList.append(self.page_name)

        if self.cfg.SecurityPolicy:
            UserPerms = self.cfg.SecurityPolicy
        else:
            from MoinMoin.security import Default as UserPerms

        # get email addresses of the all wiki user which have a profile stored;
        # add the address only if the user has subscribed to the page and
        # the user is not the current editor
        userlist = user.getUserList(request)
        subscriber_list = {}
        for uid in userlist:
            if uid == request.user.id and not include_self:
                continue # no self notification
            subscriber = user.User(request, uid)

            # The following tests should be ordered in order of
            # decreasing computation complexity, in particular
            # the permissions check may be expensive; see the bug
            # MoinMoinBugs/GetSubscribersPerformanceProblem

            # This is a bit wrong if return_users=1 (which implies that the caller will process
            # user attributes and may, for example choose to send an SMS)
            # So it _should_ be "not (subscriber.email and return_users)" but that breaks at the moment.
            if not subscriber.email:
                continue # skip empty email addresses

            # skip people not subscribed
            if not subscriber.isSubscribedTo(pageList):
                continue

            # skip people who can't read the page
            if not UserPerms(subscriber).read(self.page_name):
                continue

            # add the user to the list
            lang = subscriber.language or request.cfg.language_default
            if not lang in subscriber_list:
                subscriber_list[lang] = []
            if return_users:
                subscriber_list[lang].append(subscriber)
            else:
                subscriber_list[lang].append(subscriber.email)

        return subscriber_list

    def parse_processing_instructions(self):
        """ Parse page text and extract processing instructions,
            return a dict of PIs and the non-PI rest of the body.

            TODO: move this to external.py?
        """
        from MoinMoin import i18n
        request = self.request
        pi = {} # we collect the processing instructions here

        # default language from cfg
        pi['language'] = self.cfg.language_default or "en"

        body = self.body
        meta = self.meta

        # default is wiki markup
        pi['format'] = self.cfg.default_markup or "wiki"
        pi['formatargs'] = ''
        pi['lines'] = len(meta)

        for verb, args in meta.iteritems():
            if verb == "format": # markup format
                format, formatargs = (args + ' ').split(' ', 1)
                pi['format'] = format.lower()
                pi['formatargs'] = formatargs.strip()

            elif verb == "language":
                # Page language. Check if args is a known moin language
                if args in i18n.wikiLanguages():
                    pi['language'] = args

            elif verb == "refresh":
                if self.cfg.refresh:
                    try:
                        mindelay, targetallowed = self.cfg.refresh
                        args = args.split()
                        if len(args) >= 1:
                            delay = max(int(args[0]), mindelay)
                        if len(args) >= 2:
                            target = args[1]
                        else:
                            target = self.page_name
                        if '://' in target:
                            if targetallowed == 'internal':
                                raise ValueError
                            elif targetallowed == 'external':
                                url = target
                        else:
                            url = Page(request, target).url(request)
                        pi['refresh'] = (delay, url)
                    except (ValueError, ):
                        pass

            elif verb == "redirect":
                pi['redirect'] = args

            elif verb == "deprecated":
                pi['deprecated'] = True

            elif verb == "openiduser":
                if request.cfg.openid_server_enable_user:
                    pi['openid.user'] = args

            elif verb == "pragma":
                try:
                    key, val = args.split(' ', 1)
                except (ValueError, TypeError):
                    pass
                else:
                    request.setPragma(key, val)

        return pi

    def send_page(self, **keywords):
        """ Output the formatted page.

        TODO: "kill send_page(), quick" (since 2002 :)

        @keyword content_only: if 1, omit http headers, page header and footer
        @keyword content_id: set the id of the enclosing div
        @keyword count_hit: if 1, add an event to the log
        @keyword send_special: if True, this is a special page send
        @keyword omit_footnotes: if True, do not send footnotes (used by include macro)
        """
        request = self.request
        _ = request.getText
        request.clock.start('send_page')
        emit_headers = keywords.get('emit_headers', 1)
        content_only = keywords.get('content_only', 0)
        omit_footnotes = keywords.get('omit_footnotes', 0)
        content_id = keywords.get('content_id', 'content')
        do_cache = keywords.get('do_cache', 1)
        send_special = keywords.get('send_special', False)
        print_mode = keywords.get('print_mode', 0)
        if print_mode:
            media = request.values.get('media', 'print')
        else:
            media = 'screen'
        self.hilite_re = (keywords.get('hilite_re') or
                          request.values.get('highlight'))

        # count hit?
        if keywords.get('count_hit', 0):
            eventlog.EventLog(request).add(request, 'VIEWPAGE', {'pagename': self.page_name})

        # load the text
        body = self.data
        pi = self.pi

        if 'redirect' in pi and not (
            'action' in request.values or 'redirect' in request.values or content_only):
            # redirect to another page
            # note that by including "action=show", we prevent endless looping
            # (see code in "request") or any cascaded redirection
            pagename, anchor = wikiutil.split_anchor(pi['redirect'])
            redirect_url = Page(request, pagename).url(request,
                                                       querystr={'action': 'show', 'redirect': self.page_name, },
                                                       anchor=anchor)
            request.http_redirect(redirect_url)
            return

        if 'deprecated' in pi:
            # deprecated page, append last backup version to current contents
            # (which should be a short reason why the page is deprecated)
            request.theme.add_msg(_('The backed up content of this page is deprecated and will not be included in search results!'), "warning")

            revisions = self.getRevList()
            if len(revisions) >= 2: # XXX shouldn't that be ever the case!? Looks like not.
                oldpage = Page(request, self.page_name, rev=revisions[1])
                body += oldpage.get_raw_body()
                del oldpage

        lang = self.pi.get('language', request.cfg.language_default)
        request.setContentLanguage(lang)

        # start document output
        page_exists = self.exists()
        if not content_only:
            if emit_headers:
                request.content_type = "%s; charset=%s" % (self.output_mimetype, self.output_charset)
                if page_exists:
                    if not request.user.may.read(self.page_name):
                        request.status_code = 403
                    else:
                        request.status_code = 200
                    if not request.cacheable:
                        # use "nocache" headers if we're using a method that is not simply "display"
                        request.disableHttpCaching(level=2)
                    elif request.user.valid:
                        # use nocache headers if a user is logged in (which triggers personalisation features)
                        request.disableHttpCaching(level=1)
                    else:
                        # TODO: we need to know if a page generates dynamic content -
                        # if it does, we must not use the page file mtime as last modified value
                        # The following code is commented because it is incorrect for dynamic pages:
                        #lastmod = self.mtime()
                        #request.setHttpHeader("Last-Modified: %s" % util.timefuncs.formathttpdate(lastmod))
                        pass
                else:
                    request.status_code = 404

            if not page_exists and self.request.isSpiderAgent:
                # don't send any 404 content to bots
                return

            # TODO: request.write(self.formatter.startDocument(self.page_name))

            # send the page header
            if self.default_formatter:
                if self.rev != -1:
                    request.theme.add_msg("<strong>%s</strong><br>" % (
                        _('Revision %(rev)d as of %(date)s') % {
                            'rev': self.rev,
                            'date': self.mtime(printable=True)
                        }), "info")

                # This redirect message is very annoying.
                # Less annoying now without the warning sign.
                if 'redirect' in request.values:
                    redir = request.values['redirect']
                    request.theme.add_msg('<strong>%s</strong><br>' % (
                        _('Redirected from page "%(page)s"') % {'page':
                            wikiutil.link_tag(request, wikiutil.quoteWikinameURL(redir) + "?action=show", redir)}), "info")
                if 'redirect' in pi:
                    request.theme.add_msg('<strong>%s</strong><br>' % (
                        _('This page redirects to page "%(page)s"') % {'page': wikiutil.escape(pi['redirect'])}), "info")

                # Page trail
                trail = None
                if not print_mode:
                    request.user.addTrail(self)
                    trail = request.user.getTrail()

                title = self.split_title()

                html_head = ''
                if request.cfg.openid_server_enabled:
                    openid_username = self.page_name
                    userid = user.getUserId(request, openid_username)

                    if userid is None and 'openid.user' in self.pi:
                        openid_username = self.pi['openid.user']
                        userid = user.getUserId(request, openid_username)

                    if request.cfg.openid_server_restricted_users_group:
                        request.dicts.addgroup(request,
                                               request.cfg.openid_server_restricted_users_group)

                    if userid is not None and not request.cfg.openid_server_restricted_users_group or \
                      request.dicts.has_member(request.cfg.openid_server_restricted_users_group, openid_username):
                        html_head = '<link rel="openid2.provider" href="%s">' % \
                                        wikiutil.escape(request.getQualifiedURL(self.url(request,
                                                                                querystr={'action': 'serveopenid'})), True)
                        html_head += '<link rel="openid.server" href="%s">' % \
                                        wikiutil.escape(request.getQualifiedURL(self.url(request,
                                                                                querystr={'action': 'serveopenid'})), True)
                        html_head += '<meta http-equiv="x-xrds-location" content="%s">' % \
                                        wikiutil.escape(request.getQualifiedURL(self.url(request,
                                                                                querystr={'action': 'serveopenid', 'yadis': 'ep'})), True)
                    elif self.page_name == request.cfg.page_front_page:
                        html_head = '<meta http-equiv="x-xrds-location" content="%s">' % \
                                        wikiutil.escape(request.getQualifiedURL(self.url(request,
                                                                                querystr={'action': 'serveopenid', 'yadis': 'idp'})), True)

                request.theme.send_title(title, page=self,
                                    print_mode=print_mode,
                                    media=media, pi_refresh=pi.get('refresh'),
                                    allow_doubleclick=1, trail=trail,
                                    html_head=html_head,
                                    )

        # special pages handling, including denying access
        special = None

        if not send_special:
            if not page_exists and not body:
                special = 'missing'
            elif not request.user.may.read(self.page_name):
                special = 'denied'

            # if we have a special page, output it, unless
            #  - we should only output content (this is for say the pagelinks formatter)
            #  - we have a non-default formatter
            if special and not content_only and self.default_formatter:
                self._specialPageText(request, special) # this recursively calls send_page

        # if we didn't short-cut to a special page, output this page
        if not special:
            # parse the text and send the page content
            self.send_page_content(request, body,
                                   format=pi['format'],
                                   format_args=pi['formatargs'],
                                   do_cache=do_cache,
                                   start_line=pi['lines'])

        # end document output
        if not content_only:
            # send the page footer
            if self.default_formatter:
                request.theme.send_footer(self.page_name, print_mode=print_mode)

            # TODO: request.write(self.formatter.endDocument())

        request.clock.stop('send_page')
        if not content_only and self.default_formatter:
            request.theme.send_closing_html()

    def getFormatterName(self):
        """ Return a formatter name as used in the caching system

        @rtype: string
        @return: formatter name as used in caching
        """
        if not hasattr(self, 'formatter') or self.formatter is None:
            return ''
        module = self.formatter.__module__
        return module[module.rfind('.') + 1:]

    def canUseCache(self, parser=None):
        """ Is caching available for this request?

        This make sure we can try to use the caching system for this
        request, but it does not make sure that this will
        succeed. Themes can use this to decide if a Refresh action
        should be displayed.

        @param parser: the parser used to render the page
        @rtype: bool
        @return: if this page can use caching
        """
        return not self.rev and not self.__body_modified

    def send_page_content(self, request, body, format='wiki', format_args='', do_cache=1, **kw):
        """ Output the formatted wiki page, using caching if possible

        @param request: the request object
        @param body: text of the wiki page
        @param format: format of content, default 'wiki'
        @param format_args: #format arguments, used by some parsers
        @param do_cache: if True, use cached content
        """
        request.clock.start('send_page_content')

        from cStringIO import StringIO
        from emeraldtree import ElementTree as ET
        from MoinMoin.converter2 import default_registry as reg
        from MoinMoin.util.tree import html

        IncludeConverter = reg.get(request, 'application/x-moin-document',
                'application/x-moin-document;includes=expandall')
        MacroConverter = reg.get(request, 'application/x-moin-document',
                'application/x-moin-document;macros=expandall')
        LinkConverter = reg.get(request, 'application/x-moin-document',
                'application/x-moin-document;links=extern')
        # TODO: Real output format
        HtmlConverter = reg.get(request, 'application/x-moin-document',
                'application/x-xhtml-moin-page')

        doc = None
        if do_cache and self.canUseCache():
            doc = self.convert_input_cache(request, body, format, format_args)
        else:
            doc = self.convert_input(request, body, format, format_args)

        doc = IncludeConverter(request)(doc)
        doc = MacroConverter(request)(doc)
        doc = LinkConverter(request)(doc)
        doc = HtmlConverter(request)(doc)

        out = StringIO()
        tree = ET.ElementTree(doc)
        # TODO: Switch to xml
        tree.write(out, encoding=self.output_charset,
                default_namespace=html, method='html')
        self.request.write(out.getvalue())

        request.clock.stop('send_page_content')

    def convert_input(self, request, body=None, format=None, format_args='',
            create_pagelinks=False):
        if body is None:
            body = self.data
        if not format:
            format = self.pi.get('format', 'wiki')

        mime_type = wikiutil.MimeType(format).mime_type()

        from emeraldtree import ElementTree as ET
        from MoinMoin.converter2 import default_registry as reg
        from MoinMoin.util import iri

        InputConverter = reg.get(request, mime_type, 'application/x-moin-document')

        i = iri.Iri(scheme='wiki', authority='', path='/' + self.page_name)

        doc = InputConverter(request, i)(body.split('\n'))

        if create_pagelinks:
            PagelinksConverter = reg.get(request, 'application/x-moin-document',
                    'application/x-moin-document;links=pagelinks')
            pagelinks = PagelinksConverter(request)(doc)

            return doc, pagelinks

        return doc

    def convert_input_cache_create(self, request, body=None, format=None,
            format_args=''):
        """
        Create the document and write it to the cache.
        """
        data = self.convert_input(request, body, format, format_args,
                create_pagelinks=True)
        self.add_to_cache(request, 'tree', data[0])
        self.add_to_cache(request, 'pagelinks', data[1])

        return data

    def convert_input_cache(self, request, body=None, format=None, format_args=''):
        """
        Loads document from cache if possible, otherwise create it.
        """
        data = self.load_from_cache(request, 'tree')

        if data is None:
            data = self.convert_input_cache_create(request, body, format,
                    format_args)
            return data[0]

        return data

    def convert_input_cache_pagelinks(self, request):
        """
        Loads document from cache if possible, otherwise create it.
        All exceptions by the converters are swallowed and an empty set
        returned and cached instead.
        """
        data = self.load_from_cache(request, 'pagelinks')

        if data is None:
            try:
                data = self.convert_input_cache_create(request)[1]
            except Exception:
                data = set()
                self.add_to_cache(request, 'pagelinks', data)

    def load_from_cache(self, request, name):
        """ Return page content cache or None """
        cache = caching.CacheEntry(request, self, name, scope='item', use_pickle=True)
        attachmentsPath = self.getPagePath('attachments', check_create=0)
        if cache.needsUpdate(self._text_filename(), attachmentsPath):
            return

        try:
            return cache.content()
        except (EOFError, ValueError, TypeError):
            return
        except Exception, err:
            logging.info('failed to load "%s" cache: %s' %
                        (self.page_name, str(err)))
            return

    def add_to_cache(self, request, name, data):
        cache = caching.CacheEntry(request, self, name, scope='item', use_pickle=True)
        cache.update(data)

    def _specialPageText(self, request, special_type):
        """ Output the default page content for new pages.

        @param request: the request object
        """
        _ = request.getText

        if special_type == 'missing':
            if request.user.valid and request.user.name == self.page_name and \
               request.cfg.user_homewiki in ('Self', request.cfg.interwikiname):
                page = wikiutil.getLocalizedPage(request, 'MissingHomePage')
            else:
                page = wikiutil.getLocalizedPage(request, 'MissingPage')

            alternative_text = u"'''<<Action(action=edit, text=\"%s\")>>'''" % _('Create New Page')
        elif special_type == 'denied':
            page = wikiutil.getLocalizedPage(request, 'PermissionDeniedPage')
            alternative_text = u"'''%s'''" % _('You are not allowed to view this page.')
        else:
            assert False

        special_exists = page.exists()

        if special_exists:
            page.lazy_load()
        else:
            page.body = alternative_text
            logging.warn('The page "%s" could not be found. Check your'
                         ' underlay directory setting.' % page.page_name)

        page._page_name_force = page.page_name
        page.page_name = self.page_name

        page.send_page(content_only=True, do_cache=not special_exists, send_special=True)


    def getPageText(self, start=0, length=None):
        """ Convenience function to get the page text, skipping the header

        @rtype: unicode
        @return: page text, excluding the header
        """
        if length is None:
            return self.data[start:]
        else:
            return self.data[start:start+length]

    def getPageHeader(self, start=0, length=None):
        """ Convenience function to get the page header

        @rtype: unicode
        @return: page header
        """
        header = ['#%s %s' % t for t in self.meta.iteritems()]
        header = '\n'.join(header)
        if header:
            if length is None:
                return header[start:]
            else:
                return header[start:start+length]
        return ''

    def getPageLinks(self, request):
        """ Get a list of the links on this page.

        @param request: the request object
        @rtype: list
        @return: page names this page links to
        """
        if self.exists():
            return self.convert_input_cache_pagelinks(request)
        return ()

    def getCategories(self, request):
        """ Get categories this page belongs to.

        @param request: the request object
        @rtype: list
        @return: categories this page belongs to
        """
        return wikiutil.filterCategoryPages(request, self.getPageLinks(request))

    def getParentPage(self):
        """ Return parent page or None

        @rtype: Page
        @return: parent page or None
        """
        if self.page_name:
            pos = self.page_name.rfind('/')
            if pos > 0:
                parent = Page(self.request, self.page_name[:pos])
                if parent.exists():
                    return parent
        return None

    # Text format -------------------------------------------------------

    def encodeTextMimeType(self, text):
        """ Encode text from moin internal representation to text/* mime type

        Make sure text uses CRLF line ends, keep trailing newline.

        @param text: text to encode (unicode)
        @rtype: unicode
        @return: encoded text
        """
        if text:
            lines = text.splitlines()
            # Keep trailing newline
            if text.endswith(u'\n') and not lines[-1] == u'':
                lines.append(u'')
            text = u'\r\n'.join(lines)
        return text

    def decodeTextMimeType(self, text):
        """ Decode text from text/* mime type to moin internal representation

        @param text: text to decode (unicode). Text must use CRLF!
        @rtype: unicode
        @return: text using internal representation
        """
        text = text.replace(u'\r', u'')
        return text

    def isConflict(self):
        """ Returns true if there is a known editing conflict for that page.

        @return: true if there is a known conflict.
        """

        cache = caching.CacheEntry(self.request, self, 'conflict', scope='item')
        return cache.exists()

    def setConflict(self, state):
        """ Sets the editing conflict flag.

        @param state: bool, true if there is a conflict.
        """
        cache = caching.CacheEntry(self.request, self, 'conflict', scope='item')
        if state:
            cache.update("") # touch it!
        else:
            cache.remove()


# compatibility hack until we refactored all code using it from here:
from MoinMoin.items import Item

class RootPage(Item):
    supported_mimetypes = []

    def __init__(self, request):
        Item.__init__(self, request, name=u'')

    def getPageList(self, user=None, exists=1, filter=None, include_underlay=True, return_objects=False):
        """
        List user readable pages under current page.

        Currently only request.rootpage is used to list pages, but if we
        have true sub pages, any page can list its sub pages.

        The default behavior is listing all the pages readable by the
        current user. If you want to get a page list for another user,
        specify the user name.

        If you want to get the full page list, without user filtering,
        call with user="". Use this only if really needed, and do not
        display pages the user can not read.

        filter is usually compiled re match or search method, but can be
        any method that get a unicode argument and return bool. If you
        want to filter the page list, do it with this filter function,
        and NOT on the output of this function.

        @param user: the user requesting the pages (MoinMoin.user.User)
        @param filter: filter function
        @param exists: filter existing pages
        @param return_objects: lets it return a list of Page objects instead of
                               names
        @rtype: list of unicode strings
        @return: user readable wiki page names
        """
        # XXX: better update this docstring

        request = self.request
        if user is None:
            user = request.user

        search_term = term.AND()
        if not include_underlay:
            search_term.add(term.FromUnderlay())

        if filter:
            search_term.add(term.NameFn(filter))

        items = self.list_items(search_term, include_deleted=not exists)

        if user or return_objects:
            for item in items:
                # XXX ACL check when user given?
                if return_objects:
                    page = Page.from_item(request, item)
                    yield page
                else:
                    yield item.name
        else:
            for item in items:
                yield item.name

