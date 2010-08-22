# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - internationalization (aka i18n)

    We use Python's gettext module for loading <language>.<domain>.mo files.
    Domain is "MoinMoin" for MoinMoin distribution code and something else for
    extension translations.

    Public attributes:
        languages -- dict of languages that MoinMoin knows metadata about

    Public functions:
        wikiLanguages() -- return the available wiki user languages
        browserLanguages() -- return the browser accepted languages
        getDirection(lang) -- return the lang direction either 'ltr' or 'rtl'
        getText(str, request, lang,  **kw) -- return str translation into lang

    TODO: as soon as we have some "farm / server plugin dir", extend this to
          load translations from there, too.

    @copyright: 2001-2004 Juergen Hermann <jh@web.de>,
                2005-2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import os, gettext, glob
from StringIO import StringIO

from flask import flaskg

from flask import current_app as app

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import caching
from MoinMoin.i18n import strings

SUPPORT_DICT_PAGES = False

# This is a global for a reason: in persistent environments all languages in
# use will be cached; Note: you have to restart if you update language data.

# key: language, value: language metadata
# this gets loaded early and completely:
languages = None

# system_pages has a dictionary containing all english
# system page names and also all translated system pages names as keys,
# see also wikiutil.isSystemPage:
system_pages = {}

translations = {}

def po_filename(request, language, domain, i18n_dir='i18n'):
    """ we use MoinMoin/i18n/<language>[.<domain>].mo as filename for the PO file.

        TODO: later, when we have a farm scope plugin dir, we can also load
              language data from there.
    """
    return os.path.join(app.cfg.moinmoin_dir, i18n_dir, "%s.%s.po" % (language, domain))

def i18n_init(request):
    """ this is called early from request initialization and makes sure we
        have metadata (like what languages are available, direction of language)
        loaded into the global "languages".
        The very first time, this will be slow as it will load all languages,
        but next time it will be fast due to caching.
    """
    global languages
    flaskg.clock.start('i18n_init')
    if languages is None:
        logging.debug("trying to load translations from cache")
        # the scope of the i18n cache needs to be per-wiki, because some translations
        # have http links (to some help pages) and they must not point to another
        # wiki in the farm (confusing and maybe not even readable due to ACLs):
        meta_cache = caching.CacheEntry(request, 'i18n', 'meta', scope='wiki', use_pickle=True)
        i18n_dir = os.path.join(app.cfg.moinmoin_dir, 'i18n')
        i18n_dir_mtime = os.path.getmtime(i18n_dir)
        if meta_cache.needsUpdate(i18n_dir_mtime):
            logging.debug("cache needs update")
            _languages = {}
            _system_pages = {}
            for pagename in strings.all_pages:
                _system_pages[pagename] = ('en', pagename)
            for lang_file in glob.glob(po_filename(request, language='*', domain='MoinMoin')): # XXX only MoinMoin domain for now
                language, domain, ext = os.path.basename(lang_file).split('.')
                t = Translation(language, domain)
                f = file(lang_file)
                t.load_po(f)
                f.close()
                logging.debug("loading translation %r" % language)
                encoding = 'utf-8'
                _languages[language] = {}
                for key, value in t.info.items():
                    #logging.debug("meta key %s value %r" % (key, value))
                    _languages[language][key] = value.decode(encoding)
                for pagename in strings.all_pages:
                    try:
                        pagename_translated = t.translation._catalog[pagename]
                    except KeyError:
                        pass
                    else:
                        _system_pages[pagename_translated] = (language, pagename)
            logging.debug("dumping language metadata to disk cache")
            try:
                meta_cache.update({
                    'languages': _languages,
                    'system_pages': _system_pages,
                })
            except caching.CacheError:
                pass

        if languages is None: # another thread maybe has done it before us
            try:
                logging.debug("loading language metadata from disk cache")
                d = meta_cache.content()
                if languages is None:
                    globals().update(d)
            except caching.CacheError:
                pass
    flaskg.clock.stop('i18n_init')


class Translation(object):
    """ This class represents a translation. Usually this is a translation
        from English original texts to a single language, like e.g. "de" (german).

        The domain value defaults to 'MoinMoin' and this is reserved for
        translation of the MoinMoin distribution. If you do a translation for
        a third-party plugin, you have to use a different and unique value.
    """
    def __init__(self, language, domain='MoinMoin'):
        self.language = language
        self.domain = domain

    def load_po(self, f):
        """ load the po file """
        from MoinMoin.i18n.msgfmt import MsgFmt
        mf = MsgFmt()
        mf.read_po(f.readlines())
        mo_data = mf.generate_mo()
        f = StringIO(mo_data)
        self.load_mo(f)
        f.close()

    def load_mo(self, f):
        """ load the mo file, setup some attributes from metadata """
        # binary files have to be opened in the binary file mode!
        self.translation = gettext.GNUTranslations(f)
        self.info = info = self.translation.info()
        try:
            self.name = info['x-language']
            self.ename = info['x-language-in-english']
            self.direction = info['x-direction']
            self.maintainer = info['last-translator']
        except KeyError, err:
            logging.warning("metadata problem in %r: %s" % (self.language, str(err)))
        try:
            assert self.direction in ('ltr', 'rtl', )
        except (AttributeError, AssertionError), err:
            logging.warning("direction problem in %r: %s" % (self.language, str(err)))

    def loadLanguage(self, request, trans_dir="i18n"):
        flaskg.clock.start('loadLanguage')
        # see comment about per-wiki scope above
        cache = caching.CacheEntry(request, arena='i18n', key=self.language, scope='wiki', use_pickle=True)
        langfilename = po_filename(request, self.language, self.domain, i18n_dir=trans_dir)
        langfile_mtime = os.path.getmtime(langfilename)
        needsupdate = cache.needsUpdate(langfile_mtime)
        if not needsupdate:
            try:
                unformatted = cache.content()
                logging.debug("pickle %s load success" % self.language)
            except caching.CacheError:
                logging.debug("pickle %s load failed" % self.language)
                needsupdate = 1

        if needsupdate:
            logging.debug("langfilename %s needs update" % langfilename)
            f = file(langfilename)
            self.load_po(f)
            f.close()
            trans = self.translation
            unformatted = trans._catalog
            logging.debug("dumping lang %s" % self.language)
            try:
                cache.update(unformatted)
            except caching.CacheError:
                pass

        self.raw = unformatted
        flaskg.clock.stop('loadLanguage')


def getDirection(lang):
    """ Return the text direction for a language, either 'ltr' or 'rtl'. """
    return languages[lang]['x-direction']

def getText(original, request, lang, **kw):
    """ Return a translation of some original text.

    @param original: the original (english) text
    @param request: the request object
    @lang: the target language for the translation
    """
    if original == u"":
        return u"" # we don't want to get *.po files metadata!

    global translations
    if not lang in translations: # load translation if needed
        t = Translation(lang)
        t.loadLanguage(request)
        translations[lang] = t

    # get the matching entry in the mapping table
    translated = original
    translation = translations[lang]
    if original in translation.raw:
        translated = translation.raw[original]
    else:
        try:
            if SUPPORT_DICT_PAGES:
                if languages is None:
                    # languages not initialized yet
                    raise KeyError
                language = languages[lang]['x-language-in-english']
                dictpagename = "%sDict" % language.replace(' ', '')
                dicts = request.dicts
                if dictpagename in dicts:
                    userdict = dicts[dictpagename]
                    translated = userdict[original]
                else:
                    raise KeyError
            else:
                raise KeyError
        except KeyError:
            # do not simply return trans with str, but recursively call
            # to get english translation.
            if lang != 'en':
                logging.debug("falling back to english, requested string not in %r translation: %r" % (lang, original))
                translated = getText(original, request, 'en')
    return translated


def wikiLanguages():
    """
    Return the available user languages in this wiki.
    As we do everything in unicode (or utf-8) now, everything is available.
    """
    return languages


def browserLanguages(request):
    """
    Return the accepted languages as set in the user browser.

    Parse the HTTP headers and extract the accepted languages, according to:
    http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.4

    Return a list of languages and base languages - as they are specified in
    the request, normalizing to lower case.
    """
    fallback = []
    accepted = request.accept_languages
    if accepted:
        # Add base language for each sub language. If the user specified
        # a sub language like "en-us", we will try to to provide it or
        # a least the base language "en" in this case.
        for lang, quality in accepted:
            lang = lang.lower()
            fallback.append(lang)
            if '-' in lang:
                baselang = lang.split('-')[0]
                fallback.append(baselang)
    return fallback

def get_browser_language(request):
    """
    Return the language that is supported by wiki and what user browser
    would prefer to get. Return empty string if there is no such language
    or language_ignore_browser is true.

    @param request: the request object
    @rtype: string
    @return: ISO language code, e.g. 'en'
    """
    available = wikiLanguages()
    if available and not app.cfg.language_ignore_browser:
            for lang in browserLanguages(request):
                if lang in available:
                    return lang
    return ''

