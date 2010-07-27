# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Theme Package

    @copyright: 2003-2010 MoinMoin:ThomasWaldmann,
                2008 MoinMoin:RadomirDopieralski,
                2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""

import os

from flask import flash, url_for, render_template

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import i18n, wikiutil, caching, user
from MoinMoin import action as actionmod
from MoinMoin.items import Item
from MoinMoin.util import pysupport

modules = pysupport.getPackageModules(__file__)


class ThemeBase(object):
    """
    Base class for themes

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

    def __init__(self, request):
        """
        Initialize the theme object.

        @param request: the request object
        """
        self.request = request
        self.cfg = request.cfg
        self.user = request.user
        self.storage = request.storage
        self.output_mimetype = 'text/html' # was: page.output_mimetype
        self.output_charset = 'utf-8' # was: page.output_charset
        self.ui_lang = request.lang
        self.ui_dir = i18n.getDirection(self.ui_lang)
        self.content_lang = request.content_lang
        self.content_dir = i18n.getDirection(self.content_lang)
        self.msg_list = []
        # for html head:
        self.meta_keywords = ''
        self.meta_description = ''

    def item_exists(self, item_name):
        return self.storage.has_item(item_name)

    def item_readable(self, item_name):
        return self.request.user.may.read(item_name)

    def item_writable(self, item_name):
        return self.request.user.may.write(item_name)

    def translated_item_name(self, item_en):
        """
        Get a translated item name.
        If a translated item exists return its name, if not return item name in English.

        @param item_name: string
        @rtype: string
        """
        request = self.request
        item_lang_request = request.getText(item_en)
        if self.item_exists(item_lang_request):
            return item_lang_request

        item_lang_default = i18n.getText(item_en, request, self.cfg.language_default)
        if self.item_exists(item_lang_default):
            return item_lang_default
        return item_en

    def location_breadcrumbs(self, item_name):
        """
        Assemble the location using breadcrumbs (was: title)

        @rtype: list
        @return: location breadcrumbs items in tuple (segment_name, item_name, exists)
        """
        breadcrumbs = []
        current_item = ''
        for segment in item_name.split('/'):
            current_item += segment
            breadcrumbs.append((segment, current_item, self.item_exists(current_item)))
            current_item += '/'
        return breadcrumbs

    def path_breadcrumbs(self):
        """
        Assemble the path breadcrumbs (a.k.a.: trail)

        @rtype: list
        @return: path breadcrumbs items in tuple (wiki_name, item_name, url, exists, err)
        """
        request = self.request
        user = self.user
        breadcrumbs = []
        if not user.valid or user.show_trail:
            trail = user.getTrail()
            if trail:
                for interwiki_item_name in trail:
                    wiki_name, item_name = wikiutil.split_interwiki(interwiki_item_name)
                    wiki_name, wiki_base_url, item_name, err = wikiutil.resolve_interwiki(request, wiki_name, item_name)
                    href = wikiutil.join_wiki(wiki_base_url, item_name)
                    if wiki_name in [request.cfg.interwikiname, 'Self', ]:
                        exists = self.item_exists(item_name)
                        wiki_name = ''  # means "this wiki" for the theme code
                    else:
                        exists = True  # we can't detect existance of remote items
                    breadcrumbs.append((wiki_name, item_name, href, exists, err))
        return breadcrumbs

    def userhome(self):
        """
        Return a tuple (url, aliasname, title, exists) that is used by theme
        to render the user homepage link.
        """
        user = self.user
        request = self.request

        wikiname, itemname = wikiutil.getInterwikiHomePage(request)
        name = user.name
        aliasname = user.aliasname
        if not aliasname:
            aliasname = name
        title = "%s @ %s" % (aliasname, wikiname)
        # link to (interwiki) user homepage
        if wikiname == "Self":
            exists = self.item_exists(itemname)
        else:
            # We cannot check if wiki pages exists in remote wikis
            exists = True
        wiki_name, item_name = wikiutil.split_interwiki(itemname)
        wiki_name, wiki_base_url, item_name, err = wikiutil.resolve_interwiki(request, wiki_name, item_name)
        wiki_href = wikiutil.join_wiki(wiki_base_url, item_name)
        return wiki_href, aliasname, title, exists

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
        wiki_local = ''  # means local wiki

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
            return url, title, wiki_local

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
            return href, title, wiki_name

        # Handle regular pagename like "FrontPage"
        item_name = wikiutil.normalize_pagename(item_name, request.cfg)

        # Use localized pages for the current user
        if localize:
            item_name = self.translated_item_name(item_name)

        if not title:
            title = item_name
        return item_name, title, wiki_local

    def navibar(self, item_name):
        """
        Assemble the navibar

        @rtype: list
        @return: list of tuples (css_class, url, link_text, title)
        """
        request = self.request
        items = []  # navibar items
        current = item_name

        # Process config navi_bar
        for text in request.cfg.navi_bar:
            url, link_text, title = self.split_navilink(text)
            items.append(('wikilink', url, link_text, title))

        # Add user links to wiki links.
        userlinks = self.user.getQuickLinks()
        for text in userlinks:
            # Split text without localization, user knows what he wants
            url, link_text, title = self.split_navilink(text, localize=0)
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

        img_url = url_for('static', filename='%s/img/%s' % (self.name, icon))
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

    def shouldShowEditbar(self, item_name):
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
        if self.item_exists(item_name) and self.item_readable(item_name):
            form = self.request.form
            action = self.request.action
            # Do not show editbar on edit but on save/cancel
            return not (action == 'modify' and
                        not form.has_key('button_save') and
                        not form.has_key('button_cancel'))
        return False

    def parent_page(self, item_name):
        """
        Return name of parent page for the current page

        @rtype: unicode
        @return: parent page name
        """
        parent_page_name = wikiutil.ParentPageName(item_name)
        if item_name and parent_page_name:
            return parent_page_name

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
            self.msg_list.append(msg)
        except AttributeError:
            flash(msg, msg_class)

    # TODO: reimplement on-wiki-page sidebar definition with converter2

    # Properties ##############################################################

    def login_url(self, item_name):
        """
        Return URL usable for user login
        """
        request = self.request
        href = request.href
        url = ''
        if request.cfg.auth_login_inputs == ['special_no_input']:
            url = url_for('frontend.login', login=1)
        if request.cfg.auth_have_login:
            url = url or url_for('frontend.login')
        return url

    def actions_menu_options(self, item_name):
        """
        Create actions menu list and items data dict

        The menu will contain the same items always, but items that are
        not available will be disabled (some broken browsers will let
        you select disabled options though).

        The menu should give best user experience for javascript
        enabled browsers, and acceptable behavior for those who prefer
        not to use Javascript.

        @rtype: list
        @return: options of actions menu
        """
        request = self.request
        _ = request.getText

        menu = [
            # XXX currently everything is dispatching to frontend.show_item,
            # fix this as soon we have the right methods there:
            # title, internal name, disabled
            (_('Global History'), 'global_history', 'frontend.global_history', False, ),
            (_('Global Index'), 'global_index', 'frontend.global_index', False, ),
            # Translation may need longer or shorter separator:
            (_('------------------------'), 'show', 'frontend.show_item', True),
            (_('What links here?'), 'backlinks', 'frontend.backlinks', False, ),
            (_('Copy Item'), 'copy', 'frontend.copy_item', False, ),
            (_('Rename Item'), 'rename', 'frontend.rename_item', False, ),
            (_('Delete Item'), 'delete', 'frontend.delete_item', False, ),
            (_('Destroy Item'), 'destroy', 'frontend.destroy_item', False, ),
        ]
        options = []
        for title, action, endpoint, disabled in menu:
            # removes excluded actions from the more actions menu
            if action in request.cfg.actions_excluded:
                continue
            options.append((title, disabled, endpoint))
        return options

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

    def send_title(self, text, **keywords):
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
        # TODO: get rid of this
        if keywords.get('msg', ''):
            raise DeprecationWarning("Using send_page(msg=) is deprecated! Use theme.add_msg() instead!")
        self.request.write(self.render('show.html'))

    def render(self, name='layout.html', **context):
        # TODO: get rid of all calls to this, call render_template of flask directly
        return render_template(name, **context)


class ThemeNotFound(Exception):
    """ Thrown if the supplied theme could not be found anywhere """


def load_theme(request, theme_name=None):
    """
    Load a theme for this request.

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
    """
    Try loading a theme, falling back to defaults on error.

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

