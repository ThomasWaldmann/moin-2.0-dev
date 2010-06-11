# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Theme Package

    @copyright: 2003-2009 MoinMoin:ThomasWaldmann,
                2008 MoinMoin:RadomirDopieralski
                2010 MoinMoin:DiogenesAugustoFernandesHerminio
    @license: GNU GPL, see COPYING for details.
"""

import os
import StringIO

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

# Check whether we can emit a RSS feed.
# RSS is broken on plain Python 2.4.x, and works only when installing PyXML.
# A user reported that the RSS is valid when using Python 2.5.1 on Windows.
import sys
import xml
rss_supported = sys.version_info[:3] >= (2, 5, 1) or '_xmlplus' in xml.__file__

from MoinMoin.theme import ThemeBase


class JinjaTheme(ThemeBase):
    """
    Base class for actual themes.
    
    We need to know how the rendering will be done.
    """
    
    def __init__(self, request):
        """
        Initialize the theme object.

        @param request: the request object
        """
        self.request = request
        self.cfg = request.cfg
        self._cache = {} # Used to cache elements that may be used several times
        self._status = []
        self._send_title_called = False

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
                                                                        rev[EDIT_LOG_USERID],
                                                                        rev[EDIT_LOG_ADDR],
                                                                        rev[EDIT_LOG_HOSTNAME])
        self.env.globals.update({'cfg': self.request.cfg, '_': self.request.getText})
        
    def logo(self):
        """
        Assemble logo with link to front page

        The logo contain an image and or text or any html markup the
        admin inserted in the config file. Everything it enclosed inside
        a div with id="logo".

        @rtype: dict
        @return: logo variable
        """
        d = {}
        if self.cfg.logo_string:
            page = wikiutil.getFrontPage(self.request)
            logo = page.link_to_raw(self.request, self.cfg.logo_string)
            d = {'logo': logo}
        return d

    def interwiki(self):
        """
        Assemble the interwiki name display, linking to page_front_page

        @param d: parameter dictionary
        @rtype: dict
        @return: interwiki link
        """
        d = {}
        if self.request.cfg.show_interwiki:
            page = wikiutil.getFrontPage(self.request)
            text = self.request.cfg.interwikiname or 'Self'
            link = page.link_to(self.request, text=text, rel='nofollow')
            d = {'interwiki_link': link}
        return d

    def title(self, d):
        """
        Assemble the title (now using breadcrumbs)

        @param d: parameter dictionary
        @rtype: dict
        @return: title link in dict
        """
        # just showing a page, no action
        segments = d['page_name'].split('/')
        content = []
        curpage = ''
        for s in segments:
            curpage += s
            content.append(Page(self.request,
                                curpage).link_to(self.request, s))
            curpage += '/'
        d.update({'title_content': content})
        return d

    def username(self, d):
        """
        Assemble the username / userprefs link

        @param d: parameter dictionary
        @rtype: unicode
        @return: username html
        """
        request = self.request
        _ = request.getText

        userlinks = []
        # Add username/homepage link for registered users. We don't care
        # if it exists, the user can create it.
        if request.user.valid and request.user.name:
            interwiki = wikiutil.getInterwikiHomePage(request)
            name = request.user.name
            aliasname = request.user.aliasname
            if not aliasname:
                aliasname = name
            title = "%s @ %s" % (aliasname, interwiki[0])
            # link to (interwiki) user homepage
            homelink = (request.formatter.interwikilink(1, title=title, id="userhome", generated=True, *interwiki) +
                request.formatter.text(name) +
                request.formatter.interwikilink(0, title=title, id="userhome", *interwiki))
            userlinks.append(homelink)
            # link to userprefs action
            if 'userprefs' not in self.request.cfg.actions_excluded:
                userlinks.append(d['page'].link_to(request, text=_('Settings'),
                                               querystr={'do': 'userprefs'}, id='userprefs', rel='nofollow'))

        if request.user.valid:
            if request.user.auth_method in request.cfg.auth_can_logout:
                userlinks.append(d['page'].link_to(request, text=_('Logout'),
                                                   querystr={'do': 'logout', 'logout': 'logout'}, id='logout', rel='nofollow'))
        else:
            query = {'do': 'login'}
            # special direct-login link if the auth methods want no input
            if request.cfg.auth_login_inputs == ['special_no_input']:
                query['login'] = '1'
            if request.cfg.auth_have_login:
                userlinks.append(d['page'].link_to(request, text=_("Login"),
                                                   querystr=query, id='login', rel='nofollow'))

        return {'userlinks': userlinks}

    def splitNavilink(self, text, localize=1):
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
        fmt = request.formatter
        title = None

        # Handle [[pagename|title]] or [[url|title]] formats
        if text.startswith('[[') and text.endswith(']]'):
            text = text[2:-2]
            try:
                pagename, title = text.split('|', 1)
                pagename = pagename.strip()
                title = title.strip()
                localize = 0
            except (ValueError, TypeError):
                # Just use the text as is.
                pagename = text.strip()
        else:
            pagename = text

        if wikiutil.is_URL(pagename):
            if not title:
                title = pagename
            link = fmt.url(1, pagename) + fmt.text(title) + fmt.url(0)
            return pagename, link

        # remove wiki: url prefix
        if pagename.startswith("wiki:"):
            pagename = pagename[5:]

        # try handling interwiki links
        try:
            interwiki, page = wikiutil.split_interwiki(pagename)
            thiswiki = request.cfg.interwikiname
            if interwiki == thiswiki or interwiki == 'Self':
                pagename = page
            else:
                if not title:
                    title = page
                link = fmt.interwikilink(True, interwiki, page) + fmt.text(title) + fmt.interwikilink(False, interwiki, page)
                return pagename, link
        except ValueError:
            pass

        # Handle regular pagename like "FrontPage"
        pagename = wikiutil.normalize_pagename(pagename, request.cfg)

        # Use localized pages for the current user
        if localize:
            page = wikiutil.getLocalizedPage(request, pagename)
        else:
            page = Page(request, pagename)

        pagename = page.page_name  # can be different, due to i18n

        if not title:
            title = page.page_name
            title = self.shortenPagename(title)

        link = page.link_to(request, title)

        return pagename, link

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

    maxPagenameLength = 25  # maximum length for shortened page names

    def navibar(self, d):
        """
        Assemble the navibar

        @param d: parameter dictionary
        @rtype: unicode
        @return: navibar html
        """
        request = self.request
        found = {}  # pages we found. prevent duplicates
        items = []  # navibar items
        item = u'<li class="%s">%s</li>'
        current = d['page_name']

        # Process config navi_bar
        if request.cfg.navi_bar:
            for text in request.cfg.navi_bar:
                pagename, link = self.splitNavilink(text)
                if pagename == current:
                    cls = 'wikilink current'
                else:
                    cls = 'wikilink'
                items.append(item % (cls, link))
                found[pagename] = 1

        # Add user links to wiki links, eliminating duplicates.
        userlinks = request.user.getQuickLinks()
        for text in userlinks:
            # Split text without localization, user knows what he wants
            pagename, link = self.splitNavilink(text, localize=0)
            if not pagename in found:
                if pagename == current:
                    cls = 'userlink current'
                else:
                    cls = 'userlink'
                items.append(item % (cls, link))
                found[pagename] = 1

        # Add current page at end of local pages
        if not current in found:
            title = d['page'].page_name
            title = self.shortenPagename(title)
            link = d['page'].link_to(request, title)
            cls = 'current'
            items.append(item % (cls, link))

        # Add sister pages.
        for sistername, sisterurl in request.cfg.sistersites:
            if sistername == request.cfg.interwikiname:  # it is THIS wiki
                cls = 'sisterwiki current'
                items.append(item % (cls, sistername))
            else:
                # TODO optimize performance
                cache = caching.CacheEntry(request, 'sisters', sistername, 'farm', use_pickle=True)
                if cache.exists():
                    data = cache.content()
                    sisterpages = data['sisterpages']
                    if current in sisterpages:
                        cls = 'sisterwiki'
                        url = sisterpages[current]
                        link = request.formatter.url(1, url) + \
                               request.formatter.text(sistername) +\
                               request.formatter.url(0)
                        items.append(item % (cls, link))

        d.update({'navibar_items': items})
        return d

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

        img_url = "%s/%s/img/%s" % (self.cfg.url_prefix_static, self.name, icon)

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

    def msg(self, d):
        """
        Assemble the msg display

        Display a message with a widget or simple strings with a clear message link.

        @param d: parameter dictionary
        @rtype: dict
        @return: dict msg display html
        """
        _ = self.request.getText
        msgs = d['msg']

        result = u""
        close = d['page'].link_to(self.request, text=_('Clear message'), css_class="clear-link")
        for msg, msg_class in msgs:
            try:
                result += u'<p>%s</p>' % msg.render()
                close = ''
            except AttributeError:
                if msg and msg_class:
                    result += u'<p><div class="%s">%s</div></p>' % (msg_class, msg)
                elif msg:
                    result += u'<p>%s</p>\n' % msg
        if result:
            html = result + close
            d.update({'message': html})
        return d

    def trail(self, d):
        """
        Assemble page trail

        @param d: parameter dictionary
        @rtype: unicode
        @return: trail html
        """
        request = self.request
        user = request.user
        if not user.valid or user.show_page_trail:
            trail = user.getTrail()
            if trail:
                items = []
                for pagename in trail:
                    try:
                        interwiki, page = wikiutil.split_interwiki(pagename)
                        if interwiki != request.cfg.interwikiname and interwiki != 'Self':
                            link = (self.request.formatter.interwikilink(True, interwiki, page) +
                                    self.shortenPagename(page) +
                                    self.request.formatter.interwikilink(False, interwiki, page))
                            items.append(link)
                            continue
                        else:
                            pagename = page

                    except ValueError:
                        pass
                    page = Page(request, pagename)
                    title = page.page_name
                    title = self.shortenPagename(title)
                    link = page.link_to(request, title)
                    items.append(link)
                d.update({'trail_items': items})
        return d
     
    def _stylesheet_link(self, theme, media, href, title=None):
        """
        Create a link tag for a stylesheet.

        @param theme: True: href gives the basename of a theme stylesheet,
                      False: href is a full url of a user/admin defined stylesheet.
        @param media: 'all', 'screen', 'print', 'projection', ...
        @param href: see param theme
        @param title: optional title (for alternate stylesheets), see
                      http://www.w3.org/Style/Examples/007/alternatives
        @rtype: tuple
        @return: parameters to render stylesheet in template
        """
        if theme:
            href = '%s/%s/css/%s.css' % (self.cfg.url_prefix_static, self.name, href)
        attrs = 'type="text/css" charset="%s" media="%s" href="%s"' % (
                self.stylesheetsCharset, media, href, )
        return media, href, title

    def stylesheets_list(self, d):
        """ Assemble html head stylesheet links

        @param d: parameter dictionary
        @rtype: list
        @return: list of stylesheets parameters
        """
        request = self.request
        stylesheet_list = []
        # Check mode
        if d.get('print_mode'):
            media = d.get('media', 'print')
            stylesheets = getattr(self, 'stylesheets_' + media)
        else:
            stylesheets = self.stylesheets

        theme_css = [self._stylesheet_link(True, *stylesheet) for stylesheet in stylesheets]
        stylesheet_list.extend(theme_css)
        
        cfg_css = [self._stylesheet_link(False, *stylesheet) for stylesheet in request.cfg.stylesheets]
        stylesheet_list.extend(cfg_css)
        
        # Add user css url (assuming that user css uses same charset)
        href = request.user.valid and request.user.css_url
        if href and href.lower() != "none":
            user_css = self._stylesheet_link(False, 'all', href)
            stylesheet_list.append(user_css)
            
        #MSIE must to be the last add. This is used in for loop in head.html to render specific tags.
        msie_css = self._stylesheet_link(True, 'all', 'msie')
        stylesheet_list.append(msie_css)
        
        return stylesheet_list
            
    def shouldShowPageinfo(self, page):
        """
        Should we show page info?

        Should be implemented by actions. For now, we check here by action
        name and page.

        @param page: current page
        @rtype: bool
        @return: true if should show page info
        """
        if page.exists() and self.request.user.may.read(page.page_name):
            # These actions show the page content.
            # TODO: on new action, page info will not show.
            # A better solution will be if the action itself answer the question: showPageInfo().
            contentActions = [u'', u'show', u'refresh', u'preview', u'diff',
                              u'subscribe', u'rename', u'copy', u'backlink',
                             ]
            return self.request.action in contentActions
        return False

    def pageinfo(self, page):
        """
        Return html fragment with page meta data

        Since page information uses translated text, it uses the ui
        language and direction. It looks strange sometimes, but
        translated text using page direction looks worse.

        @param page: current page
        @rtype: dict
        @return: page last edit information in dict
        """
        _ = self.request.getText
        d = {}
        if self.shouldShowPageinfo(page):
            info = page.last_edit(printable=True)
            if info:
                if info['editor']:
                    info = _("last edited %(timestamp)s by %(editor)s") % info
                else:
                    info = _("last modified %(timestamp)s") % info
                pagename = page.page_name
                if self.request.cfg.show_interwiki:
                    pagename = "%s: %s" % (self.request.cfg.interwikiname, pagename)
                info = "%s  (%s)" % (wikiutil.escape(pagename), info)
                d.update({
                    'pageinfo_lang': self.ui_lang_attr(),
                    'pageinfo': info})
        return d

    def searchform(self, d):
        """
        Assemble HTML code for the search forms

        @param d: parameter dictionary
        @rtype: unicode
        @return: search form html
        """
        form = self.request.values
        d.update({
            'search_value': wikiutil.escape(form.get('value', ''), 1),
            'search_url': self.request.href(d['page'].page_name)})
        return d

    def showversion(self, **keywords):
        """
        Assemble HTML code for copyright and version display

        @param d: parameter dictionary
        @rtype: string
        @return: copyright and version display html
        """
        d = {}
        if self.cfg.show_version and not keywords.get('print_mode', 0):
            d.update({'moin_release': version.release, 'moin_revision': version.revision})
        return d

    def rsslink(self, d):
        """
        Create rss link in head, used by FireFox

        RSS link for FireFox. This shows an rss link in the bottom of
        the page and let you subscribe to the wiki rss feed.

        @rtype: unicode
        @param d: dictionary
        @return: rss link in dict
        """
        request = self.request
        page = d['page']
        url = page.url(request, querystr={
                'do': 'rss_rc', 'ddiffs': '1', 'unique': '1', }, escape=0)
        d.update({'rsslink': url})
        return d


    def externalScript(self, name, attrs=''):
        """
        Format external script html

        @param name: filename
        @rtype: string
        @return: external script link
        """
        jspath = '%s/common/js' % self.request.cfg.url_prefix_local
        attrs = attrs % locals()
        url = "%s/%s.js" % (jspath, name)
        return url, attrs
        
    def universal_edit_button(self, d, **keywords):
        """
        Generate HTML for an edit link in the header.
        """
        page = d['page']
        if 'modify' in self.request.cfg.actions_excluded:
            return d
        may_write = self.request.user.may.write(page.page_name)
        if not (page.exists() and may_write):
            return d  # Why dict?
        _ = self.request.getText
        querystr = {'do': 'modify'}
        # XXX is this actually used?
        text = _(u'Modify') if may_write else _(u'Immutable Page')
        url = page.url(self.request, querystr=querystr, escape=0)
        d.update({'ueb_title': text, 'ueb_url': url})
        return d

    def credits(self, **keywords):
        """
        Create credits html from credits list
        """
        d = {}
        if isinstance(self.cfg.page_credits, (list, tuple)):
            d.update({'new_page_credits': True})
        d.update({'page_credits': self.cfg.page_credits})
        return d

    def actionsMenu(self, page):
        """
        Create actions menu list and items data dict

        The menu will contain the same items always, but items that are
        not available will be disabled (some broken browsers will let
        you select disabled options though).

        The menu should give best user experience for javascript
        enabled browsers, and acceptable behavior for those who prefer
        not to use Javascript.

        TODO: Move actionsMenuInit() into body onload - requires that the theme will render body,
              it is currently done in wikiutil/page.

        @param page: current page, Page object
        @rtype: unicode
        @return: actions menu html fragment
        """
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
        option = '<option value="%(do)s"%(disabled)s>%(title)s</option>'
        # class="disabled" is a workaround for browsers that ignore
        # "disabled", e.g IE, Safari
        # for XHTML: data['disabled'] = ' disabled="disabled"'
        disabled = ' disabled class="disabled"'

        # Format standard actions
        available = actionmod.get_names(request.cfg)
        for action in menu:
            data = {'do': action, 'disabled': '', 'title': titles[action]}
            # removes excluded actions from the more actions menu
            if action in request.cfg.actions_excluded:
                continue

            # Enable delete cache only if page can use caching
            if action == 'refresh':
                if not page.canUseCache():
                    data['do'] = 'show'
                    data['disabled'] = disabled

            # SubscribeUser action enabled only if user has admin rights
            if action == 'SubscribeUser' and not request.user.may.admin(page.page_name):
                data['do'] = 'show'
                data['disabled'] = disabled

            # Special menu items. Without javascript, executing will
            # just return to the page.
            if action.startswith('__'):
                data['do'] = 'show'

            # Actions which are not available for this wiki, user or page
            if (action == '__separator__' or
                (action[0].isupper() and not action in available)):
                data['disabled'] = disabled

            options.append(option % data)

        # Add custom actions not in the standard menu
        more = [item for item in available if not item in titles]
        more.sort()
        if more:
            # Add separator
            separator = option % {'do': 'show', 'disabled': disabled,
                                  'title': titles['__separator__']}
            options.append(separator)
            # Add more actions (all enabled)
            for action in more:
                data = {'do': action, 'disabled': ''}
                # Always add spaces: LikePages -> Like Pages
                # XXX do not create page just for using split_title -
                # creating pages for non-existent does 2 storage lookups
                #title = Page(request, action).split_title(force=1)
                title = action
                # Use translated version if available
                data['title'] = _(title)
                options.append(option % data)

        data = {
            'label': titles['__title__'],
            'options': '\n'.join(options),
            'rev_field': rev is not None and '<input type="hidden" name="rev" value="%d">' % rev or '',
            'do_button': _("Do"),
            'url': self.request.href(page.page_name),
            }
        return self.render('actions_menu.html', data)

    def editbar(self, d):
        """
        Assemble the page edit bar.

        Create html on first call, then return cached html.

        @param d: parameter dictionary
        @rtype: unicode
        @return: iconbar items
        """
        page = d['page']
        if not self.shouldShowEditbar(page):
            return d

        # TODO: Make a new cache for editbar using Jinja
        items = []
        for item in self.editbarItems(page):
            if item:
                items.append(item)
        d.update({'editbar_items': items})
        return d

    def shouldShowEditbar(self, page):
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
        if (page.exists() and self.request.user.may.read(page.page_name)):
            form = self.request.form
            action = self.request.action
            # Do not show editbar on edit but on save/cancel
            return not (action == 'modify' and
                        not form.has_key('button_save') and
                        not form.has_key('button_cancel'))
        return False

    def editbarItems(self, page):
        """
        Return list of items to show on the editbar

        This is separate method to make it easy to customize the
        edtibar in sub classes.
        """
        _ = self.request.getText
        editbar_actions = []
        for editbar_item in self.request.cfg.edit_bar:
            if (editbar_item == 'Discussion' and
               (self.request.getPragma('supplementation-page', self.request.cfg.supplementation_page)
                                                   in (True, 1, 'on', '1'))):
                    editbar_actions.append(self.supplementation_page_nameLink(page))
            elif editbar_item == 'Comments':
                # we just use <a> to get same style as other links, but we add some dummy
                # link target to get correct mouseover pointer appearance. return false
                # keeps the browser away from jumping to the link target::
                editbar_actions.append('<a href="#" class="nbcomment" onClick="toggleComments();return false;">%s</a>' % _('Comments'))
            elif editbar_item == 'Modify':
                editbar_actions.append(self.modifyLink(page))
            elif editbar_item == 'Download':
                editbar_actions.append(self.downloadLink(page))
            elif editbar_item == 'Subscribe':
                editbar_actions.append(self.subscribeLink(page))
            elif editbar_item == 'Quicklink':
                editbar_actions.append(self.quicklinkLink(page))
            elif editbar_item == 'ActionsMenu':
                editbar_actions.append(self.actionsMenu(page))
        return editbar_actions

    def supplementation_page_nameLink(self, page):
        """
        Return a link to the discussion page

        If the discussion page doesn't exist and the user
        has no right to create it, show a disabled link.
        """
        _ = self.request.getText
        suppl_name = self.request.cfg.supplementation_page_name
        suppl_name_full = "%s/%s" % (page.page_name, suppl_name)

        test = Page(self.request, suppl_name_full)
        if not test.exists() and not self.request.user.may.write(suppl_name_full):
            return ('<span class="disabled">%s</span>' % _(suppl_name))
        else:
            return page.link_to(self.request, text=_(suppl_name),
                                querystr={'do': 'supplementation'}, css_class='nbsupplementation', rel='nofollow')

    def modifyLink(self, page):
        """
        Return a link to the modify action
        """
        if 'modify' in self.request.cfg.actions_excluded:
            return ""

        _ = self.request.getText
        querystr = {'do': 'modify'}
        may_write = self.request.user.may.write(page.page_name)
        text = _(u'Modify') if may_write else _(u'Immutable Page')
        attrs = {'rel': 'nofollow', }
        # TODO: Remove link alltogether when item immutable
        return page.link_to(self.request, text=text, querystr=querystr, **attrs)

    def downloadLink(self, page):
        """
        Return a link to the get action
        """
        if 'get' in self.request.cfg.actions_excluded:
            return ""

        _ = self.request.getText
        querystr = {'do': 'get'}
        text = _('Download')
        attrs = {'rel': 'nofollow', }
        return page.link_to(self.request, text=text, querystr=querystr, **attrs)

    def subscribeLink(self, page):
        """
        Return subscribe/unsubscribe link to valid users

        @rtype: unicode
        @return: subscribe or unsubscribe link
        """
        if not ((self.cfg.mail_enabled or self.cfg.jabber_enabled) and self.request.user.valid):
            return ''

        _ = self.request.getText
        if self.request.user.isSubscribedTo([page.page_name]):
            action, text = 'unsubscribe', _("Unsubscribe")
        else:
            action, text = 'subscribe', _("Subscribe")
        if action in self.request.cfg.actions_excluded:
            return ""
        return page.link_to(self.request, text=text, querystr={'do': action}, css_class='nbsubscribe', rel='nofollow')

    def quicklinkLink(self, page):
        """
        Return add/remove quicklink link

        @rtype: unicode
        @return: link to add or remove a quicklink
        """
        if not self.request.user.valid:
            return ''

        _ = self.request.getText
        if self.request.user.isQuickLinkedTo([page.page_name]):
            action, text = 'quickunlink', _("Remove Link")
        else:
            action, text = 'quicklink', _("Add Link")
        if action in self.request.cfg.actions_excluded:
            return ""
        return page.link_to(self.request, text=text, querystr={'do': action}, css_class='nbquicklink', rel='nofollow')

    # Public functions #####################################################

    def header(self, d, **kw):
        """
        Assemble wiki header

        @param d: parameter dictionary
        @rtype: unicode
        @return: page header html
        """

        # Now pass dicts to render('header.html', newdict)
        d.update(self.logo())
        d.update(self.searchform(d))
        d.update(self.username(d))
        d.update(self.interwiki())
        d.update(self.title(d))
        d.update(self.trail(d))
        d.update(self.navibar(d))
        d.update(self.editbar(d))
        d.update(self.msg(d))
        #Language of the page
        d.update({'content_lang': self.content_lang_attr()})
        return self.render('header.html', d)

    def footer(self, d, **keywords):
        """
        Assemble wiki footer

        @param d: parameter dictionary
        @keyword ...:...
        @rtype: unicode
        @return: page footer html
        """
        page = d['page']
        d.update(self.showversion(**keywords))
        d.update(self.credits())
        d.update(self.pageinfo(page))
        return self.render('footer.html', d)

    # Language stuff ####################################################

    def ui_lang_attr(self):
        """
        Generate language attributes for user interface elements

        User interface elements use the user language (if any), kept in
        request.lang.

        @rtype: string
        @return: lang and dir html attributes
        """
        lang = self.request.lang
        return ' lang="%s" dir="%s"' % (lang, i18n.getDirection(lang))

    def content_lang_attr(self):
        """
        Generate language attributes for wiki page content

        Page content uses the page language or the wiki default language.

        @rtype: string
        @return: lang and dir html attributes
        """
        lang = self.request.content_lang
        return ' lang="%s" dir="%s"' % (lang, i18n.getDirection(lang))

    def add_msg(self, msg, msg_class=None):
        """
        Adds a message to a list which will be used to generate status
        information.

        @param msg: additional message
        @param msg_class: html class for the div of the additional message.
        """
        if not msg_class:
            msg_class = 'dialog'
        if self._send_title_called:
            import traceback
            logging.warning("Calling add_msg() after send_title(): no message can be added.")
            logging.info('\n'.join(['Call stack for add_msg():'] + traceback.format_stack()))

            return
        self._status.append((msg, msg_class))

    # stuff from wikiutil.py
    def send_title(self, text, **keywords):
        """
        Output the page header (and title).

        @param text: the title text
        @keyword page: the page instance that called us - using this is more efficient than using pagename..
        @keyword pagename: 'PageName'
        @keyword print_mode: 1 (or 0)
        @keyword media: css media type, defaults to 'screen'
        @keyword allow_doubleclick: 1 (or 0)
        @keyword html_head: additional <head> code
        @keyword body_attr: additional <body> attributes
        @keyword body_onload: additional "onload" JavaScript code
        """
        request = self.request
        _ = request.getText
        rev = request.rev

        if keywords.has_key('page'):
            page = keywords['page']
            pagename = page.page_name
        else:
            pagename = keywords.get('pagename', '')
            page = Page(request, pagename)
        if keywords.get('msg', ''):
            raise DeprecationWarning("Using send_page(msg=) is deprecated! Use theme.add_msg() instead!")
        scriptname = request.script_root

        # Search_hint is moved from self.headscript() to here
        d = {'page': page, 'language': self.ui_lang_attr(), 'search_hint': _('Search')}

        # get name of system pages
        page_front_page = wikiutil.getFrontPage(request).page_name
        page_help_contents = wikiutil.getLocalizedPage(request, 'HelpContents').page_name
        page_title_index = wikiutil.getLocalizedPage(request, 'TitleIndex').page_name
        page_site_navigation = wikiutil.getLocalizedPage(request, 'SiteNavigation').page_name
        page_word_index = wikiutil.getLocalizedPage(request, 'WordIndex').page_name
        page_help_formatting = wikiutil.getLocalizedPage(request, 'HelpOnFormatting').page_name
        page_find_page = wikiutil.getLocalizedPage(request, 'FindPage').page_name
        home_page = wikiutil.getInterwikiHomePage(request)  # sorry theme API change!!! Either None or tuple (wikiname,pagename) now.
        page_parent_page = getattr(page.getParentPage(), 'page_name', None)

        # Prepare the HTML <head> element
        user_head = [request.cfg.html_head]

        meta_keywords = request.getPragma('keywords')
        meta_desc = request.getPragma('description')
        if meta_keywords:
            d.update({'meta_keywords': wikiutil.escape(meta_keywords, 1)})
        if meta_desc:
            d.update({'meta_description': wikiutil.escape(meta_desc, 1)})

        #  add meta statement if user has doubleclick on edit turned on or it is default
        if (pagename and keywords.get('allow_doubleclick', 0) and
            not keywords.get('print_mode', 0) and
            request.user.edit_on_doubleclick):
            if request.user.may.write(pagename):  # separating this gains speed
                user_head.append('<meta name="edit_on_doubleclick" content="1">\n')

        # search engine precautions / optimization:
        # if it is an action or edit/search, send query headers (noindex,nofollow):
        if request.query_string:
            user_head.append(request.cfg.html_head_queries)
        elif request.method == 'POST':
            user_head.append(request.cfg.html_head_posts)
        # we don't want to have BadContent stuff indexed:
        elif pagename in ['BadContent', 'LocalBadContent', ]:
            user_head.append(request.cfg.html_head_posts)
        # if it is a special page, index it and follow the links - we do it
        # for the original, English pages as well as for (the possibly
        # modified) frontpage:
        elif pagename in [page_front_page, request.cfg.page_front_page,
                          page_title_index, 'TitleIndex',
                          page_find_page, 'FindPage',
                          page_site_navigation, 'SiteNavigation',
                         ]:
            user_head.append(request.cfg.html_head_index)
        # if it is a normal page, index it, but do not follow the links, because
        # there are a lot of illegal links (like actions) or duplicates:
        else:
            user_head.append(request.cfg.html_head_normal)

        if 'pi_refresh' in keywords and keywords['pi_refresh']:
            user_head.append('<meta http-equiv="refresh" content="%d;URL=%s">' % keywords['pi_refresh'])

        print_mode = keywords.get('print_mode', False)

        d.update({'user_head': user_head, 'html_head_keyword': keywords.get('html_head', '')})
        #Variables used to render title
        d.update({'title': text, 'sitename': request.cfg.html_pagetitle or request.cfg.sitename})

        #Variables used to render rsslink
        d.update(self.rsslink(d))

        # Links
        if pagename and page_parent_page:
            d.update({'link_parent': request.href(page_parent_page)})

        d.update({
            'link_search': request.href(page_find_page),
            'link_index': request.href(page_title_index),
            'link_glossary': request.href(page_word_index),
            'link_help': request.href(page_help_formatting),
            'link_start': request.href(page_front_page),
        })
        
        #Using to render stylesheet acording to theme
        d.update({'theme_name': self.name})
        if print_mode:
             d.update({'theme_stylesheets': self.stylesheets_print})
        else:
            d.update({'theme_stylesheets': self.stylesheets})
        
        user_css_href = request.user.valid and request.user.css_url
        if user_css_href and href.lower() != "none":
            d.update({'user_css': user_css_href})
        
        # Listing stylesheets
        d.update({'stylesheets': self.stylesheets_list(d)})
        
        # Listing externalScripts
        external_scripts = [
                            self.externalScript('svg', 'data-path="%(jspath)s"'),
                            self.externalScript('common'),
                            ]
        d.update({'external_scripts': external_scripts})
        
        d.update(self.universal_edit_button(d))
        # Render with Jinja
        request.write(self.render('head.html', d))

        #Preparing header
        output = []
        d = {}

        # start the <body>
        bodyattr = []
        if keywords.has_key('body_attr'):
            bodyattr.append(' ')
            bodyattr.append(keywords['body_attr'])

        # Output -----------------------------------------------------------

        d = {}
        
        # Set body to the user interface language and direction
        bodyattr.append(' %s' % self.ui_lang_attr())

        body_onload = keywords.get('body_onload', '')
        if body_onload:
            d.update({'body_onload': body_onload})
        d.update({'body_attr': ''.join(bodyattr)})
        
        # If in print mode, start page div and emit the title
        # TODO: Fix the print mode
        if keywords.get('print_mode', 0):
            d.update({
                'title_text': text,
                'page': page,
                'page_name': pagename or '',
                'rev': rev,
            })
            request.themedict = d
            #Adapt to new methods
            output.append(self.startPage())
            output.append(self.interwiki())
            output.append(self.title(d))

        # In standard mode, emit theme.header
        else:
            exists = pagename and page.exists()
            # prepare dict for theme code:
            d.update({
                'theme': self.name,
                'Theme': self,
                'script_name': scriptname,
                'title_text': text,
                'logo_string': request.cfg.logo_string,
                'site_name': request.cfg.sitename,
                'page': page,
                'rev': rev,
                'pagesize': pagename and page.size() or 0,
                # exists checked to avoid creation of empty edit-log for non-existing pages
                'last_edit_info': exists and page.last_edit_info() or '',
                'page_name': pagename or '',
                'page_find_page': page_find_page,
                'page_front_page': page_front_page,
                'home_page': home_page,
                'page_help_contents': page_help_contents,
                'page_help_formatting': page_help_formatting,
                'page_parent_page': page_parent_page,
                'page_title_index': page_title_index,
                'page_word_index': page_word_index,
                'user_name': request.user.name,
                'user_valid': request.user.valid,
                'msg': self._status,
                'trail': keywords.get('trail', None),
            })

            # add quoted versions of pagenames
            newdict = {}
            for key in d:
                if key.startswith('page_'):
                    if not d[key] is None:
                        newdict['q_' + key] = wikiutil.quoteWikinameURL(d[key])
                    else:
                        newdict['q_' + key] = None
            d.update(newdict)
            request.themedict = d

            # now call the theming code to do the rendering
            output.append(self.header(d))

        # emit it
        request.write(''.join(output))
        output = []
        self._send_title_called = True

    def send_footer(self, pagename, **keywords):
        """
        Output the page footer.

        @param pagename: WikiName of the page
        @keyword print_mode: true, when page is displayed in Print mode
        """
        request = self.request
        d = request.themedict

        # Emit end of page in print mode, or complete footer in standard mode
        if keywords.get('print_mode', 0):
            request.write(self.pageinfo(d['page']))
            request.write(self.endPage())
        else:
            request.write(self.footer(d, **keywords))

    # stuff moved from request.py
    def send_closing_html(self):
        """
        Generate timing info html and closing html tag,
        everyone calling send_title must call this at the end to close
        the body and html tags.
        """
        request = self.request

        # as this is the last chance to emit some html, we stop the clocks:
        request.clock.stop('run')
        request.clock.stop('total')

        # Close html code
        if request.cfg.show_timings:
            request.write('<ul id="timings">\n')
            for t in request.clock.dump():
                request.write('<li>%s</li>\n' % t)
            request.write('</ul>\n')
        #request.write('<!-- auth_method == %s -->' % repr(request.user.auth_method))

    def render_content(self, item_name, content=None, title=None):
        """
        Render some content plus Theme header/footer.
        If content is None, the normal Item content for item_name will be rendered.
        """
        request = self.request
        if content is None:
            item = Item.create(request, item_name)
            content = item.do_show()
        if title is None:
            title = item_name
        if getattr(request.cfg, 'templating', False):
            template = self.env.get_template('base.html')
            html = template.render(gettext=self.request.getText,
                                   item_name=item_name,
                                   title=title,
                                   content=content,
                                  )
            request.write(html)
        else:
            request.headers.add('Content-Type', 'text/html; charset=utf-8')
            # Use user interface language for this generated page
            request.setContentLanguage(request.lang)
            request.theme.send_title(title, pagename=item_name)
            request.write(content)
            request.theme.send_footer(item_name)
            request.theme.send_closing_html()

    def sidebar(self, d, **keywords):
        """
        Display page called SideBar as an additional element on every page

        @param d: parameter dictionary
        @rtype: string
        @return: sidebar html
        """
        # Check which page to display, return nothing if doesn't exist.
        sidebar = self.request.getPragma('sidebar', u'SideBar')
        page = Page(self.request, sidebar)
        if not page.exists():
            return u""
        # Capture the page's generated HTML in a buffer.
        buffer = StringIO.StringIO()
        self.request.redirect(buffer)
        try:
            page.send_page(content_only=1, content_id="sidebar")
        finally:
            self.request.redirect()
        return u'<div class="sidebar">%s</div>' % buffer.getvalue()

    def render(self, filename, context={}):
        """
        Base function that renders using Jinja2.

        @param filename: name of the template will be render.
        @param context: used to passes variables to template.
        @return: template rendered by jinja2
        """
        template = self.env.get_template(filename)
        return template.render(**context)


class ThemeNotFound(Exception):
    """
    Thrown if the supplied theme could not be found anywhere
    """


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
    @return: A statuscode for how successful the loading was
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
