# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Theme Support

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
from MoinMoin import wikiutil, caching, user


class ThemeSupport(object):
    """
    Support code for template feeding.
    """
    # Standard set of style sheets
    stylesheets = (
        # media         basename
        ('all',         'common'),
        ('screen',      'screen'),
        ('print',       'print'),
        ('projection',  'projection'),
        )

    def __init__(self, cfg, name='modernized'):
        self.name = name
        self.cfg = cfg
        self.user = flaskg.user
        self.storage = flaskg.storage
        self.output_mimetype = 'text/html'  # was: page.output_mimetype
        self.output_charset = 'utf-8'  # was: page.output_charset
        self.ui_lang = 'en' # XXX
        self.ui_dir = 'ltr' # XXX
        self.content_lang = flaskg.content_lang # XXX
        self.content_dir = 'ltr' # XXX
        # for html head:
        self.meta_keywords = ''
        self.meta_description = ''

    def translated_item_name(self, item_en):
        """
        Get a translated item name.
        If a translated item exists return its name, if not return item name in English.

        @param item_name: unicode
        @rtype: unicode
        """
        item_lang_request = _(item_en)
        if self.storage.has_item(item_lang_request):
            return item_lang_request

        item_lang_default = item_en # FIXME, was: i18n.getText(item_en, request, self.cfg.language_default)
        if self.storage.has_item(item_lang_default):
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
            breadcrumbs.append((segment, current_item, self.storage.has_item(current_item)))
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
            if wiki_name in [self.cfg.interwikiname, 'Self', ]:
                exists = self.storage.has_item(item_name)
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

        wikiname, itemname = wikiutil.getInterwikiHome()
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
        if wiki_name not in [self.cfg.interwikiname, 'Self', ]:
            if not title:
                title = item_name
            return href, title, wiki_name

        # Handle regular pagename like "FrontPage"
        item_name = wikiutil.normalize_pagename(item_name, self.cfg)

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
        for text in self.cfg.navi_bar:
            url, link_text, title = self.split_navilink(text)
            items.append(('wikilink', url, link_text, title))

        # Add user links to wiki links.
        userlinks = self.user.getQuickLinks()
        for text in userlinks:
            # Split text without localization, user knows what he wants
            url, link_text, title = self.split_navilink(text, localize=0)
            items.append(('userlink', url, link_text, title))

        # Add sister pages.
        for sistername, sisterurl in self.cfg.sistersites:
            if sistername == self.cfg.interwikiname:  # it is THIS wiki
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
        if self.cfg.auth_login_inputs == ['special_no_input']:
            url = url_for('frontend.login', login=1)
        if self.cfg.auth_have_login:
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
                if action not in self.cfg.actions_excluded]

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


def get_editor_info(rev, external=False):
    from MoinMoin.items import EDIT_LOG_USERID, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME
    addr = rev.get(EDIT_LOG_ADDR)
    hostname = rev.get(EDIT_LOG_HOSTNAME)
    text = _('anonymous')  # link text
    title = ''  # link title
    css = 'editor'  # link/span css class
    name = None  # author name
    uri = None  # author homepage uri
    email = None  # pure email address of author
    if app.cfg.show_hosts and addr:
        # only tell ip / hostname if show_hosts is True
        if hostname:
            text = hostname[:15]  # 15 = len(ipaddr)
            name = title = '%s[%s]' % (hostname, addr)
            css = 'editor host'
        else:
            name = text = addr
            title = '[%s]' % (addr, )
            css = 'editor ip'

    userid = rev.get(EDIT_LOG_USERID)
    if userid:
        u = user.User(userid)
        name = u.name
        text = name
        aliasname = u.aliasname
        if not aliasname:
            aliasname = name
        if title:
            # we already have some address info
            title = "%s @ %s" % (aliasname, title)
        else:
            title = aliasname
        if u.mailto_author and u.email:
            email = u.email
            css = 'editor mail'
        else:
            homewiki = app.cfg.user_homewiki
            if homewiki in ('Self', app.cfg.interwikiname):
                homewiki = u'Self'
                css = 'editor homepage local'
                uri = url_for('frontend.show_item', item_name=name, _external=external)
            else:
                css = 'editor homepage interwiki'
                wt, wu, tail, err = wikiutil.resolve_interwiki(homewiki, name)
                uri = wikiutil.join_wiki(wu, tail)

    result = dict(name=name, text=text, css=css, title=title)
    if uri:
        result['uri'] = uri
    if email:
        result['email'] = email
    return result


def shorten_item_name(name, length=25):
    """
    Shorten item names

    Shorten very long item names that tend to break the user
    interface. The short name is usually fine, unless really stupid
    long names are used (WYGIWYD).

    @param name: item name, unicode
    @param length: maximum length for shortened item names, int
    @rtype: unicode
    @return: shortened version.
    """
    # First use only the sub page name, that might be enough
    if len(name) > length:
        name = name.split('/')[-1]
        # If it's not enough, replace the middle with '...'
        if len(name) > length:
            half, left = divmod(length - 3, 2)
            name = u'%s...%s' % (name[:half + left], name[-half:])
    return name


def setup_jinja_env():
    app.jinja_env.filters['datetime_format'] = lambda tm, u = flaskg.user: u.getFormattedDateTime(tm)
    app.jinja_env.filters['date_format'] = lambda tm, u = flaskg.user: u.getFormattedDate(tm)
    app.jinja_env.filters['shorten_item_name'] = shorten_item_name

    theme_name = app.cfg.theme_default if app.cfg.theme_force else flaskg.user.theme_name
    theme = ThemeSupport(app.cfg, theme_name)

    app.jinja_env.globals.update({
                            'isinstance': isinstance,
                            'list': list,
                            'theme': theme,
                            'user': flaskg.user,
                            'storage': flaskg.storage,
                            'clock': flaskg.clock,
                            'cfg': app.cfg,
                            '_': _,
                            'item_name': 'handlers need to give it',
                            'get_editor_info': lambda rev: get_editor_info(rev),
                            })



