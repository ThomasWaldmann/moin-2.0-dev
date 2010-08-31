# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Theme Package

    @copyright: 2003-2010 MoinMoin:ThomasWaldmann,
                2008 MoinMoin:RadomirDopieralski,
                2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""

import os

from flask import current_app as app
from flask import flaskg
from flask import url_for

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import _, N_
from MoinMoin import i18n, wikiutil, caching, user
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

    def __init__(self):
        """
        Initialize the theme object.
        """
        self.cfg = app.cfg
        self.user = flaskg.user
        self.output_mimetype = 'text/html'  # was: page.output_mimetype
        self.output_charset = 'utf-8'  # was: page.output_charset
        self.ui_lang = 'en'
        self.ui_dir = i18n.getDirection(self.ui_lang)
        self.content_lang = flaskg.content_lang
        self.content_dir = i18n.getDirection(self.content_lang)
        # for html head:
        self.meta_keywords = ''
        self.meta_description = ''

    def item_exists(self, item_name):
        """
        Get a boolean indicating whether an item_name exists or not.

        @param item_name: unicode
        @rtype: boolean
        """
        return flaskg.storage.has_item(item_name)

    def item_readable(self, item_name):
        """
        Get a boolean indicating whether the current user can read in item_name.

        @param item_name: unicode
        @rtype: boolean
        """
        return flaskg.user.may.read(item_name)

    def item_writable(self, item_name):
        """
        Get a boolean indicating whether the current user can write in item_name.

        @param item_name: unicode
        @rtype: boolean
        """
        return flaskg.user.may.write(item_name)

    def translated_item_name(self, item_en):
        """
        Get a translated item name.
        If a translated item exists return its name, if not return item name in English.

        @param item_name: unicode
        @rtype: unicode
        """
        item_lang_request = _(item_en)
        if self.item_exists(item_lang_request):
            return item_lang_request

        item_lang_default = item_en # FIXME, was: i18n.getText(item_en, request, self.cfg.language_default)
        if self.item_exists(item_lang_default):
            return item_lang_default
        return item_en

    def emit_custom_html(self, html):
        """
        Generate custom HTML code in `html`
        @param html: a string or a callable object, in which case
                 it is called and its return value is used
        @rtype: string
        @return: string with html
        """
        if html and callable(html):
            html = html()
        return html

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
        user = self.user
        breadcrumbs = []
        trail = user.getTrail()
        for interwiki_item_name in trail:
            wiki_name, item_name = wikiutil.split_interwiki(interwiki_item_name)
            wiki_name, wiki_base_url, item_name, err = wikiutil.resolve_interwiki(wiki_name, item_name)
            href = wikiutil.join_wiki(wiki_base_url, item_name)
            if wiki_name in [app.cfg.interwikiname, 'Self', ]:
                exists = self.item_exists(item_name)
                wiki_name = ''  # means "this wiki" for the theme code
            else:
                exists = True  # we can't detect existance of remote items
            breadcrumbs.append((wiki_name, item_name, href, exists, err))
        return breadcrumbs

    def userhome(self):
        """
        Assemble arguments used to build user homepage link

        @rtype: tuple
        @return: arguments of user homepage link in tuple (wiki_href, aliasname, title, exists)
        """
        user = self.user

        wikiname, itemname = wikiutil.getInterwikiHomePage()
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
        wiki_name, wiki_base_url, item_name, err = wikiutil.resolve_interwiki(wikiname, itemname)
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
        title = None
        wiki_local = ''  # means local wiki

        # Handle [[pagename|title]] or [[url|title]] formats
        if text.startswith('[[') and text.endswith(']]'):
            text = text[2:-2]
            try:
                target, title = text.split('|', 1)
                target = target.strip()
                title = title.strip()
                localize = 0
            except (ValueError, TypeError):
                # Just use the text as is.
                target = text.strip()
        else:
            target = text

        if wikiutil.is_URL(target):
            if not title:
                title = target
            return target, title, wiki_local

        # remove wiki: url prefix
        if target.startswith("wiki:"):
            target = target[5:]

        # try handling interwiki links
        wiki_name, item_name = wikiutil.split_interwiki(target)
        wiki_name, wiki_base_url, item_name, err = wikiutil.resolve_interwiki(wiki_name, item_name)
        href = wikiutil.join_wiki(wiki_base_url, item_name)
        if wiki_name not in [app.cfg.interwikiname, 'Self', ]:
            if not title:
                title = item_name
            return href, title, wiki_name

        # Handle regular pagename like "FrontPage"
        item_name = wikiutil.normalize_pagename(item_name, app.cfg)

        # Use localized pages for the current user
        if localize:
            item_name = self.translated_item_name(item_name)

        if not title:
            title = item_name
        href = url_for('frontend.show_item', item_name=item_name)
        return href, title, wiki_local

    def navibar(self, item_name):
        """
        Assemble the navibar

        @rtype: list
        @return: list of tuples (css_class, url, link_text, title)
        """
        items = []  # navibar items
        current = item_name

        # Process config navi_bar
        for text in app.cfg.navi_bar:
            url, link_text, title = self.split_navilink(text)
            items.append(('wikilink', url, link_text, title))

        # Add user links to wiki links.
        userlinks = self.user.getQuickLinks()
        for text in userlinks:
            # Split text without localization, user knows what he wants
            url, link_text, title = self.split_navilink(text, localize=0)
            items.append(('userlink', url, link_text, title))

        # Add sister pages.
        for sistername, sisterurl in app.cfg.sistersites:
            if sistername == app.cfg.interwikiname:  # it is THIS wiki
                items.append(('sisterwiki current', sisterurl, sistername))
            else:
                cache = caching.CacheEntry('sisters', sistername, 'farm', use_pickle=True)
                if cache.exists():
                    data = cache.content()
                    sisterpages = data['sisterpages']
                    if current in sisterpages:
                        url = sisterpages[current]
                        items.append(('sisterwiki', url, sistername, ''))
        return items

    def parent_item(self, item_name):
        """
        Return name of parent item for the current item

        @rtype: unicode
        @return: parent item name
        """
        parent_item_name = wikiutil.ParentItemName(item_name)
        if item_name and parent_item_name:
            return parent_item_name

    # TODO: reimplement on-wiki-page sidebar definition with converter2

    # Properties ##############################################################

    def login_url(self):
        """
        Return URL usable for user login

        @rtype: unicode
        @return: url for user login
        """
        url = ''
        if app.cfg.auth_login_inputs == ['special_no_input']:
            url = url_for('frontend.login', login=1)
        if app.cfg.auth_have_login:
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
        menu = [
            # title, internal name, endpoint, disabled
            (_('Global History'), 'global_history', 'frontend.global_history', False, ),
            (_('Global Index'), 'global_index', 'frontend.global_index', False, ),
            # Translation may need longer or shorter separator:
            (_('-----------------------------------'), 'show', 'frontend.show_item', True),
            (_('What links here?'), 'backlinks', 'frontend.backlinks', False, ),
            (_('Local Site Map'), 'sitemap', 'frontend.sitemap', False, ),
            (_('Items with similar names'), 'similar_names', 'frontend.similar_names', False, ),
            (_('-----------------------------------'), 'show', 'frontend.show_item', True),
            (_('Copy Item'), 'copy', 'frontend.copy_item', False, ),
            (_('Rename Item'), 'rename', 'frontend.rename_item', False, ),
            (_('Delete Item'), 'delete', 'frontend.delete_item', False, ),
            (_('Destroy Item'), 'destroy', 'frontend.destroy_item', False, ),
        ]
        return [(title, disabled, endpoint)
                for title, action, endpoint, disabled in menu
                if action not in app.cfg.actions_excluded]

    @property
    def special_item_names(self):
        """
        Return a list of item names for items that are considered "index" items.
        For index items, base.html adds cfg.html_head_index.

        @rtype: list
        @return: list of item names
        """
        return [self.cfg.page_front_page,
                self.translated_item_name(self.cfg.page_front_page)
               ]


class ThemeNotFound(Exception):
    """
    Thrown if the supplied theme could not be found anywhere
    """


def load_theme(theme_name=None):
    """
    Load a theme.

    @param theme_name: the name of the theme
    @type theme_name: str
    @rtype: Theme
    @return: a initialized theme
    """
    if theme_name is None or theme_name == '<default>':
        theme_name = app.cfg.theme_default

    try:
        Theme = wikiutil.importPlugin(app.cfg, 'theme', theme_name, 'Theme')
    except wikiutil.PluginMissingError:
        raise ThemeNotFound(theme_name)

    return Theme()


def load_theme_fallback(theme_name=None):
    """
    Try loading a theme, falling back to defaults on error.

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
        theme = load_theme(theme_name)
    except ThemeNotFound:
        fallback = 1
        try:
            theme = load_theme(app.cfg.theme_default)
        except ThemeNotFound:
            fallback = 2
            from MoinMoin.theme.modernized import Theme
            theme = Theme()
    return theme

