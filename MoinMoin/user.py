# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - User Accounts

    This module contains functions to access user accounts (list all users, get
    some specific user). User instances are used to access the user profile of
    some specific user (name, password, email, bookmark, trail, settings, ...).

    Some related code is in the userform and userprefs modules.

    @copyright: 2000-2004 Juergen Hermann <jh@web.de>,
                2003-2007 MoinMoin:ThomasWaldmann
                2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

# add names here to hide them in the cgitb traceback
unsafe_names = ("id", "key", "val", "user_data", "enc_password", "recoverpass_key")

import os, time, sha, codecs, hmac

from MoinMoin import config, caching, wikiutil, i18n, events
from MoinMoin.util import timefuncs, filesys, random_string
from MoinMoin.util import timefuncs
from MoinMoin.storage.external import ItemCollection
from MoinMoin.search import term
from MoinMoin.wikiutil import url_quote_plus


def getUserList(request):
    """ Get a list of all (numerical) user IDs.

    @param request: current request
    @rtype: list
    @return: all user IDs
    """
    return ItemCollection(request.cfg.user_backend, request).keys()


def get_by_filter(request, key, value):
    """ Searches for an user with a given filter """
    filter = term.MetaDataMatch(key, value)
    identifier = ItemCollection(request.cfg.user_backend, request).iterate(filter)
    users = []
    for user in identifier:
        users.append(User(request, user))
    return users


def get_by_email_address(request, email_address):
    """ Searches for an user with a particular e-mail address and returns it. """
    users = get_by_filter(request, 'email', email_address)
    if len(users) > 0:
        return users[0]


def get_by_jabber_id(request, jabber_id):
    """ Searches for an user with a perticular jabber id and returns it. """
    users = get_by_filter(request, 'jid', jabber_id)
    if len(users) > 0:
        return users[0]


def getUserIdByOpenId(request, openid):
    """ Searches for an user with a particular openid id and returns it. """
    filter = term.HasMetaDataValue('openids', openid)
    identifier = ItemCollection(request.cfg.user_backend, request).iterate(filter)
    users = []
    for user in identifier:
        users.append(User(request, user))
    return users


def getUserId(request, searchName):
    """ Get the user ID for a specific user NAME.

    @param searchName: the user name to look up
    @rtype: string
    @return: the corresponding user ID or None
    """
    try:
        coll = ItemCollection(request.cfg.user_backend, request)
        for user in coll.iterate(term.MetaDataMatch('name', searchName)):
            return user
        return None
    except IndexError:
        return None


def getUserIdentification(request, username=None):
    """ Return user name or IP or '<unknown>' indicator.

    @param request: the request object
    @param username: (optional) user name
    @rtype: string
    @return: user name or IP or unknown indicator
    """
    _ = request.getText

    if username is None:
        username = request.user.name

    return username or (request.cfg.show_hosts and request.remote_addr) or _("<unknown>")


def get_editor(request, userid, addr, hostname):
    """ Return a tuple of type id and string or Page object
        representing the user that did the edit.

        The type id is one of 'ip' (DNS or numeric IP), 'user' (user name)
        or 'homepage' (Page instance of user's homepage).
    """
    result = 'ip', request.cfg.show_hosts and hostname or ''
    if userid:
        userdata = User(request, userid)
        if userdata.mailto_author and userdata.email:
            return ('email', userdata.email)
        elif userdata.name:
            interwiki = wikiutil.getInterwikiHomePage(request, username=userdata.name)
            if interwiki:
                result = ('interwiki', interwiki)
    return result


def get_printable_editor(request, userid, addr, hostname):
    """ Return a HTML-safe string representing the user that did the edit.
    """
    if request.cfg.show_hosts:
        title = " @ %s[%s]" % (hostname, addr)
    else:
        title = ""
    kind, info = get_editor(request, userid, addr, hostname)
    userdata = User(request, userid)
    if kind == 'interwiki':
        name = userdata.name
        aliasname = userdata.aliasname
        if not aliasname:
            aliasname = name
        title = aliasname + title
        text = (request.formatter.interwikilink(1, title=title, generated=True, *info) +
                request.formatter.text(name) +
                request.formatter.interwikilink(0, title=title, *info))
    elif kind == 'email':
        name = userdata.name
        aliasname = userdata.aliasname
        if not aliasname:
            aliasname = name
        title = aliasname + title
        url = 'mailto:%s' % info
        text = (request.formatter.url(1, url, css='mailto', title=title) +
                request.formatter.text(name) +
                request.formatter.url(0))
    elif kind == 'ip':
        try:
            idx = info.index('.')
        except ValueError:
            idx = len(info)
        title = '???' + title
        text = request.formatter.text(info[:idx])
    else:
        raise Exception("unknown EditorData type")
    return (request.formatter.span(1, title=title) +
            text +
            request.formatter.span(0))


def encodePassword(pwd, charset='utf-8'):
    """ Encode a cleartext password

    Compatible to Apache htpasswd SHA encoding.

    When using different encoding than 'utf-8', the encoding might fail
    and raise UnicodeError.

    @param pwd: the cleartext password, (unicode)
    @param charset: charset used to encode password, used only for
        compatibility with old passwords generated on moin-1.2.
    @rtype: string
    @return: the password in apache htpasswd compatible SHA-encoding,
        or None
    """
    import base64

    # Might raise UnicodeError, but we can't do anything about it here,
    # so let the caller handle it.
    pwd = pwd.encode(charset)

    pwd = sha.new(pwd).digest()
    pwd = '{SHA}' + base64.encodestring(pwd).rstrip()
    return pwd


def normalizeName(name):
    """ Make normalized user name

    Prevent impersonating another user with names containing leading,
    trailing or multiple whitespace, or using invisible unicode
    characters.

    Prevent creating user page as sub page, because '/' is not allowed
    in user names.

    Prevent using ':' and ',' which are reserved by acl.

    @param name: user name, unicode
    @rtype: unicode
    @return: user name that can be used in acl lines
    """
    username_allowedchars = "'@.-_" # ' for names like O'Brian or email addresses.
                                    # "," and ":" must not be allowed (ACL delimiters).
                                    # We also allow _ in usernames for nicer URLs.
    # Strip non alpha numeric characters (except username_allowedchars), keep white space
    name = ''.join([c for c in name if c.isalnum() or c.isspace() or c in username_allowedchars])

    # Normalize white space. Each name can contain multiple
    # words separated with only one space.
    name = ' '.join(name.split())

    return name


def isValidName(request, name):
    """ Validate user name

    @param name: user name, unicode
    """
    normalized = normalizeName(name)
    return (name == normalized) and not wikiutil.isGroupPage(request, name)


class User:
    """ A MoinMoin User """

    def __init__(self, request, id=None, name="", password=None, auth_username="", **kw):
        """ Initialize User object

        TODO: when this gets refactored, use "uid" not builtin "id"

        @param request: the request object
        @param id: (optional) user ID
        @param name: (optional) user name
        @param password: (optional) user password (unicode)
        @param auth_username: (optional) already authenticated user name
                              (e.g. when using http basic auth) (unicode)
        @keyword auth_method: method that was used for authentication,
                              default: 'internal'
        @keyword auth_attribs: tuple of user object attribute names that are
                               determined by auth method and should not be
                               changeable by preferences, default: ().
                               First tuple element was used for authentication.
        """

        self._item_collection = ItemCollection(request.cfg.user_backend, None)
        self._user = None

        self._cfg = request.cfg
        self.valid = 0
        self.id = id
        self.auth_username = auth_username
        self.auth_method = kw.get('auth_method', 'internal')
        self.auth_attribs = kw.get('auth_attribs', ())
        self.bookmarks = {} # interwikiname: bookmark

        # create some vars automatically
        self.__dict__.update(self._cfg.user_form_defaults)

        if name:
            self.name = name
        elif auth_username: # this is needed for user_autocreate
            self.name = auth_username

        # create checkbox fields (with default 0)
        for key, label in self._cfg.user_checkbox_fields:
            setattr(self, key, self._cfg.user_checkbox_defaults.get(key, 0))

        self.recoverpass_key = ""

        self.enc_password = ""
        if password:
            try:
                self.enc_password = encodePassword(password)
            except UnicodeError:
                pass # Should never happen

        #self.edit_cols = 80
        self.tz_offset = int(float(self._cfg.tz_offset) * 3600)
        self.language = ""
        self.real_language = "" # In case user uses "Browser setting". For language-statistics
        self.loaded = False
        self.date_fmt = ""
        self.datetime_fmt = ""
        self.quicklinks = self._cfg.quicklinks_default
        self.subscribed_pages = self._cfg.subscribed_pages_default
        self.email_subscribed_events = self._cfg.email_subscribed_events_default
        self.jabber_subscribed_events = self._cfg.jabber_subscribed_events_default
        self.theme_name = self._cfg.theme_default
        self.editor_default = self._cfg.editor_default
        self.editor_ui = self._cfg.editor_ui
        self.last_saved = str(time.time())

        # attrs not saved to profile
        self._request = request
        self._trail = []

        # we got an already authenticated username:
        check_pass = 0
        if not self.id and self.auth_username:
            self.id = getUserId(request, self.auth_username)
            if not password is None:
                check_pass = 1
        if self.id:
            self.load_from_id(check_pass)
        elif self.name:
            self.id = getUserId(self._request, self.name)
            if self.id:
                self.load_from_id(1)
            else:
                self.id = self.make_id()
        else:
            self.id = self.make_id()

        # "may" so we can say "if user.may.read(pagename):"
        if self._cfg.SecurityPolicy:
            self.may = self._cfg.SecurityPolicy(self)
        else:
            from MoinMoin.security import Default
            self.may = Default(self)

        if self.language and not self.language in i18n.wikiLanguages():
            self.language = 'en'

    def __repr__(self):
        return "<%s.%s at 0x%x name:%r valid:%r>" % (
            self.__class__.__module__, self.__class__.__name__,
            id(self), self.name, self.valid)

    def make_id(self):
        """ make a new unique user id """
        #!!! this should probably be a hash of REMOTE_ADDR, HTTP_USER_AGENT
        # and some other things identifying remote users, then we could also
        # use it reliably in edit locking
        from random import randint
        return "%s.%d" % (str(time.time()), randint(0, 65535))

    def create_or_update(self, changed=False):
        """ Create or update a user profile

        @param changed: bool, set this to True if you updated the user profile values
        """
        if self._cfg.user_autocreate:
            if not self.valid and not self.disabled or changed: # do we need to save/update?
                self.save() # yes, create/update user profile

    def exists(self):
        """ Do we have a user account for this user?

        @rtype: bool
        @return: true, if we have a user account
        """
        return self.id in self._item_collection

    def load_from_id(self, check_pass=0):
        """ Load user account data from disk.

        Can only load user data if the id number is already known.

        This loads all member variables, except "id" and "valid" and
        those starting with an underscore.

        @param check_pass: If 1, then self.enc_password must match the
                           password in the user account file.
        """
        if not self.exists():
            return

        self._user = self._item_collection[self.id]

        user_data = dict()
        user_data.update(self._user.metadata)

        # Validate data from user file. In case we need to change some
        # values, we set 'changed' flag, and later save the user data.
        changed = 0

        if check_pass:
            # If we have no password set, we don't accept login with username
            if not user_data['enc_password']:
                return
            # Check for a valid password, possibly changing encoding
            valid, changed = self._validatePassword(user_data)
            if not valid:
                return

        # Remove ignored checkbox values from user data
        for key, label in self._cfg.user_checkbox_fields:
            if key in user_data and key in self._cfg.user_checkbox_disable:
                del user_data[key]

        # Copy user data into user object
        for key, val in user_data.items():
            vars(self)[key] = val

        self.tz_offset = int(self.tz_offset)

        # Remove old unsupported attributes from user data file.
        remove_attributes = ['passwd', 'show_emoticons']
        for attr in remove_attributes:
            if hasattr(self, attr):
                delattr(self, attr)
                changed = 1

        # make sure checkboxes are boolean
        for key, label in self._cfg.user_checkbox_fields:
            try:
                setattr(self, key, int(getattr(self, key)))
            except ValueError:
                setattr(self, key, 0)

        # convert (old) hourly format to seconds
        if -24 <= self.tz_offset and self.tz_offset <= 24:
            self.tz_offset = self.tz_offset * 3600

        # clear trail
        self._trail = []

        if not self.disabled:
            self.valid = 1

        # Mark this user as loaded from disk, so UserCreatedEvent is not sent
        self.loaded = True

        # If user data has been changed, save fixed user data.
        if changed:
            self.save()

    def _validatePassword(self, data):
        """ Try to validate user password

        This is a private method and should not be used by clients.

        In pre 1.3, the wiki used some 8 bit charset. The user password
        was entered in this 8 bit password and passed to
        encodePassword. So old passwords can use any of the charset
        used.

        In 1.3, we use unicode internally, so we encode the password in
        encodePassword using utf-8.

        When we compare passwords we must compare with same encoding, or
        the passwords will not match. We don't know what encoding the
        password on the user file uses. We may ask the wiki admin to put
        this into the config, but he may be wrong.

        The way chosen is to try to encode and compare passwords using
        all the encoding that were available on 1.2, until we get a
        match, which means that the user is valid.

        If we get a match, we replace the user password hash with the
        utf-8 encoded version, and next time it will match on first try
        as before. The user password did not change, this change is
        completely transparent for the user. Only the sha digest will
        change.

        @param data: dict with user data
        @rtype: 2 tuple (bool, bool)
        @return: password is valid, password did change
        """
        # First try with default encoded password. Match only non empty
        # passwords. (require non empty enc_password)
        if self.enc_password and self.enc_password == data['enc_password']:
            return True, False

        # Try to match using one of pre 1.3 8 bit charsets

        # Get the clear text password from the form (require non empty
        # password)
        password = self._request.form.get('password', [None])[0]
        if not password:
            return False, False

        # First get all available pre13 charsets on this system
        pre13 = ['iso-8859-1', 'iso-8859-2', 'euc-jp', 'gb2312', 'big5', ]
        available = []
        for charset in pre13:
            try:
                encoder = codecs.getencoder(charset)
                available.append(charset)
            except LookupError:
                pass # missing on this system

        # Now try to match the password
        for charset in available:
            # Try to encode, failure is expected
            try:
                enc_password = encodePassword(password, charset=charset)
            except UnicodeError:
                continue

            # And match (require non empty enc_password)
            if enc_password and enc_password == data['enc_password']:
                # User password match - replace the user password in the
                # file with self.password
                data['enc_password'] = self.enc_password
                return True, True

        # No encoded password match, this must be wrong password
        return False, False

    def persistent_items(self):
        """ items we want to store into the user profile """
        return [(key, value) for key, value in vars(self).items()
                    if key not in self._cfg.user_transient_fields and key[0] != '_']

    def save(self):
        """
        Save user account data to user account file on disk.

        This saves all member variables, except "id" and "valid" and
        those starting with an underscore.
        """
        if not self.exists():
            self._user = self._item_collection.new_item(self.id)

        self._user.lock = True
        for key in self._user.metadata:
            del self._user.metadata[key]

        self.last_saved = str(time.time())

        attrs = self.persistent_items()
        attrs.sort()
        for key, value in attrs:
            self._user.metadata[key] = value

        self._user.metadata.save()
        self._user.lock = False

        arena = 'user'
        key = 'name2id'
        caching.CacheEntry(self._request, arena, key, scope='wiki').remove()
        try:
            del self._request.cfg.cache.name2id
        except:
            pass

        if not self.disabled:
            self.valid = 1

        if not self.loaded:
            event = events.UserCreatedEvent(self._request, self)
        else:
            event = events.UserChangedEvent(self._request, self)
        events.send_event(event)

    # -----------------------------------------------------------------
    # Time and date formatting

    def getTime(self, tm):
        """ Get time in user's timezone.

        @param tm: time (UTC UNIX timestamp)
        @rtype: int
        @return: tm tuple adjusted for user's timezone
        """
        return timefuncs.tmtuple(tm + self.tz_offset)


    def getFormattedDate(self, tm):
        """ Get formatted date adjusted for user's timezone.

        @param tm: time (UTC UNIX timestamp)
        @rtype: string
        @return: formatted date, see cfg.date_fmt
        """
        date_fmt = self.date_fmt or self._cfg.date_fmt
        return time.strftime(date_fmt, self.getTime(tm))


    def getFormattedDateTime(self, tm):
        """ Get formatted date and time adjusted for user's timezone.

        @param tm: time (UTC UNIX timestamp)
        @rtype: string
        @return: formatted date and time, see cfg.datetime_fmt
        """
        datetime_fmt = self.datetime_fmt or self._cfg.datetime_fmt
        return time.strftime(datetime_fmt, self.getTime(tm))

    # -----------------------------------------------------------------
    # Bookmark

    def setBookmark(self, tm):
        """ Set bookmark timestamp.

        @param tm: timestamp
        """
        if self.valid:
            interwikiname = unicode(self._cfg.interwikiname or '')
            bookmark = unicode(tm)
            self.bookmarks[interwikiname] = bookmark
            self.save()

    def getBookmark(self):
        """ Get bookmark timestamp.

        @rtype: int
        @return: bookmark timestamp or None
        """
        bm = None
        interwikiname = unicode(self._cfg.interwikiname or '')
        if self.valid:
            try:
                bm = int(self.bookmarks[interwikiname])
            except (ValueError, KeyError):
                pass
        return bm

    def delBookmark(self):
        """ Removes bookmark timestamp.

        @rtype: int
        @return: 0 on success, 1 on failure
        """
        interwikiname = unicode(self._cfg.interwikiname or '')
        if self.valid:
            try:
                del self.bookmarks[interwikiname]
            except KeyError:
                return 1
            self.save()
            return 0
        return 1

    # -----------------------------------------------------------------
    # Subscribe

    def getSubscriptionList(self):
        """ Get list of pages this user has subscribed to

        @rtype: list
        @return: pages this user has subscribed to
        """
        return self.subscribed_pages

    def isSubscribedTo(self, pagelist):
        """ Check if user subscription matches any page in pagelist.

        The subscription list may contain page names or interwiki page
        names. e.g 'Page Name' or 'WikiName:Page_Name'

        TODO: check if it's fast enough when getting called for many
              users from page.getSubscribersList()

        @param pagelist: list of pages to check for subscription
        @rtype: bool
        @return: if user is subscribed any page in pagelist
        """
        if not self.valid:
            return False

        import re
        # Create a new list with both names and interwiki names.
        pages = pagelist[:]
        if self._cfg.interwikiname:
            pages += [self._interWikiName(pagename) for pagename in pagelist]
        # Create text for regular expression search
        text = '\n'.join(pages)

        for pattern in self.getSubscriptionList():
            # Try simple match first
            if pattern in pages:
                return True
            # Try regular expression search, skipping bad patterns
            try:
                pattern = re.compile(r'^%s$' % pattern, re.M)
            except re.error:
                continue
            if pattern.search(text):
                return True

        return False

    def subscribe(self, pagename):
        """ Subscribe to a wiki page.

        To enable shared farm users, if the wiki has an interwiki name,
        page names are saved as interwiki names.

        @param pagename: name of the page to subscribe
        @type pagename: unicode
        @rtype: bool
        @return: if page was subscribed
        """
        if self._cfg.interwikiname:
            pagename = self._interWikiName(pagename)

        if pagename not in self.subscribed_pages:
            self.subscribed_pages.append(pagename)
            self.save()

            # Send a notification
            from MoinMoin.events import SubscribedToPageEvent, send_event
            e = SubscribedToPageEvent(self._request, pagename, self.name)
            send_event(e)
            return True

        return False

    def unsubscribe(self, pagename):
        """ Unsubscribe a wiki page.

        Try to unsubscribe by removing non-interwiki name (leftover
        from old use files) and interwiki name from the subscription
        list.

        Its possible that the user will be subscribed to a page by more
        then one pattern. It can be both pagename and interwiki name,
        or few patterns that all of them match the page. Therefore, we
        must check if the user is still subscribed to the page after we
        try to remove names from the list.

        @param pagename: name of the page to subscribe
        @type pagename: unicode
        @rtype: bool
        @return: if unsubscrieb was successful. If the user has a
            regular expression that match, it will always fail.
        """
        changed = False
        if pagename in self.subscribed_pages:
            self.subscribed_pages.remove(pagename)
            changed = True

        interWikiName = self._interWikiName(pagename)
        if interWikiName and interWikiName in self.subscribed_pages:
            self.subscribed_pages.remove(interWikiName)
            changed = True

        if changed:
            self.save()
        return not self.isSubscribedTo([pagename])

    # -----------------------------------------------------------------
    # Quicklinks

    def getQuickLinks(self):
        """ Get list of pages this user wants in the navibar

        @rtype: list
        @return: quicklinks from user account
        """
        return self.quicklinks

    def isQuickLinkedTo(self, pagelist):
        """ Check if user quicklink matches any page in pagelist.

        @param pagelist: list of pages to check for quicklinks
        @rtype: bool
        @return: if user has quicklinked any page in pagelist
        """
        if not self.valid:
            return False

        for pagename in pagelist:
            if pagename in self.quicklinks:
                return True
            interWikiName = self._interWikiName(pagename)
            if interWikiName and interWikiName in self.quicklinks:
                return True

        return False

    def addQuicklink(self, pagename):
        """ Adds a page to the user quicklinks

        If the wiki has an interwiki name, all links are saved as
        interwiki names. If not, as simple page name.

        @param pagename: page name
        @type pagename: unicode
        @rtype: bool
        @return: if pagename was added
        """
        changed = False
        interWikiName = self._interWikiName(pagename)
        if interWikiName:
            if pagename in self.quicklinks:
                self.quicklinks.remove(pagename)
                changed = True
            if interWikiName not in self.quicklinks:
                self.quicklinks.append(interWikiName)
                changed = True
        else:
            if pagename not in self.quicklinks:
                self.quicklinks.append(pagename)
                changed = True

        if changed:
            self.save()
        return changed

    def removeQuicklink(self, pagename):
        """ Remove a page from user quicklinks

        Remove both interwiki and simple name from quicklinks.

        @param pagename: page name
        @type pagename: unicode
        @rtype: bool
        @return: if pagename was removed
        """
        changed = False
        interWikiName = self._interWikiName(pagename)
        if interWikiName and interWikiName in self.quicklinks:
            self.quicklinks.remove(interWikiName)
            changed = True
        if pagename in self.quicklinks:
            self.quicklinks.remove(pagename)
            changed = True

        if changed:
            self.save()
        return changed

    def _interWikiName(self, pagename):
        """ Return the inter wiki name of a page name

        @param pagename: page name
        @type pagename: unicode
        """
        if not self._cfg.interwikiname:
            return None

        return "%s:%s" % (self._cfg.interwikiname, pagename)

    # -----------------------------------------------------------------
    # Trail

    def _wantTrail(self):
        return (not self.valid and self._request.session.is_stored  # anon session
                or self.valid and (self.show_page_trail or self.remember_last_visit))  # logged-in session

    def addTrail(self, page):
        """ Add page to trail.

        @param page: the page (object) to add to the trail
        """
        if self._wantTrail():
            # load trail if not known
            self.getTrail()

            pagename = page.page_name
            # Add only existing pages that the user may read
            if not (page.exists() and self._request.user.may.read(pagename)):
                return

            # Save interwiki links internally
            if self._cfg.interwikiname:
                pagename = self._interWikiName(pagename)

            # Don't append tail to trail ;)
            if self._trail and self._trail[-1] == pagename:
                return

            # Append new page, limiting the length
            self._trail = [p for p in self._trail if p != pagename]
            self._trail = self._trail[-(self._cfg.trail_size-1):]
            self._trail.append(pagename)
            self.saveTrail()

    def saveTrail(self):
        """ Save trail into session """
        if not self._request.session.is_new:
            self._request.session['trail'] = self._trail

    def getTrail(self):
        """ Return list of recently visited pages.

        @rtype: list
        @return: pages in trail
        """
        if not self._trail and self._wantTrail():
            trail = self._request.session.get('trail', [])
            trail = [t.strip() for t in trail]
            trail = [t for t in trail if t]
            self._trail = trail[-self._cfg.trail_size:]

        return self._trail

    # -----------------------------------------------------------------
    # Other

    def isCurrentUser(self):
        """ Check if this user object is the user doing the current request """
        return self._request.user.name == self.name

    def isSuperUser(self):
        """ Check if this user is superuser """
        request = self._request
        if request.cfg.DesktopEdition and request.remote_addr == '127.0.0.1' and request.user and request.user.valid:
            # the DesktopEdition gives any local user superuser powers
            return True
        superusers = request.cfg.superuser
        assert isinstance(superusers, (list, tuple))
        return self.valid and self.name and self.name in superusers

    def host(self):
        """ Return user host """
        _ = self._request.getText
        host = self.isCurrentUser() and self._cfg.show_hosts and self._request.remote_addr
        return host or _("<unknown>")

    def wikiHomeLink(self):
        """ Return wiki markup usable as a link to the user homepage,
            it doesn't matter whether it already exists or not.
        """
        wikiname, pagename = wikiutil.getInterwikiHomePage(self._request, self.name)
        if wikiname == 'Self':
            if wikiutil.isStrictWikiname(self.name):
                markup = pagename
            else:
                markup = '[[%s]]' % pagename
        else:
            markup = '[[%s:%s]]' % (wikiname, pagename)
        return markup

    def signature(self):
        """ Return user signature using wiki markup

        Users sign with a link to their homepage.
        Visitors return their host address.

        TODO: The signature use wiki format only, for example, it will
        not create a link when using rst format. It will also break if
        we change wiki syntax.
        """
        if self.name:
            return self.wikiHomeLink()
        else:
            return self.host()

    def generate_recovery_token(self):
        key = random_string(64, "abcdefghijklmnopqrstuvwxyz0123456789")
        msg = str(int(time.time()))
        h = hmac.new(key, msg, sha).hexdigest()
        self.recoverpass_key = key
        self.save()
        return msg + '-' + h

    def apply_recovery_token(self, tok, newpass):
        key = self.recoverpass_key
        parts = tok.split('-')
        if len(parts) != 2:
            return False
        try:
            stamp = int(parts[0])
        except ValueError:
            return False
        # only allow it to be valid for twelve hours
        if stamp + 12*60*60 < time.time():
            return False
        # check hmac
        h = hmac.new(self.recoverpass_key, str(stamp), sha).hexdigest()
        if h != parts[1]:
            return False
        self.recoverpass_key = ""
        self.enc_password = encodePassword(newpass)
        self.save()
        return True

    def mailAccountData(self, cleartext_passwd=None):
        """ Mail a user who forgot his password a message enabling
            him to login again.
        """
        from MoinMoin.mail import sendmail
        from MoinMoin.wikiutil import getLocalizedPage
        _ = self._request.getText

        tok = self.generate_recovery_token()

        text = '\n' + _("""\
Login Name: %s

Password recovery token: %s

Password reset URL: %s/?action=recoverpass&name=%s&token=%s
""") % (
                        self.name,
                        tok,
                        self._request.getBaseURL(),
                        url_quote_plus(self.name),
                        tok, )

        text = _("""\
Somebody has requested to email you a password recovery token.

If you lost your password, please go to the password reset URL below or
go to the password recovery page again and enter your username and the
recovery token.
""") + text


        subject = _('[%(sitename)s] Your wiki account data',
                ) % {'sitename': self._cfg.sitename or "Wiki"}
        mailok, msg = sendmail.sendmail(self._request, [self.email], subject,
                                    text, mail_from=self._cfg.mail_from)
        return mailok, msg

