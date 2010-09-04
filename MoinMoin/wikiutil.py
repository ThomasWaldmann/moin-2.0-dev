# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Wiki Utility Functions

    @copyright: 2000-2004 Juergen Hermann <jh@web.de>,
                2004 by Florian Festi,
                2006 by Mikko Virkkil,
                2005-2010 MoinMoin:ThomasWaldmann,
                2007 MoinMoin:ReimarBauer,
                2008 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import os
import re
import time

from MoinMoin import log
logging = log.getLogger(__name__)

from flask import current_app as app
from flask import flaskg
from flask import request

from MoinMoin import _, N_
from MoinMoin import config
from MoinMoin.util import pysupport, lock
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError

import werkzeug

# constants for page names
PARENT_PREFIX = "../"
PARENT_PREFIX_LEN = len(PARENT_PREFIX)
CHILD_PREFIX = "/"
CHILD_PREFIX_LEN = len(CHILD_PREFIX)

#############################################################################
### Getting data from user/Sending data to user
#############################################################################

def decodeUnknownInput(text):
    """ Decode input in unknown encoding

    First we try utf-8 because it has special format, and it will decode
    only utf-8 files. Then we try config.charset, then iso-8859-1 using
    'replace'. We will never raise an exception, but may return junk
    data.

    WARNING: Use this function only for data that you view, not for data
    that you save in the wiki.

    @param text: the text to decode, string
    @rtype: unicode
    @return: decoded text (maybe wrong)
    """
    # Shortcut for unicode input
    if isinstance(text, unicode):
        return text

    try:
        return unicode(text, 'utf-8')
    except UnicodeError:
        if config.charset not in ['utf-8', 'iso-8859-1']:
            try:
                return unicode(text, config.charset)
            except UnicodeError:
                pass
        return unicode(text, 'iso-8859-1', 'replace')


def decodeUserInput(s, charsets=[config.charset]):
    """
    Decodes input from the user.

    @param s: the string to unquote
    @param charsets: list of charsets to assume the string is in
    @rtype: unicode
    @return: the unquoted string as unicode
    """
    for charset in charsets:
        try:
            return s.decode(charset)
        except UnicodeError:
            pass
    raise UnicodeError('The string %r cannot be decoded.' % s)


def clean_input(text, max_len=201):
    """ Clean input:
        replace CR, LF, TAB by whitespace
        delete control chars

        @param text: unicode text to clean (if we get str, we decode)
        @rtype: unicode
        @return: cleaned text
    """
    # we only have input fields with max 200 chars, but spammers send us more
    length = len(text)
    if length == 0 or length > max_len:
        return u''
    else:
        if isinstance(text, str):
            # the translate() below can ONLY process unicode, thus, if we get
            # str, we try to decode it using the usual coding:
            text = text.decode(config.charset)
        return text.translate(config.clean_input_translation_map)


def make_breakable(text, maxlen):
    """ make a text breakable by inserting spaces into nonbreakable parts
    """
    text = text.split(" ")
    newtext = []
    for part in text:
        if len(part) > maxlen:
            while part:
                newtext.append(part[:maxlen])
                part = part[maxlen:]
        else:
            newtext.append(part)
    return " ".join(newtext)

########################################################################
### Storage
########################################################################

# Precompiled patterns for file name [un]quoting
UNSAFE = re.compile(r'[^a-zA-Z0-9_]+')
QUOTED = re.compile(r'\(([a-fA-F0-9]+)\)')


def quoteWikinameFS(wikiname, charset=config.charset):
    """ Return file system representation of a Unicode WikiName.

    Warning: will raise UnicodeError if wikiname can not be encoded using
    charset. The default value of config.charset, 'utf-8' can encode any
    character.

    @param wikiname: Unicode string possibly containing non-ascii characters
    @param charset: charset to encode string
    @rtype: string
    @return: quoted name, safe for any file system
    """
    filename = wikiname.encode(charset)

    quoted = []
    location = 0
    for needle in UNSAFE.finditer(filename):
        # append leading safe stuff
        quoted.append(filename[location:needle.start()])
        location = needle.end()
        # Quote and append unsafe stuff
        quoted.append('(')
        for character in needle.group():
            quoted.append('%02x' % ord(character))
        quoted.append(')')

    # append rest of string
    quoted.append(filename[location:])
    return ''.join(quoted)


class InvalidFileNameError(Exception):
    """ Called when we find an invalid file name """
    pass


def unquoteWikiname(filename, charsets=[config.charset]):
    """ Return Unicode WikiName from quoted file name.

    We raise an InvalidFileNameError if we find an invalid name, so the
    wiki could alarm the admin or suggest the user to rename a page.
    Invalid file names should never happen in normal use, but are rather
    cheap to find.

    This function should be used only to unquote file names, not page
    names we receive from the user. These are handled in request already.

    Todo: search clients of unquoteWikiname and check for exceptions.

    @param filename: string using charset and possibly quoted parts
    @param charsets: list of charsets used by string
    @rtype: Unicode String
    @return: WikiName
    """
    ### Temporary fix start ###
    # From some places we get called with Unicode strings
    if isinstance(filename, type(u'')):
        filename = filename.encode(config.charset)
    ### Temporary fix end ###

    parts = []
    start = 0
    for needle in QUOTED.finditer(filename):
        # append leading unquoted stuff
        parts.append(filename[start:needle.start()])
        start = needle.end()
        # Append quoted stuff
        group = needle.group(1)
        # Filter invalid filenames
        if (len(group) % 2 != 0):
            raise InvalidFileNameError(filename)
        try:
            for i in range(0, len(group), 2):
                byte = group[i:i+2]
                character = chr(int(byte, 16))
                parts.append(character)
        except ValueError:
            # byte not in hex, e.g 'xy'
            raise InvalidFileNameError(filename)

    # append rest of string
    if start == 0:
        wikiname = filename
    else:
        parts.append(filename[start:len(filename)])
        wikiname = ''.join(parts)

    # FIXME: This looks wrong, because at this stage "()" can be both errors
    # like open "(" without close ")", or unquoted valid characters in the file name.
    # Filter invalid filenames. Any left (xx) must be invalid
    #if '(' in wikiname or ')' in wikiname:
    #    raise InvalidFileNameError(filename)

    wikiname = decodeUserInput(wikiname, charsets)
    return wikiname


#############################################################################
### Page edit locking
#############################################################################

EDIT_LOCK_TIMESTAMP = "edit_lock_timestamp"
EDIT_LOCK_ADDR = "edit_lock_addr"
EDIT_LOCK_HOSTNAME = "edit_lock_hostname"
EDIT_LOCK_USERID = "edit_lock_userid"

EDIT_LOCK = (EDIT_LOCK_TIMESTAMP, EDIT_LOCK_ADDR, EDIT_LOCK_HOSTNAME, EDIT_LOCK_USERID)

def get_edit_lock(item):
    """
    Given an Item, get a tuple containing the timestamp of the edit-lock and the user.
    """
    for key in EDIT_LOCK:
        if not key in item:
            return (False, 0.0, "", "", "")
        else:
            return (True, float(item[EDIT_LOCK_TIMESTAMP]), item[EDIT_LOCK_ADDR],
                    item[EDIT_LOCK_HOSTNAME], item[EDIT_LOCK_USERID])

def set_edit_lock(item):
    """
    Set the lock property to True or False.
    """
    timestamp = time.time()
    addr = request.remote_addr
    hostname = wikiutil.get_hostname(addr)
    userid = flaskg.user.valid and flaskg.user.id or ''

    item.change_metadata()
    item[EDIT_LOCK_TIMESTAMP] = str(timestamp)
    item[EDIT_LOCK_ADDR] = addr
    item[EDIT_LOCK_HOSTNAME] = hostname
    item[EDIT_LOCK_USERID] = userid
    item.publish_metadata()


#############################################################################
### InterWiki
#############################################################################

def split_interwiki(wikiurl):
    """ Split a interwiki name, into wikiname and pagename, e.g:

    'MoinMoin:FrontPage' -> "MoinMoin", "FrontPage"
    'FrontPage' -> "Self", "FrontPage"
    'MoinMoin:Page with blanks' -> "MoinMoin", "Page with blanks"
    'MoinMoin:' -> "MoinMoin", ""

    @param wikiurl: the url to split
    @rtype: tuple
    @return: (wikiname, pagename)
    """
    try:
        wikiname, pagename = wikiurl.split(":", 1)
    except ValueError:
        wikiname, pagename = 'Self', wikiurl
    return wikiname, pagename

def resolve_interwiki(wikiname, pagename):
    """ Resolve an interwiki reference (wikiname:pagename).

    @param wikiname: interwiki wiki name
    @param pagename: interwiki page name
    @rtype: tuple
    @return: (wikitag, wikiurl, wikitail, err)
    """
    this_wiki_url = request.script_root + '/'
    if wikiname in ('Self', app.cfg.interwikiname):
        return (wikiname, this_wiki_url, pagename, False)
    else:
        try:
            return (wikiname, app.cfg.interwiki_map[wikiname], pagename, False)
        except KeyError:
            return (wikiname, this_wiki_url, "InterWiki", True)

def join_wiki(wikiurl, wikitail):
    """
    Add a (url_quoted) page name to an interwiki url.

    Note: We can't know what kind of URL quoting a remote wiki expects.
          We just use a utf-8 encoded string with standard URL quoting.

    @param wikiurl: wiki url, maybe including a $PAGE placeholder
    @param wikitail: page name
    @rtype: string
    @return: generated URL of the page in the other wiki
    """
    wikitail = werkzeug.url_quote(wikitail, charset=config.charset, safe='/')
    if '$PAGE' in wikiurl:
        return wikiurl.replace('$PAGE', wikitail)
    else:
        return wikiurl + wikitail

#############################################################################
### Item types (based on item names)
#############################################################################

def isSystemItem(itemname):
    """ Is this a system page?

    @param itemname: the item name
    @rtype: bool
    @return: True if page is a system item
    """
    from MoinMoin.items import IS_SYSITEM
    try:
        item = flaskg.storage.get_item(itemname)
        return item.get_revision(-1)[IS_SYSITEM]
    except (NoSuchItemError, NoSuchRevisionError, KeyError):
        pass

    return isTemplateItem(itemname)


def isTemplateItem(itemname):
    """ Is this a template item?

    @param itemname: the item name
    @rtype: bool
    @return: True if item is a template item
    """
    return app.cfg.cache.item_template_regexact.search(itemname) is not None


def isGroupItem(itemname):
    """ Is this a name of group item?

    @param itemname: the item name
    @rtype: bool
    @return: True if item is a group item
    """
    return app.cfg.cache.item_group_regexact.search(itemname) is not None


def filterCategoryPages(pagelist):
    """ Return category pages in pagelist

    WARNING: DO NOT USE THIS TO FILTER THE FULL PAGE LIST! Use
    getPageList with a filter function.

    If you pass a list with a single pagename, either that is returned
    or an empty list, thus you can use this function like a `isCategoryPage`
    one.

    @param pagelist: a list of pages
    @rtype: list
    @return: only the category pages of pagelist
    """
    func = app.cfg.cache.item_category_regexact.search
    return [pn for pn in pagelist if func(pn)]


def getInterwikiHome(username=None):
    """
    Get a user's homepage.

    cfg.user_homewiki influences behaviour of this:
    'Self' does mean we store user homepage in THIS wiki.
    When set to our own interwikiname, it behaves like with 'Self'.

    'SomeOtherWiki' means we store user homepages in another wiki.

    @param username: the user's name
    @rtype: tuple (or None for anon users)
    @return: (wikiname, pagename)
    """
    # default to current user
    if username is None and flaskg.user.valid:
        username = flaskg.user.name
    if not username:
        return None # anon user

    homewiki = app.cfg.user_homewiki
    if homewiki == app.cfg.interwikiname:
        homewiki = u'Self'

    return homewiki, username


def AbsPageName(context, pagename):
    """
    Return the absolute pagename for a (possibly) relative pagename.

    @param context: name of the page where "pagename" appears on
    @param pagename: the (possibly relative) page name
    @rtype: string
    @return: the absolute page name
    """
    if pagename.startswith(PARENT_PREFIX):
        while context and pagename.startswith(PARENT_PREFIX):
            context = '/'.join(context.split('/')[:-1])
            pagename = pagename[PARENT_PREFIX_LEN:]
        pagename = '/'.join(filter(None, [context, pagename, ]))
    elif pagename.startswith(CHILD_PREFIX):
        if context:
            pagename = context + '/' + pagename[CHILD_PREFIX_LEN:]
        else:
            pagename = pagename[CHILD_PREFIX_LEN:]
    return pagename

def RelPageName(context, pagename):
    """
    Return the relative pagename for some context.

    @param context: name of the page where "pagename" appears on
    @param pagename: the absolute page name
    @rtype: string
    @return: the relative page name
    """
    if context == '':
        # special case, context is some "virtual root" page with name == ''
        # every page is a subpage of this virtual root
        return CHILD_PREFIX + pagename
    elif pagename.startswith(context + CHILD_PREFIX):
        # simple child
        return pagename[len(context):]
    else:
        # some kind of sister/aunt
        context_frags = context.split('/')   # A, B, C, D, E
        pagename_frags = pagename.split('/') # A, B, C, F
        # first throw away common parents:
        common = 0
        for cf, pf in zip(context_frags, pagename_frags):
            if cf == pf:
                common += 1
            else:
                break
        context_frags = context_frags[common:] # D, E
        pagename_frags = pagename_frags[common:] # F
        go_up = len(context_frags)
        return PARENT_PREFIX * go_up + '/'.join(pagename_frags)


def ParentItemName(pagename):
    """
    Return the parent pagename.

    @param pagename: the absolute page name (unicode)
    @rtype: unicode
    @return: the parent page name (or empty string for toplevel pages)
    """
    if pagename:
        pos = pagename.rfind('/')
        if pos > 0:
            return pagename[:pos]
    return u''


#############################################################################
### mimetype support
#############################################################################
import mimetypes

MIMETYPES_MORE = {
 # OpenOffice 2.x & other open document stuff
 '.odt': 'application/vnd.oasis.opendocument.text',
 '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
 '.odp': 'application/vnd.oasis.opendocument.presentation',
 '.odg': 'application/vnd.oasis.opendocument.graphics',
 '.odc': 'application/vnd.oasis.opendocument.chart',
 '.odf': 'application/vnd.oasis.opendocument.formula',
 '.odb': 'application/vnd.oasis.opendocument.database',
 '.odi': 'application/vnd.oasis.opendocument.image',
 '.odm': 'application/vnd.oasis.opendocument.text-master',
 '.ott': 'application/vnd.oasis.opendocument.text-template',
 '.ots': 'application/vnd.oasis.opendocument.spreadsheet-template',
 '.otp': 'application/vnd.oasis.opendocument.presentation-template',
 '.otg': 'application/vnd.oasis.opendocument.graphics-template',
 # some systems (like Mac OS X) don't have some of these:
 '.patch': 'text/x-diff',
 '.diff': 'text/x-diff',
 '.py': 'text/x-python',
 '.cfg': 'text/plain',
 '.conf': 'text/plain',
 '.irc': 'text/plain',
 '.md5': 'text/plain',
 '.csv': 'text/csv',
 '.flv': 'video/x-flv',
 '.wmv': 'video/x-ms-wmv',
 '.swf': 'application/x-shockwave-flash',
 '.moin': 'text/x.moin.wiki',
 '.creole': 'text/x.moin.creole',
}

# add all mimetype patterns of pygments
import pygments.lexers

for name, short, patterns, mime in pygments.lexers.get_all_lexers():
    for pattern in patterns:
        if pattern.startswith('*.') and mime:
            MIMETYPES_MORE[pattern[1:]] = mime[0]

[mimetypes.add_type(mimetype, ext, True) for ext, mimetype in MIMETYPES_MORE.items()]

MIMETYPES_sanitize_mapping = {
    # this stuff is text, but got application/* for unknown reasons
    ('application', 'docbook+xml'): ('text', 'docbook'),
    ('application', 'x-latex'): ('text', 'latex'),
    ('application', 'x-tex'): ('text', 'tex'),
    ('application', 'javascript'): ('text', 'javascript'),
}

MIMETYPES_spoil_mapping = {} # inverse mapping of above
for _key, _value in MIMETYPES_sanitize_mapping.items():
    MIMETYPES_spoil_mapping[_value] = _key


class MimeType(object):
    """ represents a mimetype like text/plain """

    def __init__(self, mimestr=None, filename=None):
        self.major = self.minor = None # sanitized mime type and subtype
        self.params = {} # parameters like "charset" or others
        self.charset = None # this stays None until we know for sure!
        self.raw_mimestr = mimestr
        self.filename = filename
        if mimestr:
            self.parse_mimetype(mimestr)
        elif filename:
            self.parse_filename(filename)

    def parse_filename(self, filename):
        mtype, encoding = mimetypes.guess_type(filename)
        if mtype is None:
            mtype = 'application/octet-stream'
        self.parse_mimetype(mtype)

    def parse_mimetype(self, mimestr):
        """ take a string like used in content-type and parse it into components,
            alternatively it also can process some abbreviated string like "wiki"
        """
        parameters = mimestr.split(";")
        parameters = [p.strip() for p in parameters]
        mimetype, parameters = parameters[0], parameters[1:]
        mimetype = mimetype.split('/')
        if len(mimetype) >= 2:
            major, minor = mimetype[:2] # we just ignore more than 2 parts
        else:
            major, minor = self.parse_format(mimetype[0])
        self.major = major.lower()
        self.minor = minor.lower()
        for param in parameters:
            key, value = param.split('=')
            if value[0] == '"' and value[-1] == '"': # remove quotes
                value = value[1:-1]
            self.params[key.lower()] = value
        if 'charset' in self.params:
            self.charset = self.params['charset'].lower()
        self.sanitize()

    def parse_format(self, format):
        """ maps from what we currently use on-page in a #format xxx processing
            instruction to a sanitized mimetype major, minor tuple.
            can also be user later for easier entry by the user, so he can just
            type "wiki" instead of "text/x.moin.wiki".
        """
        format = format.lower()
        if format in config.parser_text_mimetype:
            mimetype = 'text', format
        else:
            mapping = {
                'wiki': ('text', 'x.moin.wiki'),
                'irc': ('text', 'irssi'),
            }
            try:
                mimetype = mapping[format]
            except KeyError:
                mimetype = 'text', 'x-%s' % format
        return mimetype

    def sanitize(self):
        """ convert to some representation that makes sense - this is not necessarily
            conformant to /etc/mime.types or IANA listing, but if something is
            readable text, we will return some text/* mimetype, not application/*,
            because we need text/plain as fallback and not application/octet-stream.
        """
        self.major, self.minor = MIMETYPES_sanitize_mapping.get((self.major, self.minor), (self.major, self.minor))

    def spoil(self):
        """ this returns something conformant to /etc/mime.type or IANA as a string,
            kind of inverse operation of sanitize(), but doesn't change self
        """
        major, minor = MIMETYPES_spoil_mapping.get((self.major, self.minor), (self.major, self.minor))
        return self.content_type(major, minor)

    def content_type(self, major=None, minor=None, charset=None, params=None):
        """ return a string suitable for Content-Type header
        """
        major = major or self.major
        minor = minor or self.minor
        params = params or self.params or {}
        if major == 'text':
            charset = charset or self.charset or params.get('charset', config.charset)
            params['charset'] = charset
        mimestr = "%s/%s" % (major, minor)
        params = ['%s="%s"' % (key.lower(), value) for key, value in params.items()]
        params.insert(0, mimestr)
        return "; ".join(params)

    def mime_type(self):
        """ return a string major/minor only, no params """
        return "%s/%s" % (self.major, self.minor)

    def content_disposition(self, cfg):
        # for dangerous files (like .html), when we are in danger of cross-site-scripting attacks,
        # we just let the user store them to disk ('attachment').
        # For safe files, we directly show them inline (this also works better for IE).
        mime_type = self.mime_type()
        dangerous = mime_type in cfg.mimetypes_xss_protect
        content_disposition = dangerous and 'attachment' or 'inline'
        filename = self.filename
        if filename is not None:
            # TODO: fix the encoding here, plain 8 bit is not allowed according to the RFCs
            # There is no solution that is compatible to IE except stripping non-ascii chars
            if isinstance(filename, unicode):
                filename = filename.encode(config.charset)
            content_disposition += '; filename="%s"' % filename
        return content_disposition

    def module_name(self):
        """ convert this mimetype to a string useable as python module name,
            we yield the exact module name first and then proceed to shorter
            module names (useful for falling back to them, if the more special
            module is not found) - e.g. first "text_python", next "text".
            Finally, we yield "application_octet_stream" as the most general
            mimetype we have.
            Hint: the fallback handler module for text/* should be implemented
                  in module "text" (not "text_plain")
        """
        mimetype = self.mime_type()
        modname = mimetype.replace("/", "_").replace("-", "_").replace(".", "_")
        fragments = modname.split('_')
        for length in range(len(fragments), 1, -1):
            yield "_".join(fragments[:length])
        yield self.raw_mimestr
        yield fragments[0]
        yield "application_octet_stream"


#############################################################################
### Plugins
#############################################################################

class PluginError(Exception):
    """ Base class for plugin errors """

class PluginMissingError(PluginError):
    """ Raised when a plugin is not found """

class PluginAttributeError(PluginError):
    """ Raised when plugin does not contain an attribtue """


def importPlugin(cfg, kind, name, function="execute"):
    """ Import wiki or builtin plugin

    Returns <function> attr from a plugin module <name>.
    If <function> attr is missing, raise PluginAttributeError.
    If <function> is None, return the whole module object.

    If <name> plugin can not be imported, raise PluginMissingError.

    kind may be one of 'action', 'macro' or any other
    directory that exist in MoinMoin or data/plugin.

    Wiki plugins will always override builtin plugins. If you want
    specific plugin, use either importWikiPlugin or importBuiltinPlugin
    directly.

    @param cfg: wiki config instance
    @param kind: what kind of module we want to import
    @param name: the name of the module
    @param function: the function name
    @rtype: any object
    @return: "function" of module "name" of kind "kind", or None
    """
    try:
        return importWikiPlugin(cfg, kind, name, function)
    except PluginMissingError:
        return importBuiltinPlugin(kind, name, function)


def importWikiPlugin(cfg, kind, name, function="execute"):
    """ Import plugin from the wiki data directory

    See importPlugin docstring.
    """
    plugins = wikiPlugins(kind, cfg)
    modname = plugins.get(name, None)
    if modname is None:
        raise PluginMissingError()
    moduleName = '%s.%s' % (modname, name)
    return importNameFromPlugin(moduleName, function)


def importBuiltinPlugin(kind, name, function="execute"):
    """ Import builtin plugin from MoinMoin package

    See importPlugin docstring.
    """
    if not name in builtinPlugins(kind):
        raise PluginMissingError()
    moduleName = 'MoinMoin.%s.%s' % (kind, name)
    return importNameFromPlugin(moduleName, function)


def importNameFromPlugin(moduleName, name):
    """ Return <name> attr from <moduleName> module,
        raise PluginAttributeError if name does not exist.

        If name is None, return the <moduleName> module object.
    """
    if name is None:
        fromlist = []
    else:
        fromlist = [name]
    module = __import__(moduleName, globals(), {}, fromlist)
    if fromlist:
        # module has the obj for module <moduleName>
        try:
            return getattr(module, name)
        except AttributeError:
            raise PluginAttributeError
    else:
        # module now has the toplevel module of <moduleName> (see __import__ docs!)
        components = moduleName.split('.')
        for comp in components[1:]:
            module = getattr(module, comp)
        return module


def builtinPlugins(kind):
    """ Gets a list of modules in MoinMoin.'kind'

    @param kind: what kind of modules we look for
    @rtype: list
    @return: module names
    """
    modulename = "MoinMoin." + kind
    return pysupport.importName(modulename, "modules")


def wikiPlugins(kind, cfg):
    """
    Gets a dict containing the names of all plugins of @kind
    as the key and the containing module name as the value.

    @param kind: what kind of modules we look for
    @rtype: dict
    @return: plugin name to containing module name mapping
    """
    # short-cut if we've loaded the dict already
    # (or already failed to load it)
    cache = cfg._site_plugin_lists
    if kind in cache:
        result = cache[kind]
    else:
        result = {}
        for modname in cfg._plugin_modules:
            try:
                module = pysupport.importName(modname, kind)
                packagepath = os.path.dirname(module.__file__)
                plugins = pysupport.getPluginModules(packagepath)
                for p in plugins:
                    if not p in result:
                        result[p] = '%s.%s' % (modname, kind)
            except AttributeError:
                pass
        cache[kind] = result
    return result


def getPlugins(kind, cfg):
    """ Gets a list of plugin names of kind

    @param kind: what kind of modules we look for
    @rtype: list
    @return: module names
    """
    # Copy names from builtin plugins - so we dont destroy the value
    all_plugins = builtinPlugins(kind)[:]

    # Add extension plugins without duplicates
    for plugin in wikiPlugins(kind, cfg):
        if plugin not in all_plugins:
            all_plugins.append(plugin)

    return all_plugins


def searchAndImportPlugin(cfg, type, name, what=None):
    type2classname = {
    }
    if what is None:
        what = type2classname[type]
    mt = MimeType(name)
    plugin = None
    for module_name in mt.module_name():
        try:
            plugin = importPlugin(cfg, type, module_name, what)
            break
        except PluginMissingError:
            pass
    else:
        raise PluginMissingError("Plugin not found! (%r %r %r)" % (type, name, what))
    return plugin


#############################################################################
### Parameter parsing
#############################################################################

class BracketError(Exception):
    pass

class BracketUnexpectedCloseError(BracketError):
    def __init__(self, bracket):
        self.bracket = bracket
        BracketError.__init__(self, "Unexpected closing bracket %s" % bracket)

class BracketMissingCloseError(BracketError):
    def __init__(self, bracket):
        self.bracket = bracket
        BracketError.__init__(self, "Missing closing bracket %s" % bracket)

class ParserPrefix:
    """
    Trivial container-class holding a single character for
    the possible prefixes for parse_quoted_separated_ext
    and implementing rich equal comparison.
    """
    def __init__(self, prefix):
        self.prefix = prefix

    def __eq__(self, other):
        return isinstance(other, ParserPrefix) and other.prefix == self.prefix

    def __repr__(self):
        return '<ParserPrefix(%s)>' % self.prefix.encode('utf-8')

def parse_quoted_separated_ext(args, separator=None, name_value_separator=None,
                               brackets=None, seplimit=0, multikey=False,
                               prefixes=None, quotes='"'):
    """
    Parses the given string according to the other parameters.

    Items can be quoted with any character from the quotes parameter
    and each quote can be escaped by doubling it, the separator and
    name_value_separator can both be quoted, when name_value_separator
    is set then the name can also be quoted.

    Values that are not given are returned as None, while the
    empty string as a value can be achieved by quoting it.

    If a name or value does not start with a quote, then the quote
    looses its special meaning for that name or value, unless it
    starts with one of the given prefixes (the parameter is unicode
    containing all allowed prefixes.) The prefixes will be returned
    as ParserPrefix() instances in the first element of the tuple
    for that particular argument.

    If multiple separators follow each other, this is treated as
    having None arguments inbetween, that is also true for when
    space is used as separators (when separator is None), filter
    them out afterwards.

    The function can also do bracketing, i.e. parse expressions
    that contain things like
        "(a (a b))" to ['(', 'a', ['(', 'a', 'b']],
    in this case, as in this example, the returned list will
    contain sub-lists and the brackets parameter must be a list
    of opening and closing brackets, e.g.
        brackets = ['()', '<>']
    Each sub-list's first item is the opening bracket used for
    grouping.
    Nesting will be observed between the different types of
    brackets given. If bracketing doesn't match, a BracketError
    instance is raised with a 'bracket' property indicating the
    type of missing or unexpected bracket, the instance will be
    either of the class BracketMissingCloseError or of the class
    BracketUnexpectedCloseError.

    If multikey is True (along with setting name_value_separator),
    then the returned tuples for (key, value) pairs can also have
    multiple keys, e.g.
        "a=b=c" -> ('a', 'b', 'c')

    @param args: arguments to parse
    @param separator: the argument separator, defaults to None, meaning any
        space separates arguments
    @param name_value_separator: separator for name=value, default '=',
        name=value keywords not parsed if evaluates to False
    @param brackets: a list of two-character strings giving
        opening and closing brackets
    @param seplimit: limits the number of parsed arguments
    @param multikey: multiple keys allowed for a single value
    @rtype: list
    @returns: list of unicode strings and tuples containing
        unicode strings, or lists containing the same for
        bracketing support
    """
    idx = 0
    assert name_value_separator is None or name_value_separator != separator
    assert name_value_separator is None or len(name_value_separator) == 1
    if not isinstance(args, unicode):
        raise TypeError('args must be unicode')
    max = len(args)
    result = []         # result list
    cur = [None]        # current item
    quoted = None       # we're inside quotes, indicates quote character used
    skipquote = 0       # next quote is a quoted quote
    noquote = False     # no quotes expected because word didn't start with one
    seplimit_reached = False # number of separators exhausted
    separator_count = 0 # number of separators encountered
    SPACE = [' ', '\t', ]
    nextitemsep = [separator]   # used for skipping trailing space
    SPACE = [' ', '\t', ]
    if separator is None:
        nextitemsep = SPACE[:]
        separators = SPACE
    else:
        nextitemsep = [separator]   # used for skipping trailing space
        separators = [separator]
    if name_value_separator:
        nextitemsep.append(name_value_separator)

    # bracketing support
    opening = []
    closing = []
    bracketstack = []
    matchingbracket = {}
    if brackets:
        for o, c in brackets:
            assert not o in opening
            opening.append(o)
            assert not c in closing
            closing.append(c)
            matchingbracket[o] = c

    def additem(result, cur, separator_count, nextitemsep):
        if len(cur) == 1:
            result.extend(cur)
        elif cur:
            result.append(tuple(cur))
        cur = [None]
        noquote = False
        separator_count += 1
        seplimit_reached = False
        if seplimit and separator_count >= seplimit:
            seplimit_reached = True
            nextitemsep = [n for n in nextitemsep if n in separators]

        return cur, noquote, separator_count, seplimit_reached, nextitemsep

    while idx < max:
        char = args[idx]
        next = None
        if idx + 1 < max:
            next = args[idx+1]
        if skipquote:
            skipquote -= 1
        if not separator is None and not quoted and char in SPACE:
            spaces = ''
            # accumulate all space
            while char in SPACE and idx < max - 1:
                spaces += char
                idx += 1
                char = args[idx]
            # remove space if args end with it
            if char in SPACE and idx == max - 1:
                break
            # remove space at end of argument
            if char in nextitemsep:
                continue
            idx -= 1
            if len(cur) and cur[-1]:
                cur[-1] = cur[-1] + spaces
        elif not quoted and char == name_value_separator:
            if multikey or len(cur) == 1:
                cur.append(None)
            else:
                if not multikey:
                    if cur[-1] is None:
                        cur[-1] = ''
                    cur[-1] += name_value_separator
                else:
                    cur.append(None)
            noquote = False
        elif not quoted and not seplimit_reached and char in separators:
            (cur, noquote, separator_count, seplimit_reached,
             nextitemsep) = additem(result, cur, separator_count, nextitemsep)
        elif not quoted and not noquote and char in quotes:
            if len(cur) and cur[-1] is None:
                del cur[-1]
            cur.append(u'')
            quoted = char
        elif char == quoted and not skipquote:
            if next == quoted:
                skipquote = 2 # will be decremented right away
            else:
                quoted = None
        elif not quoted and char in opening:
            while len(cur) and cur[-1] is None:
                del cur[-1]
            (cur, noquote, separator_count, seplimit_reached,
             nextitemsep) = additem(result, cur, separator_count, nextitemsep)
            bracketstack.append((matchingbracket[char], result))
            result = [char]
        elif not quoted and char in closing:
            while len(cur) and cur[-1] is None:
                del cur[-1]
            (cur, noquote, separator_count, seplimit_reached,
             nextitemsep) = additem(result, cur, separator_count, nextitemsep)
            cur = []
            if not bracketstack:
                raise BracketUnexpectedCloseError(char)
            expected, oldresult = bracketstack[-1]
            if not expected == char:
                raise BracketUnexpectedCloseError(char)
            del bracketstack[-1]
            oldresult.append(result)
            result = oldresult
        elif not quoted and prefixes and char in prefixes and cur == [None]:
            cur = [ParserPrefix(char)]
            cur.append(None)
        else:
            if len(cur):
                if cur[-1] is None:
                    cur[-1] = char
                else:
                    cur[-1] += char
            else:
                cur.append(char)
            noquote = True

        idx += 1

    if bracketstack:
        raise BracketMissingCloseError(bracketstack[-1][0])

    if quoted:
        if len(cur):
            if cur[-1] is None:
                cur[-1] = quoted
            else:
                cur[-1] = quoted + cur[-1]
        else:
            cur.append(quoted)

    additem(result, cur, separator_count, nextitemsep)

    return result

def parse_quoted_separated(args, separator=',', name_value=True, seplimit=0):
    result = []
    positional = result
    if name_value:
        name_value_separator = '='
        trailing = []
        keywords = {}
    else:
        name_value_separator = None

    l = parse_quoted_separated_ext(args, separator=separator,
                                   name_value_separator=name_value_separator,
                                   seplimit=seplimit)
    for item in l:
        if isinstance(item, tuple):
            key, value = item
            if key is None:
                key = u''
            keywords[key] = value
            positional = trailing
        else:
            positional.append(item)

    if name_value:
        return result, keywords, trailing
    return result

def get_bool(request, arg, name=None, default=None):
    """
    For use with values returned from parse_quoted_separated or given
    as macro parameters, return a boolean from a unicode string.
    Valid input is 'true'/'false', 'yes'/'no' and '1'/'0' or None for
    the default value.

    @param request: A request instance
    @param arg: The argument, may be None or a unicode string
    @param name: Name of the argument, for error messages
    @param default: default value if arg is None
    @rtype: boolean or None
    @returns: the boolean value of the string according to above rules
              (or default value)
    """
    assert default is None or isinstance(default, bool)
    if arg is None:
        return default
    elif not isinstance(arg, unicode):
        raise TypeError('Argument must be None or unicode')
    arg = arg.lower()
    if arg in [u'0', u'false', u'no']:
        return False
    elif arg in [u'1', u'true', u'yes']:
        return True
    else:
        if name:
            raise ValueError(
                _('Argument "%s" must be a boolean value, not "%s"') % (
                    name, arg))
        else:
            raise ValueError(
                _('Argument must be a boolean value, not "%s"') % arg)


def get_int(request, arg, name=None, default=None):
    """
    For use with values returned from parse_quoted_separated or given
    as macro parameters, return an integer from a unicode string
    containing the decimal representation of a number.
    None is a valid input and yields the default value.

    @param request: A request instance
    @param arg: The argument, may be None or a unicode string
    @param name: Name of the argument, for error messages
    @param default: default value if arg is None
    @rtype: int or None
    @returns: the integer value of the string (or default value)
    """
    assert default is None or isinstance(default, (int, long))
    if arg is None:
        return default
    elif not isinstance(arg, unicode):
        raise TypeError('Argument must be None or unicode')
    try:
        return int(arg)
    except ValueError:
        if name:
            raise ValueError(
                _('Argument "%s" must be an integer value, not "%s"') % (
                    name, arg))
        else:
            raise ValueError(
                _('Argument must be an integer value, not "%s"') % arg)


def get_float(request, arg, name=None, default=None):
    """
    For use with values returned from parse_quoted_separated or given
    as macro parameters, return a float from a unicode string.
    None is a valid input and yields the default value.

    @param request: A request instance
    @param arg: The argument, may be None or a unicode string
    @param name: Name of the argument, for error messages
    @param default: default return value if arg is None
    @rtype: float or None
    @returns: the float value of the string (or default value)
    """
    assert default is None or isinstance(default, (int, long, float))
    if arg is None:
        return default
    elif not isinstance(arg, unicode):
        raise TypeError('Argument must be None or unicode')
    try:
        return float(arg)
    except ValueError:
        if name:
            raise ValueError(
                _('Argument "%s" must be a floating point value, not "%s"') % (
                    name, arg))
        else:
            raise ValueError(
                _('Argument must be a floating point value, not "%s"') % arg)


def get_complex(request, arg, name=None, default=None):
    """
    For use with values returned from parse_quoted_separated or given
    as macro parameters, return a complex from a unicode string.
    None is a valid input and yields the default value.

    @param request: A request instance
    @param arg: The argument, may be None or a unicode string
    @param name: Name of the argument, for error messages
    @param default: default return value if arg is None
    @rtype: complex or None
    @returns: the complex value of the string (or default value)
    """
    assert default is None or isinstance(default, (int, long, float, complex))
    if arg is None:
        return default
    elif not isinstance(arg, unicode):
        raise TypeError('Argument must be None or unicode')
    try:
        # allow writing 'i' instead of 'j'
        arg = arg.replace('i', 'j').replace('I', 'j')
        return complex(arg)
    except ValueError:
        if name:
            raise ValueError(
                _('Argument "%s" must be a complex value, not "%s"') % (
                    name, arg))
        else:
            raise ValueError(
                _('Argument must be a complex value, not "%s"') % arg)


def get_unicode(request, arg, name=None, default=None):
    """
    For use with values returned from parse_quoted_separated or given
    as macro parameters, return a unicode string from a unicode string.
    None is a valid input and yields the default value.

    @param request: A request instance
    @param arg: The argument, may be None or a unicode string
    @param name: Name of the argument, for error messages
    @param default: default return value if arg is None;
    @rtype: unicode or None
    @returns: the unicode string (or default value)
    """
    assert default is None or isinstance(default, unicode)
    if arg is None:
        return default
    elif not isinstance(arg, unicode):
        raise TypeError('Argument must be None or unicode')

    return arg


def get_choice(request, arg, name=None, choices=[None], default_none=False):
    """
    For use with values returned from parse_quoted_separated or given
    as macro parameters, return a unicode string that must be in the
    choices given. None is a valid input and yields first of the valid
    choices.

    @param request: A request instance
    @param arg: The argument, may be None or a unicode string
    @param name: Name of the argument, for error messages
    @param choices: the possible choices
    @param default_none: If False (default), get_choice returns first available
                         choice if arg is None. If True, get_choice returns
                         None if arg is None. This is useful if some arg value
                         is required (no default choice).
    @rtype: unicode or None
    @returns: the unicode string (or default value)
    """
    assert isinstance(choices, (tuple, list))
    if arg is None:
        if default_none:
            return None
        else:
            return choices[0]
    elif not isinstance(arg, unicode):
        raise TypeError('Argument must be None or unicode')
    elif not arg in choices:
        if name:
            raise ValueError(
                _('Argument "%s" must be one of "%s", not "%s"') % (
                    name, '", "'.join([repr(choice) for choice in choices]),
                    arg))
        else:
            raise ValueError(
                _('Argument must be one of "%s", not "%s"') % (
                    '", "'.join([repr(choice) for choice in choices]), arg))

    return arg


class IEFArgument:
    """
    Base class for new argument parsers for
    invoke_extension_function.
    """
    def __init__(self):
        pass

    def parse_argument(self, s):
        """
        Parse the argument given in s (a string) and return
        the argument for the extension function.
        """
        raise NotImplementedError

    def get_default(self):
        """
        Return the default for this argument.
        """
        raise NotImplementedError


class UnitArgument(IEFArgument):
    """
    Argument class for invoke_extension_function that forces
    having any of the specified units given for a value.

    Note that the default unit is "mm".

    Use, for example, "UnitArgument('7mm', float, ['%', 'mm'])".

    If the defaultunit parameter is given, any argument that
    can be converted into the given argtype is assumed to have
    the default unit. NOTE: This doesn't work with a choice
    (tuple or list) argtype.
    """
    def __init__(self, default, argtype, units=['mm'], defaultunit=None):
        """
        Initialise a UnitArgument giving the default,
        argument type and the permitted units.
        """
        IEFArgument.__init__(self)
        self._units = list(units)
        self._units.sort(lambda x, y: len(y) - len(x))
        self._type = argtype
        self._defaultunit = defaultunit
        assert defaultunit is None or defaultunit in units
        if default is not None:
            self._default = self.parse_argument(default)
        else:
            self._default = None

    def parse_argument(self, s):
        for unit in self._units:
            if s.endswith(unit):
                ret = (self._type(s[:len(s) - len(unit)]), unit)
                return ret
        if self._defaultunit is not None:
            try:
                return (self._type(s), self._defaultunit)
            except ValueError:
                pass
        units = ', '.join(self._units)
        ## XXX: how can we translate this?
        raise ValueError("Invalid unit in value %s (allowed units: %s)" % (s, units))

    def get_default(self):
        return self._default


class required_arg:
    """
    Wrap a type in this class and give it as default argument
    for a function passed to invoke_extension_function() in
    order to get generic checking that the argument is given.
    """
    def __init__(self, argtype):
        """
        Initialise a required_arg
        @param argtype: the type the argument should have
        """
        if not (argtype in (bool, int, long, float, complex, unicode) or
                isinstance(argtype, (IEFArgument, tuple, list))):
            raise TypeError("argtype must be a valid type")
        self.argtype = argtype


def invoke_extension_function(request, function, args, fixed_args=[]):
    """
    Parses arguments for an extension call and calls the extension
    function with the arguments.

    If the macro function has a default value that is a bool,
    int, long, float or unicode object, then the given value
    is converted to the type of that default value before passing
    it to the macro function. That way, macros need not call the
    wikiutil.get_* functions for any arguments that have a default.

    @param request: the request object
    @param function: the function to invoke
    @param args: unicode string with arguments (or evaluating to False)
    @param fixed_args: fixed arguments to pass as the first arguments
    @returns: the return value from the function called
    """
    from inspect import getargspec, isfunction, isclass, ismethod

    def _convert_arg(request, value, default, name=None):
        """
        Using the get_* functions, convert argument to the type of the default
        if that is any of bool, int, long, float or unicode; if the default
        is the type itself then convert to that type (keeps None) or if the
        default is a list require one of the list items.

        In other cases return the value itself.
        """
        # if extending this, extend required_arg as well!
        if isinstance(default, bool):
            return get_bool(request, value, name, default)
        elif isinstance(default, (int, long)):
            return get_int(request, value, name, default)
        elif isinstance(default, float):
            return get_float(request, value, name, default)
        elif isinstance(default, complex):
            return get_complex(request, value, name, default)
        elif isinstance(default, unicode):
            return get_unicode(request, value, name, default)
        elif isinstance(default, (tuple, list)):
            return get_choice(request, value, name, default)
        elif default is bool:
            return get_bool(request, value, name)
        elif default is int or default is long:
            return get_int(request, value, name)
        elif default is float:
            return get_float(request, value, name)
        elif default is complex:
            return get_complex(request, value, name)
        elif isinstance(default, IEFArgument):
            # defaults handled later
            if value is None:
                return None
            return default.parse_argument(value)
        elif isinstance(default, required_arg):
            if isinstance(default.argtype, (tuple, list)):
                # treat choice specially and return None if no choice
                # is given in the value
                return get_choice(request, value, name, list(default.argtype),
                       default_none=True)
            else:
                return _convert_arg(request, value, default.argtype, name)
        return value

    assert isinstance(fixed_args, (list, tuple))

    kwargs = {}
    kwargs_to_pass = {}
    trailing_args = []

    if args:
        assert isinstance(args, unicode)

        positional, keyword, trailing = parse_quoted_separated(args)

        for kw in keyword:
            try:
                kwargs[str(kw)] = keyword[kw]
            except UnicodeEncodeError:
                kwargs_to_pass[kw] = keyword[kw]

        trailing_args.extend(trailing)

    else:
        positional = []

    if isfunction(function) or ismethod(function):
        argnames, varargs, varkw, defaultlist = getargspec(function)
    elif isclass(function):
        (argnames, varargs,
         varkw, defaultlist) = getargspec(function.__init__.im_func)
    else:
        raise TypeError('function must be a function, method or class')

    # self is implicit!
    if ismethod(function) or isclass(function):
        argnames = argnames[1:]

    fixed_argc = len(fixed_args)
    argnames = argnames[fixed_argc:]
    argc = len(argnames)
    if not defaultlist:
        defaultlist = []

    # if the fixed parameters have defaults too...
    if argc < len(defaultlist):
        defaultlist = defaultlist[fixed_argc:]
    defstart = argc - len(defaultlist)

    defaults = {}
    # reverse to be able to pop() things off
    positional.reverse()
    allow_kwargs = False
    allow_trailing = False
    # convert all arguments to keyword arguments,
    # fill all arguments that weren't given with None
    for idx in range(argc):
        argname = argnames[idx]
        if argname == '_kwargs':
            allow_kwargs = True
            continue
        if argname == '_trailing_args':
            allow_trailing = True
            continue
        if positional:
            kwargs[argname] = positional.pop()
        if not argname in kwargs:
            kwargs[argname] = None
        if idx >= defstart:
            defaults[argname] = defaultlist[idx - defstart]

    if positional:
        if not allow_trailing:
            raise ValueError(_('Too many arguments'))
        trailing_args.extend(positional)

    if trailing_args:
        if not allow_trailing:
            raise ValueError(_('Cannot have arguments without name following'
                               ' named arguments'))
        kwargs['_trailing_args'] = trailing_args

    # type-convert all keyword arguments to the type
    # that the default value indicates
    for argname in kwargs.keys()[:]:
        if argname in defaults:
            # the value of 'argname' from kwargs will be put into the
            # macro's 'argname' argument, so convert that giving the
            # name to the converter so the user is told which argument
            # went wrong (if it does)
            kwargs[argname] = _convert_arg(request, kwargs[argname],
                                           defaults[argname], argname)
            if kwargs[argname] is None:
                if isinstance(defaults[argname], required_arg):
                    raise ValueError(_('Argument "%s" is required') % argname)
                if isinstance(defaults[argname], IEFArgument):
                    kwargs[argname] = defaults[argname].get_default()

        if not argname in argnames:
            # move argname into _kwargs parameter
            kwargs_to_pass[argname] = kwargs[argname]
            del kwargs[argname]

    if kwargs_to_pass:
        kwargs['_kwargs'] = kwargs_to_pass
        if not allow_kwargs:
            raise ValueError(_(u'No argument named "%s"') % (
                kwargs_to_pass.keys()[0]))

    return function(*fixed_args, **kwargs)


class ParameterParser:
    """ MoinMoin macro parameter parser

        Parses a given parameter string, separates the individual parameters
        and detects their type.

        Possible parameter types are:

        Name      | short  | example
        ----------------------------
         Integer  | i      | -374
         Float    | f      | 234.234 23.345E-23
         String   | s      | 'Stri\'ng'
         Boolean  | b      | 0 1 True false
         Name     |        | case_sensitive | converted to string

        So say you want to parse three things, name, age and if the
        person is male or not:

        The pattern will be: %(name)s%(age)i%(male)b

        As a result, the returned dict will put the first value into
        male, second into age etc. If some argument is missing, it will
        get None as its value. This also means that all the identifiers
        in the pattern will exist in the dict, they will just have the
        value None if they were not specified by the caller.

        So if we call it with the parameters as follows:
            ("John Smith", 18)
        this will result in the following dict:
            {"name": "John Smith", "age": 18, "male": None}

        Another way of calling would be:
            ("John Smith", male=True)
        this will result in the following dict:
            {"name": "John Smith", "age": None, "male": True}
    """

    def __init__(self, pattern):
        # parameter_re = "([^\"',]*(\"[^\"]*\"|'[^']*')?[^\"',]*)[,)]"
        name = "(?P<%s>[a-zA-Z_][a-zA-Z0-9_]*)"
        int_re = r"(?P<int>-?\d+)"
        bool_re = r"(?P<bool>(([10])|([Tt]rue)|([Ff]alse)))"
        float_re = r"(?P<float>-?\d+\.\d+([eE][+-]?\d+)?)"
        string_re = (r"(?P<string>('([^']|(\'))*?')|" +
                                r'("([^"]|(\"))*?"))')
        name_re = name % "name"
        name_param_re = name % "name_param"

        param_re = r"\s*(\s*%s\s*=\s*)?(%s|%s|%s|%s|%s)\s*(,|$)" % (
                   name_re, float_re, int_re, bool_re, string_re, name_param_re)
        self.param_re = re.compile(param_re, re.U)
        self._parse_pattern(pattern)

    def _parse_pattern(self, pattern):
        param_re = r"(%(?P<name>\(.*?\))?(?P<type>[ibfs]{1,3}))|\|"
        i = 0
        # TODO: Optionals aren't checked.
        self.optional = []
        named = False
        self.param_list = []
        self.param_dict = {}

        for match in re.finditer(param_re, pattern):
            if match.group() == "|":
                self.optional.append(i)
                continue
            self.param_list.append(match.group('type'))
            if match.group('name'):
                named = True
                self.param_dict[match.group('name')[1:-1]] = i
            elif named:
                raise ValueError("Named parameter expected")
            i += 1

    def __str__(self):
        return "%s, %s, optional:%s" % (self.param_list, self.param_dict,
                                        self.optional)

    def parse_parameters(self, params):
        # Default list/dict entries to None
        parameter_list = [None] * len(self.param_list)
        parameter_dict = dict([(key, None) for key in self.param_dict])
        check_list = [0] * len(self.param_list)

        i = 0
        start = 0
        fixed_count = 0
        named = False

        while start < len(params):
            match = re.match(self.param_re, params[start:])
            if not match:
                raise ValueError("malformed parameters")
            start += match.end()
            if match.group("int"):
                pvalue = int(match.group("int"))
                ptype = 'i'
            elif match.group("bool"):
                pvalue = (match.group("bool") == "1") or (match.group("bool") == "True") or (match.group("bool") == "true")
                ptype = 'b'
            elif match.group("float"):
                pvalue = float(match.group("float"))
                ptype = 'f'
            elif match.group("string"):
                pvalue = match.group("string")[1:-1]
                ptype = 's'
            elif match.group("name_param"):
                pvalue = match.group("name_param")
                ptype = 'n'
            else:
                raise ValueError("Parameter parser code does not fit param_re regex")

            name = match.group("name")
            if name:
                if name not in self.param_dict:
                    # TODO we should think on inheritance of parameters
                    raise ValueError("unknown parameter name '%s'" % name)
                nr = self.param_dict[name]
                if check_list[nr]:
                    raise ValueError("parameter '%s' specified twice" % name)
                else:
                    check_list[nr] = 1
                pvalue = self._check_type(pvalue, ptype, self.param_list[nr])
                parameter_dict[name] = pvalue
                parameter_list[nr] = pvalue
                named = True
            elif named:
                raise ValueError("only named parameters allowed after first named parameter")
            else:
                nr = i
                if nr not in self.param_dict.values():
                    fixed_count = nr + 1
                parameter_list[nr] = self._check_type(pvalue, ptype, self.param_list[nr])

            # Let's populate and map our dictionary to what's been found
            for name in self.param_dict:
                tmp = self.param_dict[name]
                parameter_dict[name] = parameter_list[tmp]

            i += 1

        for i in range(fixed_count):
            parameter_dict[i] = parameter_list[i]

        return fixed_count, parameter_dict

    def _check_type(self, pvalue, ptype, format):
        if ptype == 'n' and 's' in format: # n as s
            return pvalue

        if ptype in format:
            return pvalue # x -> x

        if ptype == 'i':
            if 'f' in format:
                return float(pvalue) # i -> f
            elif 'b' in format:
                return pvalue != 0 # i -> b
        elif ptype == 's':
            if 'b' in format:
                if pvalue.lower() == 'false':
                    return False # s-> b
                elif pvalue.lower() == 'true':
                    return True # s-> b
                else:
                    raise ValueError('%r does not match format %r' % (pvalue, format))

        if 's' in format: # * -> s
            return str(pvalue)

        raise ValueError('%r does not match format %r' % (pvalue, format))


#############################################################################
### Misc
#############################################################################
def normalize_pagename(name, cfg):
    """ Normalize page name

    Prevent creating page names with invisible characters or funny
    whitespace that might confuse the users or abuse the wiki, or
    just does not make sense.

    Restrict even more group pages, so they can be used inside acl lines.

    @param name: page name, unicode
    @rtype: unicode
    @return: decoded and sanitized page name
    """
    # Strip invalid characters
    name = config.page_invalid_chars_regex.sub(u'', name)

    # Split to pages and normalize each one
    pages = name.split(u'/')
    normalized = []
    for page in pages:
        # Ignore empty or whitespace only pages
        if not page or page.isspace():
            continue

        # Cleanup group pages.
        # Strip non alpha numeric characters, keep white space
        if isGroupItem(page):
            page = u''.join([c for c in page
                             if c.isalnum() or c.isspace()])

        # Normalize white space. Each name can contain multiple
        # words separated with only one space. Split handle all
        # 30 unicode spaces (isspace() == True)
        page = u' '.join(page.split())

        normalized.append(page)

    # Assemble components into full pagename
    name = u'/'.join(normalized)
    return name


def drawing2fname(drawing):
    config.drawing_extensions = ['.tdraw', '.adraw',
                                 '.svg',
                                 '.png', '.jpg', '.jpeg', '.gif',
                                ]
    fname, ext = os.path.splitext(drawing)
    # note: do not just check for empty extension or stuff like drawing:foo.bar
    # will fail, instead of being expanded to foo.bar.tdraw
    if ext not in config.drawing_extensions:
        # for backwards compatibility, twikidraw is the default:
        drawing += '.tdraw'
    return drawing


def getUnicodeIndexGroup(name):
    """
    Return a group letter for `name`, which must be a unicode string.
    Currently supported: Hangul Syllables (U+AC00 - U+D7AF)

    @param name: a string
    @rtype: string
    @return: group letter or None
    """
    c = name[0]
    if u'\uAC00' <= c <= u'\uD7AF': # Hangul Syllables
        return unichr(0xac00 + (int(ord(c) - 0xac00) / 588) * 588)
    else:
        return c.upper() # we put lower and upper case words into the same index group


def is_URL(arg, schemas=config.url_schemas):
    """ Return True if arg is a URL (with a schema given in the schemas list).

        Note: there are not that many requirements for generic URLs, basically
        the only mandatory requirement is the ':' between schema and rest.
        Schema itself could be anything, also the rest (but we only support some
        schemas, as given in config.url_schemas, so it is a bit less ambiguous).
    """
    if ':' not in arg:
        return False
    for schema in schemas:
        if arg.startswith(schema + ':'):
            return True
    return False


def containsConflictMarker(text):
    """ Returns true if there is a conflict marker in the text. """
    return "/!\\ '''Edit conflict" in text

def anchor_name_from_text(text):
    '''
    Generate an anchor name from the given text.
    This function generates valid HTML IDs matching: [A-Za-z][A-Za-z0-9:_.-]*
    Note: this transformation has a special feature: when you feed it with a
          valid ID/name, it will return it without modification (identity
          transformation).
    '''
    quoted = werkzeug.url_quote_plus(text, charset='utf-7', safe=':')
    res = quoted.replace('%', '.').replace('+', '_')
    if not res[:1].isalpha():
        return 'A%s' % res
    return res

def split_anchor(pagename):
    """
    Split a pagename that (optionally) has an anchor into the real pagename
    and the anchor part. If there is no anchor, it returns an empty string
    for the anchor.

    Note: if pagename contains a # (as part of the pagename, not as anchor),
          you can use a trick to make it work nevertheless: just append a
          # at the end:
          "C##" returns ("C#", "")
          "Problem #1#" returns ("Problem #1", "")

    TODO: We shouldn't deal with composite pagename#anchor strings, but keep
          it separate.
          Current approach: [[pagename#anchor|label|attr=val,&qarg=qval]]
          Future approach:  [[pagename|label|attr=val,&qarg=qval,#anchor]]
          The future approach will avoid problems when there is a # in the
          pagename part (and no anchor). Also, we need to append #anchor
          at the END of the generated URL (AFTER the query string).
    """
    parts = pagename.rsplit('#', 1)
    if len(parts) == 2:
        return parts
    else:
        return pagename, ""


def split_body(body):
    """ Extract the processing instructions / acl / etc. at the beginning of a page's body.

        Hint: if you have a Page object p, you already have the result of this function in
              p.meta and (even better) parsed/processed stuff in p.pi.

        Returns a list of (pi, restofline) tuples and a string with the rest of the body.
    """
    pi = {}
    while body.startswith('#'):
        try:
            line, body = body.split('\n', 1) # extract first line
        except ValueError:
            line = body
            body = ''

        # end parsing on empty (invalid) PI
        if line == "#":
            body = line + '\n' + body
            break

        if line[1] == '#':# two hash marks are a comment
            comment = line[2:]
            if not comment.startswith(' '):
                # we don't require a blank after the ##, so we put one there
                comment = ' ' + comment
                line = '##%s' % comment

        verb, args = (line[1:] + ' ').split(' ', 1) # split at the first blank
        pi.setdefault(verb.lower(), []).append(args.strip())

    for key, value in pi.iteritems():
        if key in ['#', ]:
            # transform the lists to tuples:
            pi[key] = tuple(value)
        elif key in ['acl', ]:
            # join the list of values to a single value
            pi[key] = u' '.join(value)
        else:
            # for keys that can't occur multiple times, don't use a list:
            pi[key] = value[-1] # use the last value to copy 1.9 parsing behaviour

    return pi, body


def add_metadata_to_body(metadata, data):
    """
    Adds the processing instructions to the data.
    """
    from MoinMoin.items import NAME, ACL, MIMETYPE, LANGUAGE

    meta_keys = [NAME, ACL, MIMETYPE, LANGUAGE, ]

    metadata_data = ""
    for key, value in metadata.iteritems():
        if key not in meta_keys:
            continue
        # special handling for list metadata
        if isinstance(value, (list, tuple)):
            for line in value:
                metadata_data += "#%s %s\n" % (key, line)
        else:
            metadata_data += "#%s %s\n" % (key, value)
    return metadata_data + data


def get_hostname(addr):
    """
    Looks up the hostname depending on the configuration.
    """
    if app.cfg.log_reverse_dns_lookups:
        import socket
        try:
            hostname = socket.gethostbyaddr(addr)[0]
            hostname = unicode(hostname, config.charset)
        except (socket.error, UnicodeError):
            hostname = addr
    else:
        hostname = addr
    return hostname

