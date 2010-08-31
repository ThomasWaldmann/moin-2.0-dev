# -*- coding: ascii -*-
"""
MoinMoin - a wiki engine in Python.

This creates the WSGI application (using Flask) as "app".

@copyright: 2000-2006 by Juergen Hermann <jh@web.de>,
            2002-2010 MoinMoin:ThomasWaldmann,
            2008 MoinMoin:FlorianKrupicka,
            2010 MoinMoin:DiogenesAugusto
@license: GNU GPL, see COPYING for details.
"""
import os
import sys

# XXX temporary sys.path hack for convenience:
support_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'support'))
if support_dir not in sys.path:
    sys.path.insert(0, support_dir)

# monkey patching needs to be done after sys.path setup
from MoinMoin.util import monkeypatch

from flask import Flask, request, url_for, render_template, flash, session, flaskg
from flask import current_app as app

from werkzeug import ImmutableDict

class MoinFlask(Flask):
    # TODO: at all places where we insert html into output, use the Markup
    # class of flask/jinja so we can switch autoescape on in the end.
    jinja_options = ImmutableDict(
        autoescape=False,
    )


from MoinMoin import log
logging = log.getLogger(__name__)

# FIXME dummy i18n for now XXX
_ = lambda x: x
N_ = lambda s, p, n: s if n == 1 else p

def create_app(flask_config_file=None, flask_config_dict=None,
               moin_config_class=None, warn_default=True, **kwargs
              ):
    """
    Factory for moin wsgi apps

    @param flask_config_file: a flask config file name (may have a MOINCFG class),
                              if not given, a config pointed to by MOINCFG env var
                              will be loaded (if possible).
    @param flask_config_dict: a dict used to update flask config (applied after
                              flask_config_file was loaded [if given])
    @param moin_config_class: if you give this, it'll be instantiated as app.cfg,
                              otherwise it'll use MOINCFG from flask config. If that
                              also is not there, it'll use the DefaultConfig built
                              into MoinMoin.
    @oaram warn_default: emit a warning if moin falls back to its builtin default
                         config (maybe user forgot to specify MOINCFG?)
    @param **kwargs: if you give additional key/values here, they'll get patched
                     into the moin configuration class (before it instance is created)
    """
    app = MoinFlask('MoinMoin')
    if flask_config_file:
        app.config.from_pyfile(flask_config_file)
    else:
        app.config.from_envvar('MOINCFG', silent=True)
    if flask_config_dict:
        app.config.update(flask_config_dict)
    Config = moin_config_class
    if not Config:
        Config = app.config.get('MOINCFG')
    if not Config:
        if warn_default:
            logging.warning("using builtin default configuration")
        from MoinMoin.config.default import DefaultConfig as Config
    for key, value in kwargs.iteritems():
        setattr(Config, key, value)
    app.cfg = Config()
    # register converters
    from werkzeug.routing import PathConverter
    app.url_map.converters['itemname'] = PathConverter
    # register modules
    from MoinMoin.apps.frontend import frontend
    app.register_module(frontend)
    from MoinMoin.apps.admin import admin
    app.register_module(admin, url_prefix='/+admin')
    from MoinMoin.apps.feed import feed
    app.register_module(feed, url_prefix='/+feed')
    from MoinMoin.apps.misc import misc
    app.register_module(misc, url_prefix='/+misc')
    # register filters
    app.jinja_env.filters['shorten_item_name'] = shorten_item_name
    # register before/after request functions
    app.before_request(before)
    app.after_request(after)
    # init storage
    app.unprotected_storage = init_unprotected_backends(app)
    import_export_xml(app)
    app.storage = init_protected_backends(app)
    return app


from MoinMoin.util.clock import Clock
from MoinMoin.util.uidgen import UniqueIDGenerator
from MoinMoin.storage.error import StorageError
from MoinMoin.storage.serialization import serialize, unserialize
from MoinMoin.storage.backends import router, acl, memory
from MoinMoin import auth, config, i18n, user


def set_umask(new_mask=0777^config.umask):
    """ Set the OS umask value (and ignore potential failures on OSes where
        this is not supported).
        Default: the bitwise inverted value of config.umask
    """
    try:
        old_mask = os.umask(new_mask)
    except:
        # maybe we are on win32?
        pass


def init_unprotected_backends(app):
    """ initialize the backend

        This is separate from init because the conftest request setup needs to be
        able to create fresh data storage backends in between init and init_backend.
    """
    # A ns_mapping consists of several lines, where each line is made up like this:
    # mountpoint, unprotected backend, protection to apply as a dict
    # We don't consider the protection here. That is done in init_protected_backends.
    ns_mapping = app.cfg.namespace_mapping
    # Just initialize with unprotected backends.
    unprotected_mapping = [(ns, backend) for ns, backend, acls in ns_mapping]
    index_uri = app.cfg.router_index_uri
    unprotected_storage = router.RouterBackend(unprotected_mapping, index_uri=index_uri)
    return unprotected_storage


def import_export_xml(app):
    # If the content was already pumped into the backend, we don't want
    # to do that again. (Works only until the server is restarted.)
    xmlfile = app.cfg.load_xml
    if xmlfile:
        app.cfg.load_xml = None
        tmp_backend = router.RouterBackend([('/', memory.MemoryBackend())],
                                           index_uri='sqlite://')
        unserialize(tmp_backend, xmlfile)
        # TODO optimize this, maybe unserialize could count items it processed
        item_count = 0
        for item in tmp_backend.iteritems():
            item_count += 1
        logging.debug("loaded xml into tmp_backend: %s, %d items" % (xmlfile, item_count))
        try:
            # In case the server was restarted we cannot know whether
            # the xml data already exists in the target backend.
            # Hence we check the existence of the items before we unserialize
            # them to the backend.
            backend = app.unprotected_storage
            for item in tmp_backend.iteritems():
                item = backend.get_item(item.name)
        except StorageError:
            # if there is some exception, we assume that backend needs to be filled
            # we need to use it as unserialization target so that update mode of
            # unserialization creates the correct item revisions
            logging.debug("unserialize xml file %s into %r" % (xmlfile, backend))
            unserialize(backend, xmlfile)
    else:
        item_count = 0

    # XXX wrong place / name - this is a generic preload functionality, not just for tests
    # To make some tests happy
    app.cfg.test_num_pages = item_count

    xmlfile = app.cfg.save_xml
    if xmlfile:
        app.cfg.save_xml = None
        backend = app.unprotected_storage
        serialize(backend, xmlfile)


def init_protected_backends(app):
    """
    This function is invoked after the user has been set up. setup_user needs access to
    storage and the ACL middleware needs access to the user's name. Hence we first
    init the unprotected backends so setup_user can access storage, and protect the
    backends after the user has been set up.
    """
    amw = acl.AclWrapperBackend
    ns_mapping = app.cfg.namespace_mapping
    # Protect each backend with the acls provided for it in the mapping at position 2
    protected_mapping = [(ns, amw(app.cfg, backend, **acls)) for ns, backend, acls in ns_mapping]
    index_uri = app.cfg.router_index_uri
    storage = router.RouterBackend(protected_mapping, index_uri=index_uri)
    return storage


def setup_user(context):
    """ Try to retrieve a valid user object from the request, be it
    either through the session or through a login. """
    # init some stuff for auth processing:
    flaskg._login_multistage = None
    flaskg._login_multistage_name = None
    flaskg._login_messages = []

    # first try setting up from session
    userobj = auth.setup_from_session(context)

    # then handle login/logout forms
    form = request.values

    if 'login_submit' in form:
        # this is a real form, submitted by POST
        params = {
            'username': form.get('login_username'),
            'password': form.get('login_password'),
            'attended': True,
            'stage': form.get('stage')
        }
        userobj = auth.handle_login(context, userobj, **params)
    elif 'logout_submit' in form:
        # currently just a GET link
        userobj = auth.handle_logout(context, userobj)
    else:
        userobj = auth.handle_request(context, userobj)

    # if we still have no user obj, create a dummy:
    if not userobj:
        userobj = user.User(context, auth_method='invalid')

    return userobj


def setup_i18n_preauth(context):
    """ Determine language for the request in absence of any user info. """
    if i18n.languages is None:
        i18n.i18n_init(context)

    lang = None
    if i18n.languages:
        cfg = app.cfg
        if not cfg.language_ignore_browser:
            for l, w in request.accept_languages:
                logging.debug("client accepts language %r, weight %r" % (l, w))
                if l in i18n.languages:
                    logging.debug("moin supports language %r" % l)
                    lang = l
                    break
            else:
                logging.debug("moin does not support any language client accepts")
        if not lang:
            if cfg.language_default in i18n.languages:
                lang = cfg.language_default
                logging.debug("fall back to cfg.language_default (%r)" % lang)
    if not lang:
        lang = 'en'
        logging.debug("emergency fallback to 'en'")
    logging.debug("setup_i18n_preauth returns %r" % lang)
    return lang


def setup_i18n_postauth():
    """ Determine language for the request after user-id is established. """
    lang = flaskg.user.getLang()
    logging.debug("setup_i18n_postauth returns %r" % lang)
    return lang

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


def get_editor_info(request, rev, external=False):
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
        u = user.User(request, userid)
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


def setup_jinja_env(context):
    app.jinja_env.filters['datetime_format'] = lambda tm, u = flaskg.user: u.getFormattedDateTime(tm)
    app.jinja_env.filters['date_format'] = lambda tm, u = flaskg.user: u.getFormattedDate(tm)

    from MoinMoin.theme import ThemeSupport
    theme_name = app.cfg.theme_default if app.cfg.theme_force else flaskg.user.theme_name
    flaskg.theme = ThemeSupport(theme_name)

    app.jinja_env.globals.update({
                            'isinstance': isinstance,
                            'list': list,
                            'theme': flaskg.theme,
                            'user': flaskg.user,
                            'cfg': app.cfg,
                            '_': _,
                            'flaskg': flaskg,
                            'item_name': 'handlers need to give it',
                            'translated_item_name': flaskg.theme.translated_item_name,
                            'get_editor_info': lambda rev, request=context: get_editor_info(request, rev),
                            })


def before():
    """
    Wraps an incoming WSGI request in a Context object and initializes
    several important attributes.
    """
    flaskg.clock = Clock()
    flaskg.clock.start('total')
    flaskg.clock.start('init')

    set_umask() # do it once per request because maybe some server
                # software sets own umask

    context = request # werkzeug contextlocal request object

    lang = setup_i18n_preauth(context)

    flaskg.unprotected_storage = app.unprotected_storage
    flaskg.user = setup_user(context)

    flaskg.dicts = app.cfg.dicts(context)
    flaskg.groups = app.cfg.groups(context)

    flaskg.content_lang = app.cfg.language_default
    flaskg.current_lang = app.cfg.language_default

    lang = setup_i18n_postauth()

    def uid_generator():
        return UniqueIDGenerator()
    flaskg.uid_generator = uid_generator

    flaskg.storage = app.storage

    setup_jinja_env(context)

    flaskg.context = context

    flaskg.clock.stop('init')
    # if return value is not None, it is the final response


def after(response):
    return response

