# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Configuration defaults class

    @copyright: 2000-2004 Juergen Hermann <jh@web.de>,
                2005-2010 MoinMoin:ThomasWaldmann,
                2008      MoinMoin:JohannesBerg,
                2010      MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""

import re
import os
import sys

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import _, N_
from MoinMoin import config, error, util
from MoinMoin import datastruct
from MoinMoin.auth import MoinAuth
import MoinMoin.auth as authmodule
from MoinMoin.security import AccessControlList


class CacheClass(object):
    """ just a container for stuff we cache """
    pass


class ConfigFunctionality(object):
    """ Configuration base class with config class behaviour.

        This class contains the functionality for the DefaultConfig
        class for the benefit of the WikiConfig macro.
    """

    # attributes of this class that should not be shown
    # in the WikiConfig() macro.
    siteid = None
    cache = None
    mail_enabled = None
    auth_can_logout = None
    auth_have_login = None
    auth_login_inputs = None
    _site_plugin_lists = None
    xapian_searchers = None
    moinmoin_dir = None

    def __init__(self):
        """ Init Config instance """
        self.cache = CacheClass()

        if self.config_check_enabled:
            self._config_check()

        # define directories
        self.moinmoin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
        data_dir = os.path.normpath(self.data_dir)
        self.data_dir = data_dir
        for dirname in ['cache', 'plugin', 'tmp', ]:
            name = dirname + '_dir'
            if not getattr(self, name, None):
                setattr(self, name, os.path.abspath(os.path.join(data_dir, dirname)))

        # Try to decode certain names which allow unicode
        self._decode()

        # After that, pre-compile some regexes
        self.cache.item_category_regex = re.compile(self.item_category_regex, re.UNICODE)
        self.cache.item_dict_regex = re.compile(self.item_dict_regex, re.UNICODE)
        self.cache.item_group_regex = re.compile(self.item_group_regex, re.UNICODE)
        self.cache.item_template_regex = re.compile(self.item_template_regex, re.UNICODE)

        # the ..._regexact versions only match if nothing is left (exact match)
        self.cache.item_category_regexact = re.compile(u'^%s$' % self.item_category_regex, re.UNICODE)
        self.cache.item_dict_regexact = re.compile(u'^%s$' % self.item_dict_regex, re.UNICODE)
        self.cache.item_group_regexact = re.compile(u'^%s$' % self.item_group_regex, re.UNICODE)
        self.cache.item_template_regexact = re.compile(u'^%s$' % self.item_template_regex, re.UNICODE)

        if not isinstance(self.superuser, list):
            msg = """The superuser setting in your wiki configuration is not a list
                     (e.g. ['Sample User', 'AnotherUser']).
                     Please change it in your wiki configuration and try again."""
            raise error.ConfigurationError(msg)

        self._loadPluginModule()

        # Preparse user dicts
        self._fillDicts()

        # Normalize values
        self.language_default = self.language_default.lower()

        # Use site name as default name-logo
        if self.logo_string is None:
            self.logo_string = self.sitename

        # post process

        self.auth_can_logout = []
        self.auth_login_inputs = []
        found_names = []
        for auth in self.auth:
            if not auth.name:
                raise error.ConfigurationError("Auth methods must have a name.")
            if auth.name in found_names:
                raise error.ConfigurationError("Auth method names must be unique.")
            found_names.append(auth.name)
            if auth.logout_possible and auth.name:
                self.auth_can_logout.append(auth.name)
            for input in auth.login_inputs:
                if not input in self.auth_login_inputs:
                    self.auth_login_inputs.append(input)
        self.auth_have_login = len(self.auth_login_inputs) > 0
        self.auth_methods = found_names

        # internal dict for plugin `modules' lists
        self._site_plugin_lists = {}

        # we replace any string placeholders with config values
        # e.g u'%(page_front_page)s' % self
        self.navi_bar = [elem % self for elem in self.navi_bar]

        # check if python-xapian is installed
        if self.xapian_search:
            try:
                import xapian
            except ImportError, err:
                self.xapian_search = False
                logging.error("xapian_search was auto-disabled because python-xapian is not installed [%s]." % str(err))

        # list to cache xapian searcher objects
        self.xapian_searchers = []

        # check if mail is possible and set flag:
        self.mail_enabled = (self.mail_smarthost is not None or self.mail_sendmail is not None) and self.mail_from
        self.mail_enabled = self.mail_enabled and True or False

        # Cache variables for the properties below
        if self.url_prefix_local is None:
            self.url_prefix_local = self.url_prefix_static

        if self.namespace_mapping is None:
            raise error.ConfigurationError("No storage configuration specified! You need to define a namespace_mapping. " + \
                                           "For further reference, please see HelpOnStorageConfiguration.")

        if self.secrets is None:  # admin did not setup a real secret, so make up something
            self.secrets = self.calc_secrets()

        secret_key_names = ['action/cache', 'wikiutil/tickets', ]

        secret_min_length = 10
        if isinstance(self.secrets, str):
            if len(self.secrets) < secret_min_length:
                raise error.ConfigurationError("The secrets = '...' wiki config setting is a way too short string (minimum length is %d chars)!" % (
                    secret_min_length))
            # for lazy people: set all required secrets to same value
            secrets = {}
            for key in secret_key_names:
                secrets[key] = self.secrets
            self.secrets = secrets

        # we check if we have all secrets we need and that they have minimum length
        for secret_key_name in secret_key_names:
            try:
                secret = self.secrets[secret_key_name]
                if len(secret) < secret_min_length:
                    raise ValueError
            except (KeyError, ValueError):
                raise error.ConfigurationError("You must set a (at least %d chars long) secret string for secrets['%s']!" % (
                    secret_min_length, secret_key_name))

    def calc_secrets(self):
        """ make up some 'secret' using some config values """
        varnames = ['data_dir', 'language_default',
                    'mail_smarthost', 'mail_from', 'page_front_page',
                    'theme_default', 'sitename', 'logo_string',
                    'interwikiname', 'user_homewiki', ]
        secret = ''
        for varname in varnames:
            var = getattr(self, varname, None)
            if isinstance(var, (str, unicode)):
                secret += repr(var)
        return secret

    def _config_check(self):
        """ Check namespace and warn about unknown names

        Warn about names which are not used by DefaultConfig, except
        modules, classes, _private or __magic__ names.

        This check is disabled by default, when enabled, it will show an
        error message with unknown names.
        """
        unknown = ['"%s"' % name for name in dir(self)
                  if not name.startswith('_') and
                  name not in DefaultConfig.__dict__ and
                  not isinstance(getattr(self, name), (type(sys), type(DefaultConfig)))]
        if unknown:
            msg = """
Unknown configuration options: %s.

For more information, visit HelpOnConfiguration. Please check your
configuration for typos before requesting support or reporting a bug.
""" % ', '.join(unknown)
            raise error.ConfigurationError(msg)

    def _decode(self):
        """ Try to decode certain names, ignore unicode values

        Try to decode str using utf-8. If the decode fail, raise FatalError.

        Certain config variables should contain unicode values, and
        should be defined with u'text' syntax. Python decode these if
        the file have a 'coding' line.

        This will allow utf-8 users to use simple strings using, without
        using u'string'. Other users will have to use u'string' for
        these names, because we don't know what is the charset of the
        config files.
        """
        charset = 'utf-8'
        message = u"""
"%(name)s" configuration variable is a string, but should be
unicode. Use %(name)s = u"value" syntax for unicode variables.

Also check your "-*- coding -*-" line at the top of your configuration
file. It should match the actual charset of the configuration file.
"""

        decode_names = (
            'sitename', 'interwikiname', 'user_homewiki', 'logo_string', 'navi_bar',
            'page_front_page', 'page_license_page', 'mail_from',
            'item_category_regex', 'item_dict_regex', 'item_group_regex', 'item_template_regex',
            )

        for name in decode_names:
            attr = getattr(self, name, None)
            if attr:
                # Try to decode strings
                if isinstance(attr, str):
                    try:
                        setattr(self, name, unicode(attr, charset))
                    except UnicodeError:
                        raise error.ConfigurationError(message %
                                                       {'name': name})
                # Look into lists and try to decode strings inside them
                elif isinstance(attr, list):
                    for i in xrange(len(attr)):
                        item = attr[i]
                        if isinstance(item, str):
                            try:
                                attr[i] = unicode(item, charset)
                            except UnicodeError:
                                raise error.ConfigurationError(message %
                                                               {'name': name})

    def _loadPluginModule(self):
        """
        import all plugin modules

        To be able to import plugin from arbitrary path, we have to load
        the base package once using imp.load_module. Later, we can use
        standard __import__ call to load plugins in this package.

        Since each configured plugin path has unique plugins, we load the
        plugin packages as "moin_plugin_<sha1(path)>.plugin".
        """
        import imp
        import hashlib

        plugin_dirs = [self.plugin_dir] + self.plugin_dirs
        self._plugin_modules = []

        try:
            # Lock other threads while we check and import
            imp.acquire_lock()
            try:
                for pdir in plugin_dirs:
                    csum = 'p_%s' % hashlib.new('sha1', pdir).hexdigest()
                    modname = '%s.%s' % (self.siteid, csum)
                    # If the module is not loaded, try to load it
                    if not modname in sys.modules:
                        # Find module on disk and try to load - slow!
                        abspath = os.path.abspath(pdir)
                        parent_dir, pname = os.path.split(abspath)
                        fp, path, info = imp.find_module(pname, [parent_dir])
                        try:
                            # Load the module and set in sys.modules
                            module = imp.load_module(modname, fp, path, info)
                            # XXX for what was this good for?:
                            #setattr(sys.modules[self.siteid], 'csum', module)
                        finally:
                            # Make sure fp is closed properly
                            if fp:
                                fp.close()
                    if modname not in self._plugin_modules:
                        self._plugin_modules.append(modname)
            finally:
                imp.release_lock()
        except ImportError, err:
            msg = """
Could not import plugin package "%(path)s" because of ImportError:
%(err)s.

Make sure your data directory path is correct, check permissions, and
that the data/plugin directory has an __init__.py file.
""" % {
    'path': pdir,
    'err': str(err),
}
            raise error.ConfigurationError(msg)

    def _fillDicts(self):
        """ fill config dicts

        Fills in missing dict keys of derived user config by copying
        them from this base class.
        """
        # user checkbox defaults
        for key, value in DefaultConfig.user_checkbox_defaults.items():
            if key not in self.user_checkbox_defaults:
                self.user_checkbox_defaults[key] = value

    def __getitem__(self, item):
        """ Make it possible to access a config object like a dict """
        return getattr(self, item)


class DefaultConfig(ConfigFunctionality):
    """ Configuration base class with default config values
        (added below)
    """
    # Do not add anything into this class. Functionality must
    # be added above to avoid having the methods show up in
    # the WikiConfig macro. Settings must be added below to
    # the options dictionary.


def _default_password_checker(cfg, username, password):
    """ Check if a password is secure enough.
        We use a built-in check to get rid of the worst passwords.

        We do NOT use cracklib / python-crack here any more because it is
        not thread-safe (we experienced segmentation faults when using it).

        If you don't want to check passwords, use password_checker = None.

        @return: None if there is no problem with the password,
                 some unicode object with an error msg, if the password is problematic.
    """
    # in any case, do a very simple built-in check to avoid the worst passwords
    if len(password) < 6:
        return _("Password is too short.")
    if len(set(password)) < 4:
        return _("Password has not enough different characters.")

    username_lower = username.lower()
    password_lower = password.lower()
    if username in password or password in username or \
       username_lower in password_lower or password_lower in username_lower:
        return _("Password is too easy (password contains name or name contains password).")

    keyboards = (ur"`1234567890-=qwertyuiop[]\asdfghjkl;'zxcvbnm,./", # US kbd
                 ur"^1234567890ß´qwertzuiopü+asdfghjklöä#yxcvbnm,.-", # german kbd
                ) # add more keyboards!
    for kbd in keyboards:
        rev_kbd = kbd[::-1]
        if password in kbd or password in rev_kbd or \
           password_lower in kbd or password_lower in rev_kbd:
            return _("Password is too easy (keyboard sequence).")
    return None


class DefaultExpression(object):
    def __init__(self, exprstr):
        self.text = exprstr
        self.value = eval(exprstr)


#
# Options that are not prefixed automatically with their
# group name, see below (at the options dict) for more
# information on the layout of this structure.
#
options_no_group_name = {
  # ==========================================================================
  'datastruct': ('Datastruct settings', None, (
    #('dicts', lambda cfg, request: datastruct.ConfigDicts(request, {}),
    ('dicts', lambda cfg, request: datastruct.WikiDicts(request),
     "function f(cfg, request) that returns a backend which is used to access dicts definitions."),
    ('groups', lambda cfg, request: datastruct.ConfigGroups(request, {}),
    #('groups', lambda cfg, request: datastruct.WikiGroups(request),
     "function f(cfg, request) that returns a backend which is used to access groups definitions."),
  )),
  # ==========================================================================
  'auth': ('Authentication / Authorization / Security settings', None, (
    ('superuser', [],
     "List of trusted user names with wiki system administration super powers (not to be confused with ACL admin rights!). Used for e.g. software installation, language installation via SystemPagesSetup and more. See also HelpOnSuperUser."),
    ('auth', DefaultExpression('[MoinAuth()]'),
     "list of auth objects, to be called in this order (see HelpOnAuthentication)"),
    ('auth_methods_trusted', ['http', 'given', ], # Note: 'http' auth method is currently just a redirect to 'given'
     'authentication methods for which users should be included in the special "Trusted" ACL group.'),
    ('secrets', None, """Either a long shared secret string used for multiple purposes or a dict {"purpose": "longsecretstring", ...} for setting up different shared secrets for different purposes. If you don't setup own secret(s), a secret string will be auto-generated from other config settings."""),
    # use sha512 as soon as we require python2.5 because sha1 is weak:
    ('hash_algorithm', 'sha1', "Name of hash algorithm used to compute data hashes"),
    ('SecurityPolicy',
     None,
     "Class object hook for implementing security restrictions or relaxations"),
    ('actions_excluded',
     ['copy',  # has questionable behaviour regarding subpages a user can't read, but can copy
     ],
     "Exclude unwanted actions (list of strings)"),

    ('password_checker', DefaultExpression('_default_password_checker'),
     'checks whether a password is acceptable (default check is length >= 6, at least 4 different chars, no keyboard sequence, not username used somehow (you can switch this off by using `None`)'),

  )),
  # ==========================================================================
  'spam_leech_dos': ('Anti-Spam/Leech/DOS',
  'These settings help limiting ressource usage and avoiding abuse.',
  (
    ('textchas', None,
     "Spam protection setup using site-specific questions/answers, see HelpOnSpam."),
    ('textchas_disabled_group', None,
     "Name of a group of trusted users who do not get asked !TextCha questions."),
  )),
  # ==========================================================================
  'style': ('Style / Theme / UI related',
  'These settings control how the wiki user interface will look like.',
  (
    ('sitename', u'Untitled Wiki',
     "Short description of your wiki site, displayed below the logo on each page, and used in RSS documents as the channel title [Unicode]"),
    ('interwikiname', None, "unique and stable InterWiki name (prefix, moniker) of the site [Unicode], or None"),
    ('logo_string', None, "The wiki logo top of page, HTML is allowed (`<img>` is possible as well) [Unicode]"),
    ('html_pagetitle', None, "Allows you to set a specific HTML page title (if None, it defaults to the value of `sitename`)"),
    ('navi_bar', [u'FindPage', u'HelpContents', ],
     'Most important page names. Users can add more names in their quick links in user preferences. To link to URL, use `u"[[url|link title]]"`, to use a shortened name for long page name, use `u"[[LongLongPageName|title]]"`. [list of Unicode strings]'),

    ('theme_default', 'modernized',
     "the name of the theme that is used by default (see HelpOnThemes)"),
    ('theme_force', False,
     "if True, do not allow to change the theme"),

    ('stylesheets', [],
     """
     List of tuples (media, csshref, title, alternate_stylesheet)
     to insert after theme css, before user css, see HelpOnThemes.
     Usage: [('screen', 'http://moinmo.in/static/alternate.css', 'Moin Other Style', True)]
     """),

     ('external_scripts', [],
      """
      List of tuples (type, href) to insert after Moin javascript.
      Usage: [('text/javascript', 'http://moinmo.in/static/script.js')]
      """),

    ('supplementation_item_names', [u'Discussion', ],
     "List of names of the supplementation (sub)items [unicode]"),

    ('interwiki_preferred', [], "In dialogues, show those wikis at the top of the list."),
    ('sistersites', [], "list of tuples `('WikiName', 'sisterpagelist_fetch_url')`"),

    ('trail_size', 5,
     "Number of items in the trail of recently visited items"),

    ('html_before_header', '', "Custom HTML markup sent ''before'' the system header / title area but after the body tag."),
    ('html_after_header', '', "Custom HTML markup sent ''after'' the system header / title area (and body tag)."),
    ('html_before_footer', '', "Custom HTML markup sent ''before'' the system footer."),
    ('html_after_footer', '', "Custom HTML markup sent ''after'' the system footer."),

    ('edit_bar', ['Show', 'Meta', 'Modify', 'Comments', 'Download', 'History', 'Subscribe', 'Quicklink', 'Index', 'Supplementation', 'ActionsMenu'],
     'list of edit bar entries'),
    ('history_count', (100, 200), "number of revisions shown for info/history action (default_count_shown, max_count_shown)"),

    ('show_hosts', True,
     "if True, show host names and IPs. Set to False to hide them."),
    ('show_interwiki', False,
     "if True, let the theme display your interwiki name"),
    ('show_names', True,
     "if True, show user names in the revision history and on Recent``Changes. Set to False to hide them."),
    ('show_section_numbers', False,
     'show section numbers in headings by default'),
    ('show_timings', False, "show some timing values at bottom of a page"),
    ('show_rename_redirect', False, "if True, offer creation of redirect pages when renaming wiki pages"),

    ('page_credits',
     [
       '<a href="http://moinmo.in/" title="This site uses the MoinMoin Wiki software.">MoinMoin Powered</a>',
       '<a href="http://moinmo.in/Python" title="MoinMoin is written in Python.">Python Powered</a>',
       '<a href="http://moinmo.in/GPL" title="MoinMoin is GPL licensed.">GPL licensed</a>',
       '<a href="http://validator.w3.org/check?uri=referer" title="Click here to validate this page.">Valid HTML 5</a>',
     ],
     'list with html fragments with logos or strings for crediting.'),
  )),
  # ==========================================================================
  'editor': ('Editor related', None, (
    ('editor_default', 'text', "Editor to use by default, 'text' or 'gui'"),
    ('editor_force', False, "if True, force using the default editor"),
    ('editor_ui', 'freechoice', "Editor choice shown on the user interface, 'freechoice' or 'theonepreferred'"),
    ('page_license_enabled', False, 'if True, show a license hint in page editor.'),
    ('page_license_page', u'WikiLicense', 'Page linked from the license hint. [Unicode]'),
    ('edit_locking', 'warn 10', "Editor locking policy: `None`, `'warn <timeout in minutes>'`, or `'lock <timeout in minutes>'`"),
    ('edit_ticketing', True, None),
    ('edit_rows', 20, "Default height of the edit box"),
  )),
  # ==========================================================================
  'data': ('Data storage', None, (
    ('data_dir', './data/', "Path to the data directory."),
    ('cache_dir', None, "Directory for caching, by default computed from `data_dir`/cache."),
    ('plugin_dir', None, "Plugin directory, by default computed to be `data_dir`/plugin."),
    ('plugin_dirs', [], "Additional plugin directories."),

    ('interwiki_map', {},
     "Dictionary of wiki_name -> wiki_url"),
    ('namespace_mapping', None,
    "This needs to point to a (correctly ordered!) list of tuples, each tuple containing: Namespace identifier, backend, acl protection to be applied to that backend. " + \
    "E.g.: [('/', FSBackend('wiki/data'), dict(default='All:read,write,create')), ]. Please see HelpOnStorageConfiguration for further reference."),
    ('load_xml', None,
     'If this points to an xml file, the file is loaded into the storage backend(s) upon first request.'),
    ('save_xml', None,
     'If this points to an xml file, the current storage backend(s) content is saved into that file upon the first request.'),
  )),
  # ==========================================================================
  'urls': ('URLs', None, (
    ('url_prefix_static', config.url_prefix_static,
     "used as the base URL for icons, css, etc."),
    ('url_prefix_local', None,
     "used as the base URL for some Javascript - set this to a URL on same server as the wiki if your url_prefix_static points to a different server."),

    ('url_mappings', {},
     "lookup table to remap URL prefixes (dict of {{{'prefix': 'replacement'}}}); especially useful in intranets, when whole trees of externally hosted documents move around"),

  )),
  # ==========================================================================
  'pages': ('Special page names', None, (
      ('page_front_page', u'Home',
     "Name of the front page. We don't expect you to keep the default. [Unicode]"),

    # the following regexes should match the complete name when used in free text
    # the group 'all' shall match all, while the group 'key' shall match the key only
    # e.g. CategoryFoo -> group 'all' ==  CategoryFoo, group 'key' == Foo
    # moin's code will add ^ / $ at beginning / end when needed
    ('item_category_regex', ur'(?P<all>Category(?P<key>(?!Template)\S+))',
     'Item names exactly matching this regex are regarded as Wiki categories [Unicode]'),
    ('item_dict_regex', ur'(?P<all>(?P<key>\S+)Dict)',
     'Item names exactly matching this regex are regarded as items containing variable dictionary definitions [Unicode]'),
    ('item_group_regex', ur'(?P<all>(?P<key>\S+)Group)',
     'Item names exactly matching this regex are regarded as items containing group definitions [Unicode]'),
    ('item_template_regex', ur'(?P<all>(?P<key>\S+)Template)',
     'Item names exactly matching this regex are regarded as items containing templates for new items [Unicode]'),
  )),
  # ==========================================================================
  'user': ('User Preferences related', None, (
    ('quicklinks_default', [],
     'List of preset quicklinks for a newly created user accounts. Existing accounts are not affected by this option whereas changes in navi_bar do always affect existing accounts. Preset quicklinks can be removed by the user in the user preferences menu, navi_bar settings not.'),
    ('subscribed_items_default', [],
     "List of item names used for presetting item subscriptions for newly created user accounts."),

    ('email_subscribed_events_default',
     [
        # XXX PageChangedEvent.__name__
        # XXX PageRenamedEvent.__name__
        # XXX PageDeletedEvent.__name__
        # XXX PageCopiedEvent.__name__
        # XXX PageRevertedEvent.__name__
     ], None),
  )),
  # ==========================================================================
  'various': ('Various', None, (
    ('bang_meta', True, 'if True, enable {{{!NoWikiName}}} markup'),

    ('config_check_enabled', False, "if True, check configuration for unknown settings."),

    ('html_head', '', "Additional <HEAD> tags, see HelpOnThemes."),
    ('html_head_queries', '<meta name="robots" content="noindex,nofollow">\n',
     "Additional <HEAD> tags for requests with query strings, like actions."),
    ('html_head_posts', '<meta name="robots" content="noindex,nofollow">\n',
     "Additional <HEAD> tags for POST requests."),
    ('html_head_index', '<meta name="robots" content="index,follow">\n',
     "Additional <HEAD> tags for some few index pages."),
    ('html_head_normal', '<meta name="robots" content="index,nofollow">\n',
     "Additional <HEAD> tags for most normal pages."),

    ('language_default', 'en', "Default language for user interface and page content, see HelpOnLanguages."),
    ('language_ignore_browser', False, "if True, ignore user's browser language settings, see HelpOnLanguages."),

    ('log_remote_addr', True,
     "if True, log the remote IP address (and maybe hostname)."),
    ('log_reverse_dns_lookups', True,
     "if True, do a reverse DNS lookup on page SAVE. If your DNS is broken, set this to False to speed up SAVE."),

    # some dangerous mimetypes (we don't use "content-disposition: inline" for them when a user
    # downloads such data, because the browser might execute e.g. Javascript contained
    # in the HTML and steal your moin session cookie or do other nasty stuff)
    ('mimetypes_xss_protect',
     [
       'text/html',
       'application/x-shockwave-flash',
       'application/xhtml+xml',
     ],
     '"content-disposition: inline" is not used for downloads of such data'),

    ('mimetypes_embed',
     [
       'application/x-dvi',
       'application/postscript',
       'application/pdf',
       'application/ogg',
       'application/vnd.visio',
       'image/x-ms-bmp',
       'image/svg+xml',
       'image/tiff',
       'image/x-photoshop',
       'audio/mpeg',
       'audio/midi',
       'audio/x-wav',
       'video/fli',
       'video/mpeg',
       'video/quicktime',
       'video/x-msvideo',
       'chemical/x-pdb',
       'x-world/x-vrml',
     ],
     'mimetypes that can be embedded by the [[HelpOnMacros/EmbedObject|EmbedObject macro]]'),

    ('refresh', None,
     "refresh = (minimum_delay_s, targets_allowed) enables use of `#refresh 5 PageName` processing instruction, targets_allowed must be either `'internal'` or `'external'`"),

    ('search_results_per_page', 25, "Number of hits shown per page in the search results"),

    ('siteid', 'MoinMoin', None), # XXX just default to some existing module name to
                                  # make plugin loader etc. work for now
  )),
}

#
# The 'options' dict carries default MoinMoin options. The dict is a
# group name to tuple mapping.
# Each group tuple consists of the following items:
#   group section heading, group help text, option list
#
# where each 'option list' is a tuple or list of option tuples
#
# each option tuple consists of
#   option name, default value, help text
#
# All the help texts will be displayed by the WikiConfigHelp() macro.
#
# Unlike the options_no_group_name dict, option names in this dict
# are automatically prefixed with "group name '_'" (i.e. the name of
# the group they are in and an underscore), e.g. the 'hierarchic'
# below creates an option called "acl_hierarchic".
#
# If you need to add a complex default expression that results in an
# object and should not be shown in the __repr__ form in WikiConfigHelp(),
# you can use the DefaultExpression class, see 'auth' above for example.
#
#
options = {
    'acl': ('Access control lists',
    'ACLs control who may do what, see HelpOnAccessControlLists.',
    (
      ('rights_valid', config.ACL_RIGHTS_VALID,
       "Valid tokens for right sides of ACL entries."),
    )),

    'ns': ('Storage Namespaces',
    "Storage namespaces can be defined for all sorts of data. All items sharing a common namespace as prefix" + \
    "are then stored within the same backend. The common prefix for all data is ''.",
    (
      ('content', '/', "All content is by default stored below /, hence the prefix is ''."),  # Not really necessary. Just for completeness.
      ('user_profile', 'UserProfile/', 'User profiles (i.e. user data, not their homepage) are stored in this namespace.'),
      ('user_homepage', 'User/', 'All user homepages are stored below this namespace.'),
      ('trash', 'Trash/', 'This is the namespace in which an item ends up when it is deleted.')
    )),

    'xapian': ('Xapian search', "Configuration of the Xapian based indexed search, see HelpOnXapian.", (
      ('search', False,
       "True to enable the fast, indexed search (based on the Xapian search library)"),
      ('index_dir', None,
       "Directory where the Xapian search index is stored (None = auto-configure wiki local storage)"),
      ('stemming', False,
       "True to enable Xapian word stemmer usage for indexing / searching."),
      ('index_history', False,
       "True to enable indexing of non-current page revisions."),
    )),

    'user': ('Users / User settings', None, (
      ('email_unique', True,
       "if True, check email addresses for uniqueness and don't accept duplicates."),

      ('homewiki', u'Self',
       "interwiki name of the wiki where the user home pages are located [Unicode] - useful if you have ''many'' users. You could even link to nonwiki \"user pages\" if the wiki username is in the target URL."),

      ('checkbox_fields',
       [
        ('mailto_author', lambda _: _('Publish my email (not my wiki homepage) in author info')),
        ('edit_on_doubleclick', lambda _: _('Open editor on double click')),
        ('show_comments', lambda _: _('Show comment sections')),
        ('disabled', lambda _: _('Disable this account forever')),
        # if an account is disabled, it may be used for looking up
        # id -> username for page info and recent changes, but it
        # is not usable for the user any more:
       ],
       "Describes user preferences, see HelpOnConfiguration/UserPreferences."),

      ('checkbox_defaults',
       {
        'mailto_author': False,
        'edit_on_doubleclick': True,
        'show_comments': False,
        'disabled': False,
       },
       "Defaults for user preferences, see HelpOnConfiguration/UserPreferences."),

      ('checkbox_disable', [],
       "Disable user preferences, see HelpOnConfiguration/UserPreferences."),

      ('checkbox_remove', [],
       "Remove user preferences, see HelpOnConfiguration/UserPreferences."),

      ('transient_fields',
       ['id', 'valid', 'may', 'auth_username', 'password', 'password2', 'auth_method', 'auth_attribs', ],
       "User object attributes that are not persisted to permanent storage (internal use)."),
    )),

    'mail': ('Mail settings',
        'These settings control outgoing and incoming email from and to the wiki.',
    (
      ('from', None, "Used as From: address for generated mail."),
      ('login', None, "'username userpass' for SMTP server authentication (None = don't use auth)."),
      ('smarthost', None, "Address of SMTP server to use for sending mail (None = don't use SMTP server)."),
      ('sendmail', None, "sendmail command to use for sending mail (None = don't use sendmail)"),
    )),
}

def _add_options_to_defconfig(opts, addgroup=True):
    for groupname in opts:
        group_short, group_doc, group_opts = opts[groupname]
        for name, default, doc in group_opts:
            if addgroup:
                name = groupname + '_' + name
            if isinstance(default, DefaultExpression):
                default = default.value
            setattr(DefaultConfig, name, default)

_add_options_to_defconfig(options)
_add_options_to_defconfig(options_no_group_name, False)

