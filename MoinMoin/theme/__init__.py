# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Theme Package

    @copyright: 2003-2009 MoinMoin:ThomasWaldmann,
                2008 MoinMoin:RadomirDopieralski,
                2010 MoinMoin:DiogenesAugustoFernandesHerminio
    @license: GNU GPL, see COPYING for details.
"""

import os, StringIO
import urlparse

from jinja2 import Environment, FileSystemLoader, Template, FileSystemBytecodeCache, Markup

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import i18n, wikiutil, config, version, caching, user
from MoinMoin import action as actionmod
from MoinMoin.items import Item
from MoinMoin.Page import Page
from MoinMoin.util import pysupport
from MoinMoin.items import EDIT_LOG_USERID, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME

modules = pysupport.getPackageModules(__file__)


class ThemeBase(object):
    """ Base class for themes

    This class supplies all the standard template that sub classes can
    use without rewriting the same code. If you want to change certain
    elements, override them.
    """
    name = 'base'

    _ = lambda x: x  # We don't have gettext at this moment, so we fake it
    icons = {
        # key         alt                        icon filename      w   h
        # FileAttach
        'attach':     ("%(attach_count)s",       "moin-attach.png",   16, 16),
        'info':       ("[INFO]",                 "moin-info.png",     16, 16),
        'attachimg':  (_("[ATTACH]"),            "attach.png",        32, 32),
        # RecentChanges
        'rss':        (_("[RSS]"),               "moin-rss.png",      16, 16),
        'deleted':    (_("[DELETED]"),           "moin-deleted.png",  16, 16),
        'updated':    (_("[UPDATED]"),           "moin-updated.png",  16, 16),
        'renamed':    (_("[RENAMED]"),           "moin-renamed.png",  16, 16),
        'conflict':   (_("[CONFLICT]"),          "moin-conflict.png", 16, 16),
        'new':        (_("[NEW]"),               "moin-new.png",      16, 16),
        'diffrc':     (_("[DIFF]"),              "moin-diff.png",     16, 16),
        # General
        'bottom':     (_("[BOTTOM]"),            "moin-bottom.png",   16, 16),
        'top':        (_("[TOP]"),               "moin-top.png",      16, 16),
        'www':        ("[WWW]",                  "moin-www.png",      16, 16),
        'mailto':     ("[MAILTO]",               "moin-email.png",    16, 16),
        'news':       ("[NEWS]",                 "moin-news.png",     16, 16),
        'telnet':     ("[TELNET]",               "moin-telnet.png",   16, 16),
        'ftp':        ("[FTP]",                  "moin-ftp.png",      16, 16),
        'file':       ("[FILE]",                 "moin-ftp.png",      16, 16),
        # search forms
        'searchbutton': ("[?]",                  "moin-search.png",   16, 16),
        'interwiki':  ("[%(wikitag)s]",          "moin-inter.png",    16, 16),

        # smileys (this is CONTENT, but good looking smileys depend on looking
        # adapted to the theme background color and theme style in general)
        #vvv    ==      vvv  this must be the same for GUI editor converter
        'X-(':        ("X-(",                    'angry.png',         16, 16),
        ':D':         (":D",                     'biggrin.png',       16, 16),
        '<:(':        ("<:(",                    'frown.png',         16, 16),
        ':o':         (":o",                     'redface.png',       16, 16),
        ':(':         (":(",                     'sad.png',           16, 16),
        ':)':         (":)",                     'smile.png',         16, 16),
        'B)':         ("B)",                     'smile2.png',        16, 16),
        ':))':        (":))",                    'smile3.png',        16, 16),
        ';)':         (";)",                     'smile4.png',        16, 16),
        '/!\\':       ("/!\\",                   'alert.png',         16, 16),
        '<!>':        ("<!>",                    'attention.png',     16, 16),
        '(!)':        ("(!)",                    'idea.png',          16, 16),
        ':-?':        (":-?",                    'tongue.png',        16, 16),
        ':\\':        (":\\",                    'ohwell.png',        16, 16),
        '>:>':        (">:>",                    'devil.png',         16, 16),
        '|)':         ("|)",                     'tired.png',         16, 16),
        ':-(':        (":-(",                    'sad.png',           16, 16),
        ':-)':        (":-)",                    'smile.png',         16, 16),
        'B-)':        ("B-)",                    'smile2.png',        16, 16),
        ':-))':       (":-))",                   'smile3.png',        16, 16),
        ';-)':        (";-)",                    'smile4.png',        16, 16),
        '|-)':        ("|-)",                    'tired.png',         16, 16),
        '(./)':       ("(./)",                   'checkmark.png',     16, 16),
        '{OK}':       ("{OK}",                   'thumbs-up.png',     16, 16),
        '{X}':        ("{X}",                    'icon-error.png',    16, 16),
        '{i}':        ("{i}",                    'icon-info.png',     16, 16),
        '{1}':        ("{1}",                    'prio1.png',         15, 13),
        '{2}':        ("{2}",                    'prio2.png',         15, 13),
        '{3}':        ("{3}",                    'prio3.png',         15, 13),
        '{*}':        ("{*}",                    'star_on.png',       16, 16),
        '{o}':        ("{o}",                    'star_off.png',      16, 16),
    }
    del _

    # Style sheets - usually there is no need to override this in sub
    # classes. Simply supply the css files in the css directory.

    # Standard set of style sheets
    stylesheets = (
        # media         basename
        ('all',         'common'),
        ('screen',      'screen'),
        ('print',       'print'),
        ('projection',  'projection'),
        )

    maxPagenameLength = 25  # maximum length for shortened page names

    def __init__(self, request):
        """
        Initialize the theme object.

        @param request: the request object
        """
        self.request = request
        # TODO: get rid of this vvv
        page = request.page
        if page is None:
            path = urlparse.urlparse(request.getBaseURL()).path[1:]
            page = Page(request, path)
        self.page = page
        # TODO: get rid of this ^^^
        item_name = page.page_name
        self.item_name = item_name
        storage = request.storage
        self.storage = storage
        self.item_exists = storage.has_item(item_name)
        self.output_mimetype = page.output_mimetype
        self.output_charset = page.output_charset
        self.cfg = request.cfg
        self.user = request.user
        self.item_readable = request.user.may.read(item_name)
        self.item_writable = request.user.may.write(item_name)
        self.ui_lang = request.lang
        self.ui_dir = i18n.getDirection(self.ui_lang)
        self.content_lang = request.content_lang
        self.content_dir = i18n.getDirection(self.content_lang)
        self.msg_list = []

        jinja_cachedir = os.path.join(request.cfg.cache_dir, 'jinja')
        try:
            os.mkdir(jinja_cachedir)
        except:
            pass

        jinja_templatedir = os.path.join(os.path.dirname(__file__), '..', 'templates')

        self.env = Environment(loader=FileSystemLoader(jinja_templatedir),
                               bytecode_cache=FileSystemBytecodeCache(jinja_cachedir, '%s'),
                               extensions=['jinja2.ext.i18n'])
        from werkzeug import url_quote, url_encode
        self.env.filters['urlencode'] = lambda x: url_encode(x)
        self.env.filters['urlquote'] = lambda x: url_quote(x)
        self.env.filters['datetime_format'] = lambda tm, u=request.user: u.getFormattedDateTime(tm)
        self.env.filters['date_format'] = lambda tm, u=request.user: u.getFormattedDate(tm)
        self.env.filters['user_format'] = lambda rev, request=request: \
                                              user.get_printable_editor(request,
                                                                        rev.get(EDIT_LOG_USERID),
                                                                        rev.get(EDIT_LOG_ADDR),
                                                                        rev.get(EDIT_LOG_HOSTNAME))
        self.env.globals.update({
                                'theme': self,
                                'user': request.user,
                                'cfg': request.cfg,
                                '_': request.getText,
                                'href': request.href,
                                'static_href': request.static_href,
                                'abs_href': request.abs_href,
                                'translated_item_name': self.translated_item_name})

    def translated_item_name(self, item_en):
        """
        Get a translated item name.
        If a translated item exists return its name, if not return item name in English.

        @param item_name: string
        @rtype: string
        """
        request = self.request
        item_lang_request = request.getText(item_en)
        if self.storage.has_item(item_lang_request):
            return item_lang_request

        item_lang_default = i18n.getText(item_en, request, self.cfg.language_default)
        if self.storage.has_item(item_lang_default):
            return item_lang_default
        return item_en

    def location_breadcrumbs(self):
        """
        Assemble the location using breadcrumbs (was: title)

        @rtype: string
        @return: title in breadcrumbs
        """
        item_name = self.item_name
        segments = item_name.split('/')
        content = []
        current_item = ''
        for s in segments:
            current_item += s
            content.append((s, current_item, self.storage.has_item(current_item)))
            current_item += '/'
        return content

    def user_breadcrumbs(self):
        """
        Assemble the username / userprefs using breadcrumbs (was: username)

        @rtype: list
        @return: actions of user in breadcrumbs
        """
        # TODO: split this method into multiple methods
        request = self.request
        _ = request.getText
        href = request.href
        item_name = self.item_name
        user = self.user

        userlinks = []
        # Add username/homepage link for registered users. We don't care
        # if it exists, the user can create it.
        if user.valid and user.name:
            wikiname, itemname = wikiutil.getInterwikiHomePage(request)
            name = user.name
            aliasname = user.aliasname
            if not aliasname:
                aliasname = name
            title = "%s @ %s" % (aliasname, wikiname)
            # link to (interwiki) user homepage
            if wikiname == "Self":
                exists = self.storage.has_item(itemname)
            else:
                # We cannot check if wiki pages exists in remote wikis
                exists = True
            wiki_name, item_name = wikiutil.split_interwiki(itemname)
            wiki_name, wiki_base_url, item_name, err = wikiutil.resolve_interwiki(request, wiki_name, item_name)
            wiki_href = wikiutil.join_wiki(wiki_base_url, item_name)
            item = wiki_href, aliasname, 'id="userhome" title="%s"' % title, exists
            userlinks.append(item)
            # link to userprefs action
            if 'userprefs' not in self.cfg.actions_excluded:
                item = (href(item_name, do='userprefs'), _('Settings'),
                        'class="userprefs" rel="nofollow"', True)
                userlinks.append(item)

        if user.valid:
            if user.auth_method in request.cfg.auth_can_logout:
                item = (href(item_name, do='logout', logout='logout'), _('Logout'),
                        'class="logout" rel="nofollow"', True)
                userlinks.append(item)
        else:
            url = None
            # special direct-login link if the auth methods want no input
            if request.cfg.auth_login_inputs == ['special_no_input']:
                url = href(item_name, do='login', login=1)
            if request.cfg.auth_have_login:
                url = url or href(item_name, do='login')
                item = url, _("Login"), 'class="login" rel="nofollow"', True
                userlinks.append(item)
        return userlinks

    def split_navilink(self, text, localize=1):
        """
        Split navibar links into pagename, link to page

        Admin or user might want to use shorter navibar items by using
        the [[page|title]] or [[url|title]] syntax. In this case, we don't
        use localization, and the links goes to page or to the url, not
        the localized version of page.

        Supported syntax:
            * PageName
            * WikiName:PageName
            * wiki:WikiName:PageName
            * url
            * all targets as seen above with title: [[target|title]]

        @param text: the text used in config or user preferences
        @rtype: tuple
        @return: pagename or url, link to page or url
        """
        request = self.request
        title = None
        wiki_local = '' # means local wiki

        # Handle [[pagename|title]] or [[url|title]] formats
        if text.startswith('[[') and text.endswith(']]'):
            text = text[2:-2]
            try:
                item_name, title = text.split('|', 1)
                item_name = item_name.strip()
                title = title.strip()
                localize = 0
            except (ValueError, TypeError):
                # Just use the text as is.
                item_name = text.strip()
        else:
            item_name = text

        if wikiutil.is_URL(item_name):
            if not title:
                title = item_name
            url = self.request.href(item_name)
            return item_name, url, title, wiki_local

        # remove wiki: url prefix
        if item_name.startswith("wiki:"):
            item_name = item_name[5:]

        # try handling interwiki links
        wiki_name, item_name = wikiutil.split_interwiki(item_name)
        wiki_name, wiki_base_url, item_name, err = wikiutil.resolve_interwiki(request, wiki_name, item_name)
        href = wikiutil.join_wiki(wiki_base_url, item_name)
        if wiki_name not in [request.cfg.interwikiname, 'Self', ]:
            if not title:
                title = item_name
            return item_name, href, title, wiki_name
                
        # Handle regular pagename like "FrontPage"
        item_name = wikiutil.normalize_pagename(item_name, request.cfg)

        # Use localized pages for the current user
        if localize:
            item_name = self.translated_item_name(item_name)

        if not title:
            title = item_name
        return item_name, item_name, title, wiki_local

    def shortenPagename(self, name):
        """
        Shorten page names

        Shorten very long page names that tend to break the user
        interface. The short name is usually fine, unless really stupid
        long names are used (WYGIWYD).

        If you don't like to do this in your theme, or want to use
        different algorithm, override this method.

        @param name: page name, unicode
        @rtype: unicode
        @return: shortened version.
        """
        maxLength = self.maxPagenameLength
        # First use only the sub page name, that might be enough
        if len(name) > maxLength:
            name = name.split('/')[-1]
            # If it's not enough, replace the middle with '...'
            if len(name) > maxLength:
                half, left = divmod(maxLength - 3, 2)
                name = u'%s...%s' % (name[:half + left], name[-half:])
        return name

    def navibar(self):
        """
        Assemble the navibar

        @param d: parameter dictionary
        @rtype: unicode
        @return: navibar html
        """
        request = self.request
        items = []  # navibar items
        current = self.item_name

        # Process config navi_bar
        for text in request.cfg.navi_bar:
            pagename, url, link_text, title = self.split_navilink(text)
            items.append(('wikilink', url, link_text, title))

        # Add user links to wiki links.
        userlinks = self.user.getQuickLinks()
        for text in userlinks:
            # Split text without localization, user knows what he wants
            pagename, url, link_text, title = self.split_navilink(text, localize=0)
            items.append(('userlink', url, link_text, title))

        # Add sister pages.
        for sistername, sisterurl in request.cfg.sistersites:
            if sistername == request.cfg.interwikiname:  # it is THIS wiki
                items.append(('sisterwiki current', sisterurl, sistername))
            else:
                cache = caching.CacheEntry(request, 'sisters', sistername, 'farm', use_pickle=True)
                if cache.exists():
                    data = cache.content()
                    sisterpages = data['sisterpages']
                    if current in sisterpages:
                        url = sisterpages[current]
                        items.append(('sisterwiki', url, sistername, ''))
        return items

    def get_icon(self, icon):
        """
        Return icon data from self.icons

        If called from <<Icon(file)>> we have a filename, not a
        key. Using filenames is deprecated, but for now, we simulate old
        behavior.

        @param icon: icon name or file name (string)
        @rtype: tuple
        @return: alt (unicode), href (string), width, height (int)
        """
        if icon in self.icons:
            alt, icon, w, h = self.icons[icon]
        else:
            # Create filenames to icon data mapping on first call, then
            # cache in class for next calls.
            if not getattr(self.__class__, 'iconsByFile', None):
                d = {}
                for data in self.icons.values():
                    d[data[1]] = data
                self.__class__.iconsByFile = d

            # Try to get icon data by file name
            if icon in self.iconsByFile:
                alt, icon, w, h = self.iconsByFile[icon]
            else:
                alt, icon, w, h = '', icon, '', ''

        img_url = self.request.static_href(self.name, 'img', icon)
        return alt, img_url, w, h

    def make_icon(self, icon, vars=None, **kw):
        """
        This is the central routine for making <img> tags for icons!
        All icons stuff except the top left logo and search field icons are
        handled here.

        @param icon: icon id (dict key)
        @param vars: ...
        @rtype: string
        @return: icon html (img tag)
        """
        if vars is None:
            vars = {}
        alt, img, w, h = self.get_icon(icon)
        try:
            alt = alt % vars
        except KeyError, err:
            alt = 'KeyError: %s' % str(err)
        alt = self.request.getText(alt)
        tag = self.request.formatter.image(src=img, alt=alt, width=w, height=h, **kw)
        return tag

    def path_breadcrumbs(self):
        """
        Assemble path breadcrumbs (a.k.a.: trail)

        @rtype: list
        @return: path breadcrumbs items in tuple (item_name, url, exists)
        """
        request = self.request
        user = self.user
        items = []
        if not user.valid or user.show_trail:
            trail = user.getTrail()
            if trail:
                for interwiki_item_name in trail:
                    wiki_name, item_name = wikiutil.split_interwiki(interwiki_item_name)
                    wiki_name, wiki_base_url, item_name, err = wikiutil.resolve_interwiki(request, wiki_name, item_name)
                    href = wikiutil.join_wiki(wiki_base_url, item_name)
                    if wiki_name in [request.cfg.interwikiname, 'Self', ]:
                        exists = self.storage.has_item(item_name)
                        wiki_name = '' # means "this wiki" for the theme code
                    else:
                        exists = True # we can't detect existance of remote items
                    items.append((wiki_name, item_name, href, exists, err))
        return items

    def shouldShowPageInfo(self):
        """
        Should we show page info?

        Should be implemented by actions. For now, we check here by action
        name and page.

        @param page: current page
        @rtype: bool
        @return: true if should show page info
        """
        if self.item_exists and self.item_readable:
            # These actions show the page content.
            # TODO: on new action, page info will not show.
            # A better solution will be if the action itself answer the question: showPageInfo().
            contentActions = [u'', u'show', u'refresh', u'preview', u'diff',
                              u'subscribe', u'rename', u'copy', u'backlink',
                             ]
            return self.request.action in contentActions
        return False

    def universal_edit_button(self): # TODO: give this a better name that describes what this method tells
        """
        Should we show an edit link in the header?
        User have permission? If yes, show the universal edit button.
        @rtype: boolean
        """
        can_modify = 'modify' not in self.cfg.actions_excluded
        return can_modify and self.item_exists and self.item_writable

    def actions_menu(self):
        """
        Create actions menu list and items data dict

        The menu will contain the same items always, but items that are
        not available will be disabled (some broken browsers will let
        you select disabled options though).

        The menu should give best user experience for javascript
        enabled browsers, and acceptable behavior for those who prefer
        not to use Javascript.

        @param page: current page, Page object
        @rtype: unicode
        @return: actions menu html fragment
        """
        # TODO: Move actionsMenuInit() into body onload
        request = self.request
        _ = request.getText
        rev = request.rev

        menu = [
            'rc',
            '__separator__',
            'delete',
            'rename',
            'copy',
            '__separator__',
            'RenderAsDocbook',
            'refresh',
            'LikePages',
            'LocalSiteMap',
            'MyPages',
            'SubscribeUser',
            'PackagePages',
            'SyncPages',
            'backlink',
            ]

        titles = {
            # action: menu title
            '__title__': _("More Actions:"),
            # Translation may need longer or shorter separator
            '__separator__': _('------------------------'),
            'refresh': _('Delete Cache'),
            'rename': _('Rename Item'),
            'delete': _('Delete Item'),
            'rc': _('Recent Changes'),
            'copy': _('Copy Item'),
            'LikePages': _('Like Pages'),
            'LocalSiteMap': _('Local Site Map'),
            'MyPages': _('My Pages'),
            'SubscribeUser': _('Subscribe User'),
            'PackagePages': _('Package Pages'),
            'RenderAsDocbook': _('Render as Docbook'),
            'SyncPages': _('Sync Pages'),
            'backlink': _('What links here?'),
            }

        options = []

        # Format standard actions
        available = actionmod.get_names(request.cfg)
        for action in menu:
            do = action
            disabled = False
            title = titles[action]
            # removes excluded actions from the more actions menu
            if action in request.cfg.actions_excluded:
                continue

            # SubscribeUser action enabled only if user has admin rights
            if action == 'SubscribeUser' and not self.user.may.admin(self.item_name):
                do = 'show'
                disabled = True

            # Special menu items. Without javascript, executing will
            # just return to the page.
            if action.startswith('__'):
                do = 'show'

            # Actions which are not available for this wiki, user or page
            if action == '__separator__' or (action[0].isupper() and not action in available):
                disabled = True
            options.append((do, disabled, title))

        # Add custom actions not in the standard menu
        more = [item for item in available if not item in titles]
        more.sort()
        if more:
            # Add separator
            separator = ('show', True, titles['__separator__'])
            options.append(separator)
            # Add more actions (all enabled)
            for action in more:
                do = action
                title = action
                # Use translated version if available
                title = _(title)
                options.append((do, False, title))

        return self.render_template('actions_menu.html', label=titles['__title__'], options=options)

    def shouldShowEditbar(self):
        """
        Should we show the editbar?

        Actions should implement this, because only the action knows if
        the edit bar makes sense. Until it goes into actions, we do the
        checking here.

        @param page: current page
        @rtype: bool
        @return: true if editbar should show
        """
        # Show editbar only for existing pages, that the user may read.
        # If you may not read, you can't edit, so you don't need editbar.
        if self.item_exists and self.item_readable:
            form = self.request.form
            action = self.request.action
            # Do not show editbar on edit but on save/cancel
            return not (action == 'modify' and
                        not form.has_key('button_save') and
                        not form.has_key('button_cancel'))
        return False

    def parent_page(self):
        """
        Return name of parent page for the current page
        @rtype: unicode
        @return: parent page name
        """
        item_name = self.item_name
        parent_page_name = wikiutil.ParentPageName(item_name)
        if item_name and parent_page_name:
            return parent_page_name

    def link_supplementation_page(self):
        """
        If the discussion page doesn't exist and the user
        has no right to create it, show a disabled link.

        @rtype: bool
        """
        suppl_name = self.cfg.supplementation_page_name
        suppl_name_full = "%s/%s" % (self.item_name, suppl_name)

        return self.storage.has_item(suppl_name_full) or self.user.may.write(suppl_name_full)

    def add_msg(self, msg, msg_class=None):
        """
        Adds a message to a list which will be used to generate status
        information.

        @param msg: additional message
        @param msg_class: html class for the div of the additional message.
        """
        if not msg_class:
            msg_class = 'dialog'
        try:
            msg = msg.render()
        except AttributeError:
            msg = '<div class="%s">%s</div>' % (msg_class, msg)
        self.msg_list.append(msg)

    # TODO: reimplement on-wiki-page sidebar definition with converter2

    # Properties ##############################################################

    @property
    def special_item_names(self):
        """
        Return a list of item names for items that are considered "index" items.
        For index items, base.html adds cfg.html_head_index.

        @rtype: list
        @return: list of item names
        """
        page_front_page = self.translated_item_name(self.cfg.page_front_page)
        page_title_index = self.translated_item_name('TitleIndex')
        page_site_navigation = self.translated_item_name('SiteNavigation')
        page_find_page = self.translated_item_name('FindPage')
        return [page_front_page, self.cfg.page_front_page,
                page_title_index, 'TitleIndex',
                page_find_page, 'FindPage',
                page_site_navigation, 'SiteNavigation',
               ]

    # Public Functions ########################################################

    def send_title(self, text, content=None, **keywords):
        """
        Output the page header (and title).

        @param text: the title text
        @keyword page: the page instance that called us - using this is more efficient than using pagename..
        @keyword pagename: 'PageName'
        @keyword media: css media type, defaults to 'screen'
        @keyword allow_doubleclick: 1 (or 0)
        @keyword html_head: additional <head> code
        @keyword body_attr: additional <body> attributes
        @keyword body_onload: additional "onload" JavaScript code
        """
        request = self.request
        _ = request.getText

        if keywords.has_key('page'):
            page = keywords['page']
            pagename = page.page_name
        else:
            pagename = keywords.get('pagename', '')
            page = Page(request, pagename)
        if keywords.get('msg', ''):
            raise DeprecationWarning("Using send_page(msg=) is deprecated! Use theme.add_msg() instead!")
        #Attributes to use directly in template
        # Or to reduce parameters of functions of JinjaTheme
        self.page = page
        self.item_name = page.page_name or ''
        self.head_title = text
        request.write(self.render_content(page.page_name))

    def render_content(self, item_name, content=None, title=None, page=None, pagename=None,
                        allow_doubleclick=None, pi_refresh=None, html_head=None, trail=None, **keywords):
        """
        Render some content plus Theme header/footer.
        If content is None, the normal Item content for item_name will be rendered.
        """
        request = self.request
        _ = request.getText

        #TODO: Have to fix this code (looks ugly for me)
        if keywords.has_key('page'):
            page = keywords['page']
            pagename = page.page_name
        else:
            pagename = item_name
            page = Page(request, pagename)
        if keywords.get('msg', ''):
            raise DeprecationWarning("Using send_page(msg=) is deprecated! Use theme.add_msg() instead!")

        if content is None:
            item = Item.create(request, item_name)
            content = item.do_show()
        if title is None:
            title = item_name

        #Attributes to use directly in template
        # Or to reduce parameters of functions of JinjaTheme
        self.page = page
        self.item_name = page.page_name or ''
        self.head_title = title

        html = self.render_template(gettext=self.request.getText,
                                    item_name=item_name,
                                    title=title,
                                    content=content,
                                    allow_doubleclick=allow_doubleclick,
                                    pi_refresh=pi_refresh,
                                    html_head=html_head,
                                    trail=trail,
                                    **keywords)
        return html

    def render_template(self, filename='layout.html', **context):
        # TODO: change it to be render(self, name, **context)
        """
        Base function that renders a template using Jinja2.

        @param filename: name of the template to render.
        @param context: used to pass variables to template.
        @return: rendered output
        """
        template = self.env.get_template(filename)
        return template.render(**context)


class ThemeNotFound(Exception):
    """ Thrown if the supplied theme could not be found anywhere """


def load_theme(request, theme_name=None):
    """ Load a theme for this request.

    @param request: moin request
    @param theme_name: the name of the theme
    @type theme_name: str
    @rtype: Theme
    @return: a theme initialized for the request
    """
    if theme_name is None or theme_name == '<default>':
        theme_name = request.cfg.theme_default

    try:
        Theme = wikiutil.importPlugin(request.cfg, 'theme', theme_name, 'Theme')
    except wikiutil.PluginMissingError:
        raise ThemeNotFound(theme_name)

    return Theme(request)


def load_theme_fallback(request, theme_name=None):
    """ Try loading a theme, falling back to defaults on error.

    @param request: moin request
    @param theme_name: the name of the theme
    @type theme_name: str
    @rtype: int
    @return: A status code for how successful the loading was
             0 - theme was loaded
             1 - fallback to default theme
             2 - serious fallback to builtin theme
    """
    fallback = 0
    try:
        request.theme = load_theme(request, theme_name)
    except ThemeNotFound:
        fallback = 1
        try:
            request.theme = load_theme(request, request.cfg.theme_default)
        except ThemeNotFound:
            fallback = 2
            from MoinMoin.theme.modernized import Theme
            request.theme = Theme(request)

