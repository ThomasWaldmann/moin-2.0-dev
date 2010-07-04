# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Theme Package

    @copyright: 2003-2009 MoinMoin:ThomasWaldmann,
                2008 MoinMoin:RadomirDopieralski
                2010 MoinMoin:DiogenesAugustoFernandesHerminio
    @license: GNU GPL, see COPYING for details.
"""

import os
from jinja2 import Environment, FileSystemLoader, FileSystemBytecodeCache

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import i18n, wikiutil, caching, user
from MoinMoin import action as actionmod
from MoinMoin.items import Item
from MoinMoin.Page import Page
from MoinMoin.items import EDIT_LOG_USERID, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME

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
        self.ui_lang = self.request.lang
        self.ui_dir = i18n.getDirection(self.ui_lang)
        self.content_lang = self.request.content_lang
        self.content_dir = i18n.getDirection(self.content_lang)
        self._cache = {} # Used to cache elements that may be used several times
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
                                                                        rev[EDIT_LOG_USERID],
                                                                        rev[EDIT_LOG_ADDR],
                                                                        rev[EDIT_LOG_HOSTNAME])
        self.env.globals.update({
                                'theme': self,
                                'cfg': self.request.cfg,
                                '_': self.request.getText,
                                'href': request.href,
                                'static_href': self.request.static_href,
                                'abs_href': request.abs_href,
                                'translated_item_name': self.translated_item_name
                                })
    
    def translated_item_name(self, item_en):
        """
        Get a translated Item Name.
        If page exists return it, if not return item_name in English.
        @param item_name: string
        @rtype: string
        """
        # TODO: Convert to ITEM! TOP-PRIORITY
        request = self.request
        item_lang_request= request.getText(item_en)
        page = wikiutil.getLocalizedPage(request, item_lang_request)
        if page.exists():
            return item_lang_request
            
        item_lang_default = i18n.getText(item_en, request, self.cfg.language_default)
        page = wikiutil.getLocalizedPage(request, item_lang_default)
        if page.exists():
            return item_lang_default
            
        return item_en
    
    def link_to(self, pagename, text, querystr=None, css_id=None, css_class=None, rel=None):
        """
        Small wrapper to replace page.link_to
        @param pagename: name of the page
        @param text: text linked
        @param querystr: add querystring to url
        @param css_id: id of 'a' tag
        @param css_id: class of 'a' tag
        @param rel: rel of 'a' tag
        @rtype: string
        @return: link html
        """
        # I'm using page_name instead of page in parameter thinking in future, when we gonna drop Page.
        page = Page(self.request, pagename)
        link = '<a '
        if css_class:
            link += 'class="%s" ' % css_class
        elif not page.exists():
            link += 'class="nonexistent" '
        if css_id:
            link += 'id="%s" ' % css_id     
        if rel:
            link += 'rel="%s" ' % rel
        
        link +='href="'
        url = '%s' % (self.request.href(pagename))
        if querystr:
            url += '?'
            query = []
            for key in querystr.iterkeys():
                query.append('%s=%s' % (key, querystr[key]))
            url += '&'.join(query)
        link += '%s">%s</a>' % (wikiutil.escape(url, 0), text)
        return link
        
    def title(self):
        """
        Assemble the title (now using breadcrumbs)

        @param page_name: name of the page
        @rtype: string
        @return: title
        """
        # just showing a page, no action
        page_name = self.page.page_name
        segments = page_name.split('/')
        content = []
        curpage = ''
        for s in segments:
            curpage += s
            link = self.link_to(pagename=curpage, text=s)   
            content.append(link)
            curpage += '/'
        return content

    def username(self):
        """
        Assemble the username / userprefs link

        @param d: parameter dictionary
        @rtype: unicode
        @return: username
        """
        request = self.request
        _ = request.getText
        page = self.page
        
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
                userlinks.append(self.link_to(pagename=page.page_name, text=_('Settings'),
                                               querystr={'do': 'userprefs'}, css_id='userprefs', rel='nofollow'))

        if request.user.valid:
            if request.user.auth_method in request.cfg.auth_can_logout:
                userlinks.append(self.link_to(pagename=page.page_name, text=_('Logout'),
                                                   querystr={'do': 'logout', 'logout': 'logout'}, css_id='logout', rel='nofollow'))
        else:
            query = {'do': 'login'}
            # special direct-login link if the auth methods want no input
            if request.cfg.auth_login_inputs == ['special_no_input']:
                query['login'] = '1'
            if request.cfg.auth_have_login:
                userlinks.append(self.link_to(pagename=page.page_name, text=_("Login"),
                                                   querystr=query, css_id='login', rel='nofollow'))

        return userlinks

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

        link = self.request.href(page.page_name)
        return pagename, link, title

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

    def navibar(self):
        """
        Assemble the navibar

        @param d: parameter dictionary
        @rtype: unicode
        @return: navibar html
        """
        request = self.request
        items = []  # navibar items
        current = self.page_name

        # Process config navi_bar
        # TODO: Optimize performance and caching with Jinja
        for text in request.cfg.navi_bar:
            pagename, url, link_text = self.splitNavilink(text)
            items.append(('wikilink', url, link_text))

        # Add user links to wiki links.
        userlinks = request.user.getQuickLinks()
        for text in userlinks:
            # Split text without localization, user knows what he wants
            pagename, url, link_text = self.splitNavilink(text, localize=0)
            items.append(('userlink', url, link_text))

        # Add sister pages.
        for sistername, sisterurl in request.cfg.sistersites:
            if sistername == request.cfg.interwikiname:  # it is THIS wiki
                items.append(('sisterwiki current', sisterurl, sistername))
            else:
                # TODO optimize performance
                cache = caching.CacheEntry(request, 'sisters', sistername, 'farm', use_pickle=True)
                if cache.exists():
                    data = cache.content()
                    sisterpages = data['sisterpages']
                    if current in sisterpages:
                        url = sisterpages[current]
                        items.append(('sisterwiki', url, sistername))
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

    def trail(self):
        """
        Assemble page trail

        @param d: parameter dictionary
        @rtype: unicode
        @return: trail items
        """
        request = self.request
        user = request.user
        if not user.valid or user.show_trail:
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
                    link = self.link_to(pagename=page.page_name, text=title)
                    items.append(link)
                return items
        return []
     
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
            href = self.request.static_href(self.name, 'css', '%s.css' % href)
        attrs = 'type="text/css" charset="%s" media="%s" href="%s"' % (
                self.stylesheetsCharset, media, href, )
        return media, href, title

    def stylesheets_list(self):
        """ Assemble html head stylesheet links

        @param d: parameter dictionary
        @rtype: list
        @return: list of stylesheets parameters
        """
        request = self.request
        stylesheet_list = []
        # Check mode
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
            
    def shouldShowPageInfo(self):
        """
        Should we show page info?

        Should be implemented by actions. For now, we check here by action
        name and page.

        @param page: current page
        @rtype: bool
        @return: true if should show page info
        """
        page = self.page
        if page.exists() and self.request.user.may.read(page.page_name):
            # These actions show the page content.
            # TODO: on new action, page info will not show.
            # A better solution will be if the action itself answer the question: showPageInfo().
            contentActions = [u'', u'show', u'refresh', u'preview', u'diff',
                              u'subscribe', u'rename', u'copy', u'backlink',
                             ]
            return self.request.action in contentActions
        return False

    def pageinfo(self):
        """
        Return info with page meta data

        Since page information uses translated text, it uses the ui
        language and direction. It looks strange sometimes, but
        translated text using page direction looks worse.

        @param page: current page
        @rtype: string
        @return: page last edit information
        """
        _ = self.request.getText
        page = self.page

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
                return info
        return ''
            
    def universal_edit_button(self):
        """
        Should we show an edit link in the header?
        User have permission? If yes, show the universal edit button.
        @rtype: boolean
        """
        page = self.page
        can_modify = 'modify' not in self.request.cfg.actions_excluded
        may_write = self.request.user.may.write(page.page_name)
        return can_modify and page.exists() and may_write

    def actionsMenu(self):
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
        page = self.page
        
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
        page = self.page
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

    def parent_page(self):
        """
        Return an url to parent page for the current page
        @rtype: unicode
        @return: url to parent page
        """
        pagename = self.page.page_name
        page_parent_page = getattr(self.page.getParentPage(), 'page_name', None)
        if pagename and page_parent_page:
            return page_parent_page

    def link_supplementation_page(self):
        """
        If the discussion page doesn't exist and the user
        has no right to create it, show a disabled link.
        
        @rtype: bool
        """
        suppl_name = self.request.cfg.supplementation_page_name
        suppl_name_full = "%s/%s" % (self.page_name, suppl_name)

        test = Page(self.request, suppl_name_full)
        return test.exists() or self.request.user.may.write(suppl_name_full)

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

    # Properties ##############################################################
    
    @property
    def special_pagenames(self):
        page_front_page = self.translated_item_name(self.cfg.page_front_page)
        page_help_contents = self.translated_item_name('HelpContents')
        page_title_index = self.translated_item_name('TitleIndex')
        page_site_navigation = self.translated_item_name('SiteNavigation')
        page_word_index = self.translated_item_name('WordIndex')
        page_find_page =  self.translated_item_name('FindPage')
        return [page_front_page, self.request.cfg.page_front_page,
                page_title_index, 'TitleIndex',
                page_find_page, 'FindPage',
                page_site_navigation, 'SiteNavigation',
               ]
               
    # Public Functions ########################################################
    
    def send_title(self, text, content, **keywords):
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
        self.page_name = page.page_name or ''
        self.head_title = text
        
        d = {'page': page}
        # Prepare the HTML <head> element
        user_head = []

        #  add meta statement if user has doubleclick on edit turned on or it is default
        if (pagename and keywords.get('allow_doubleclick', 0) and
            request.user.edit_on_doubleclick):
            if request.user.may.write(pagename):  # separating this gains speed
                user_head.append('<meta name="edit_on_doubleclick" content="1">\n')

        if 'pi_refresh' in keywords and keywords['pi_refresh']:
            user_head.append('<meta http-equiv="refresh" content="%d;URL=%s">' % keywords['pi_refresh'])

        d.update({
                 'user_head': user_head,
                 'html_head_keyword': keywords.get('html_head', ''),
                  })

        user_css_href = request.user.valid and request.user.css_url
        if user_css_href and user_css_href.lower() != "none":
            d.update({'user_css': user_css_href})
        
        # Render with Jinja
        request.write(self.render('head.html', d))

        # now call the theming code to do the rendering
        request.write(self.render('header.html', d))
        request.write(content)
        request.write(self.render('footer.html', d))

    def render_content(self, item_name, content=None, title=None, page=None, pagename=None, allow_doubleclick=None, pi_refresh=None, html_head=None, trail=None):
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
            return
        request.headers.add('Content-Type', 'text/html; charset=utf-8')
        # Use user interface language for this generated page
        request.setContentLanguage(request.lang)
        request.theme.send_title(title, pagename=item_name, content=content)

    #TODO: reimplement on-wiki-page sidebar definition with converter2
    
    def render(self, filename, context):
        """
        Base function that renders using Jinja2.

        @param filename: name of the template will be render.
        @param context: used to passes variables to template.
        @return: template rendered by jinja2
        """
        template = self.env.get_template(filename)
        return template.render(**context)
