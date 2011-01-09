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

from flask import Flask, request, url_for, flash, session, flaskg
from flask import current_app as app
from flaskext.babel import Babel
from flaskext.babel import gettext as _
from flaskext.babel import lazy_gettext as N_
from flaskext.cache import Cache
from flaskext.themes import setup_themes

from werkzeug import ImmutableDict

from jinja2 import ChoiceLoader, FileSystemLoader

class MoinFlask(Flask):
    # TODO: at all places where we insert html into output, use the Markup
    # class of flask/jinja so we can switch autoescape on in the end.
    select_jinja_autoescape = False


from MoinMoin import log
logging = log.getLogger(__name__)

if sys.hexversion < 0x2060000:
    logging.warning("MoinMoin requires Python 2.6 or greater.")

from MoinMoin.themes import setup_jinja_env, themed_error

def create_app(config=None):
    """simple wrapper around create_app_ext() for flask-script"""
    return create_app_ext(flask_config_file=config)


def create_app_ext(flask_config_file=None, flask_config_dict=None,
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
    if Config.secrets is None:
        # reuse the secret configured for flask (which is required for sessions)
        Config.secrets = app.config.get('SECRET_KEY')
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
    # register before/after request functions
    app.before_request(before)
    app.after_request(after)
    cache = Cache()
    cache.init_app(app)
    app.cache = cache
    # init storage
    app.unprotected_storage, app.storage = init_backends(app)
    app.unprotected_storage.index_rebuild() # XXX run this from a script
    import_export_xml(app)
    babel = Babel(app)
    babel.localeselector(get_locale)
    babel.timezoneselector(get_timezone)
    # configure templates
    setup_themes(app)
    if app.cfg.template_dirs:
        app.jinja_env.loader = ChoiceLoader([
            FileSystemLoader(app.cfg.template_dirs),
            app.jinja_env.loader,
        ])
    app.error_handlers[403] = themed_error
    return app


def get_locale():
    locale = None
    # this might be called at a time when flaskg.user is not setup yet:
    u = getattr(flaskg, 'user', None)
    if u and u.locale is not None:
        # locale is given in user profile, use it
        locale = u.locale
    else:
        # try to guess the language from the user accept
        # header the browser transmits. The best match wins.
        supported_languages = ['de', 'fr', 'en'] # XXX
        locale = request.accept_languages.best_match(supported_languages)
    if not locale:
        locale = app.cfg.locale_default
    return locale


def get_timezone():
    # this might be called at a time when flaskg.user is not setup yet:
    u = getattr(flaskg, 'user', None)
    if u and u.timezone is not None:
        return u.timezone


from MoinMoin.util.clock import Clock
from MoinMoin.storage.error import StorageError
from MoinMoin.storage.serialization import serialize, unserialize
from MoinMoin.storage.backends import router, acl, memory
from MoinMoin import auth, config, user


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


def init_backends(app):
    """ initialize the backend """
    # A ns_mapping consists of several lines, where each line is made up like this:
    # mountpoint, unprotected backend, protection to apply as a dict
    ns_mapping = app.cfg.namespace_mapping
    index_uri = app.cfg.router_index_uri
    # Just initialize with unprotected backends.
    unprotected_mapping = [(ns, backend) for ns, backend, acls in ns_mapping]
    unprotected_storage = router.RouterBackend(unprotected_mapping, index_uri=index_uri)
    # Protect each backend with the acls provided for it in the mapping at position 2
    amw = acl.AclWrapperBackend
    protected_mapping = [(ns, amw(app.cfg, backend, **acls)) for ns, backend, acls in ns_mapping]
    storage = router.RouterBackend(protected_mapping, index_uri=index_uri)
    return unprotected_storage, storage


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


def setup_user():
    """ Try to retrieve a valid user object from the request, be it
    either through the session or through a login. """
    # init some stuff for auth processing:
    flaskg._login_multistage = None
    flaskg._login_multistage_name = None
    flaskg._login_messages = []

    # first try setting up from session
    userobj = auth.setup_from_session()

    # then handle login/logout forms
    form = request.values.to_dict()
    if 'login_submit' in form:
        # this is a real form, submitted by POST
        userobj = auth.handle_login(userobj, **form)
    elif 'logout_submit' in form:
        # currently just a GET link
        userobj = auth.handle_logout(userobj)
    else:
        userobj = auth.handle_request(userobj)

    # if we still have no user obj, create a dummy:
    if not userobj:
        userobj = user.User(auth_method='invalid')
    # if we have a valid user we store it in the session
    if userobj.valid:
        session['user.id'] = userobj.id
        session['user.auth_method'] = userobj.auth_method
        session['user.auth_attribs'] = userobj.auth_attribs
    return userobj


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

    flaskg.unprotected_storage = app.unprotected_storage
    flaskg.user = setup_user()

    flaskg.dicts = app.cfg.dicts()
    flaskg.groups = app.cfg.groups()

    flaskg.content_lang = app.cfg.language_default
    flaskg.current_lang = app.cfg.language_default

    flaskg.storage = app.storage

    setup_jinja_env()

    flaskg.clock.stop('init')
    # if return value is not None, it is the final response


def after(response):
    flaskg.clock.stop('total')
    del flaskg.clock
    return response

