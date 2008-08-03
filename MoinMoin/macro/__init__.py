# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Macro Implementation

    These macros are used by the wiki parser module to implement complex
    and/or dynamic page content.

    The canonical interface to plugin macros is their execute() function,
    which gets passed an instance of the Macro class. Such an instance
    has the four members parser, formatter, form and request.

    Using "form" directly is deprecated and should be replaced by "request.form".

    @copyright: 2000-2004 Juergen Hermann <jh@web.de>,
                2006-2007 MoinMoin:ThomasWaldmann,
                2007 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.util import pysupport
modules = pysupport.getPackageModules(__file__)

import re, time, os
from MoinMoin import action, config, util
from MoinMoin import wikiutil, i18n
from MoinMoin.Page import Page


names = ["TitleSearch", "WordIndex", "TitleIndex",
         # Macros with arguments
         "Icon",
]

#############################################################################
### Helpers
#############################################################################

def getNames(cfg):
    if not hasattr(cfg.cache, 'macro_names'):
        lnames = names[:]
        lnames.extend(i18n.wikiLanguages().keys())
        lnames.extend(wikiutil.getPlugins('macro', cfg))
        cfg.cache.macro_names = lnames # remember it
    return cfg.cache.macro_names


#############################################################################
### Macros - Handlers for <<macroname>> markup
#############################################################################

class Macro:
    """ Macro handler

    There are three kinds of macros:
     * Builtin Macros - implemented in this file and named macro_[name]
     * Language Pseudo Macros - any lang the wiki knows can be use as
       macro and is implemented here by _m_lang()
     * External macros - implemented in either MoinMoin.macro package, or
       in the specific wiki instance in the plugin/macro directory
    """
    defaultDependency = ["time"]

    Dependencies = {
        "TitleSearch": ["namespace"],
        "WordIndex": ["namespace"],
        "TitleIndex": ["namespace"],
        "Icon": ["user"], # users have different themes and user prefs
        }

    # we need the lang macros to execute when html is generated,
    # to have correct dir and lang html attributes
    for lang in i18n.wikiLanguages():
        Dependencies[lang] = []


    def __init__(self, parser):
        self.parser = parser
        self.form = self.parser.form
        self.request = self.parser.request
        self.formatter = self.request.formatter
        self._ = self.request.getText
        self.cfg = self.request.cfg

        # Initialized on execute
        self.name = None

    def _wrap(self, function, args, fixed=[]):
        try:
            return wikiutil.invoke_extension_function(self.request, function,
                                                      args, fixed)
        except ValueError, e:
            return self.format_error(e)

    def format_error(self, err):
        """ format an error object for output instead of normal macro output """
        return self.formatter.text(u'<<%s: %s>>' % (self.name, err.args[0]))

    def execute(self, macro_name, args):
        """ Get and execute a macro

        Try to get a plugin macro, or a builtin macro or a language
        macro, or just raise ImportError.
        """
        self.name = macro_name
        try:
            call = wikiutil.importPlugin(self.cfg, 'macro', macro_name,
                                         function='macro_%s' % macro_name)
            execute = lambda _self, _args: _self._wrap(call, _args, [self])
        except wikiutil.PluginAttributeError:
            # fall back to old execute() method, no longer recommended
            execute = wikiutil.importPlugin(self.cfg, 'macro', macro_name)
        except wikiutil.PluginMissingError:
            try:
                call = getattr(self, 'macro_%s' % macro_name)
                execute = lambda _self, _args: _self._wrap(call, _args)
            except AttributeError:
                if macro_name in i18n.wikiLanguages():
                    execute = self.__class__._m_lang
                else:
                    raise ImportError("Cannot load macro %s" % macro_name)
        return execute(self, args)

    def _m_lang(self, text):
        """ Set the current language for page content.

            Language macro are used in two ways:
             * [lang] - set the current language until next lang macro
             * [lang(text)] - insert text with specific lang inside page
        """
        if text:
            return (self.formatter.lang(1, self.name) +
                    self.formatter.text(text) +
                    self.formatter.lang(0, self.name))

        self.request.current_lang = self.name
        return ''

    def get_dependencies(self, macro_name):
        if macro_name in self.Dependencies:
            return self.Dependencies[macro_name]
        try:
            return wikiutil.importPlugin(self.request.cfg, 'macro',
                                         macro_name, 'Dependencies')
        except wikiutil.PluginError:
            return self.defaultDependency

    def macro_TitleSearch(self):
        from MoinMoin.macro.FullSearch import search_box
        return search_box("titlesearch", self)

    def _make_index(self, word_re=u'.+'):
        """ make an index page (used for TitleIndex and WordIndex macro)

            word_re is a regex used for splitting a pagename into fragments
            matched by it (used for WordIndex). For TitleIndex, we just match
            the whole page name, so we only get one fragment that is the same
            as the pagename.

            TODO: _make_index could get a macro on its own, more powerful / less special than WordIndex and TitleIndex.
                  It should be able to filter for specific mimetypes, maybe match pagenames by regex (replace PageList?), etc.
        """
        _ = self._
        request = self.request
        fmt = self.formatter
        allpages = int(self.form.get('allpages', [0])[0]) != 0
        # Get page list readable by current user, filter by isSystemPage if needed
        if allpages:
            pages = request.rootpage.getPageList()
        else:
            def nosyspage(name):
                return not wikiutil.isSystemPage(request, name)
            pages = request.rootpage.getPageList(filter=nosyspage)

        word_re = re.compile(word_re, re.UNICODE)
        wordmap = {}
        for name in pages:
            for word in word_re.findall(name):
                try:
                    if not wordmap[word].count(name):
                        wordmap[word].append(name)
                except KeyError:
                    wordmap[word] = [name]

        # Sort ignoring case
        tmp = [(word.upper(), word) for word in wordmap]
        tmp.sort()
        all_words = [item[1] for item in tmp]

        index_letters = []
        current_letter = None
        output = []
        for word in all_words:
            letter = wikiutil.getUnicodeIndexGroup(word)
            if letter != current_letter:
                cssid = "idx" + wikiutil.quoteWikinameURL(letter).replace('%', '')
                output.append(fmt.heading(1, 2, id=cssid)) # fmt.anchordef didn't work
                output.append(fmt.text(letter.replace('~', 'Others')))
                output.append(fmt.heading(0, 2))
                current_letter = letter
            if letter not in index_letters:
                index_letters.append(letter)
            links = wordmap[word]
            if len(links) and links[0] != word: # show word fragment as on WordIndex
                output.append(fmt.strong(1))
                output.append(word)
                output.append(fmt.strong(0))

            output.append(fmt.bullet_list(1))
            links.sort()
            last_page = None
            for name in links:
                if name == last_page:
                    continue
                output.append(fmt.listitem(1))
                output.append(Page(request, name).link_to(request, attachment_indicator=1))
                output.append(fmt.listitem(0))
            output.append(fmt.bullet_list(0))

        def _make_index_key(index_letters):
            index_letters.sort()
            def letter_link(ch):
                cssid = "idx" + wikiutil.quoteWikinameURL(ch).replace('%', '')
                return fmt.anchorlink(1, cssid) + fmt.text(ch.replace('~', 'Others')) + fmt.anchorlink(0)
            links = [letter_link(letter) for letter in index_letters]
            return ' | '.join(links)

        page = fmt.page
        allpages_txt = (_('Include system pages'), _('Exclude system pages'))[allpages]
        allpages_url = page.url(request, querystr={'allpages': allpages and '0' or '1'})

        output = [fmt.paragraph(1), _make_index_key(index_letters), fmt.linebreak(0),
                  fmt.url(1, allpages_url), fmt.text(allpages_txt), fmt.url(0), fmt.paragraph(0)] + output
        return u''.join(output)


    def macro_TitleIndex(self):
        return self._make_index()

    def macro_WordIndex(self):
        if self.request.isSpiderAgent: # reduce bot cpu usage
            return ''
        word_re = u'[%s][%s]+' % (config.chars_upper, config.chars_lower)
        return self._make_index(word_re=word_re)

    def macro_Icon(self, icon=u''):
        # empty icon name isn't valid either
        if not icon:
            raise ValueError("You need to give a non-empty icon name")
        return self.formatter.icon(icon.lower())

