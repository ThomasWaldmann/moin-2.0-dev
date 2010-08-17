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

try:
    from flask import Flask, request, url_for, render_template, flash
except ImportError:
    from MoinMoin import support
    dirname = os.path.dirname(support.__file__)
    dirname = os.path.abspath(dirname)
    if not dirname in sys.path:
        sys.path.insert(0, dirname)

    from flask import Flask, request, url_for, render_template, flash

# HACK: creating a custom alias for the single-letter "g"
# Note: this should be done with a *standard* longer name in flask and
#       documented as an official alternative to g, but Armin likes g and g only.
import flask
flask.flaskg = flaskg = flask.g
del flask

from werkzeug import ImmutableDict

class MoinFlask(Flask):
    # TODO: at all places where we insert html into output, use the Markup
    # class of flask/jinja so we can switch autoescape on in the end.
    jinja_options = ImmutableDict(
        autoescape=False,
    )

    secret_key = "thisisnotsecret"


app = MoinFlask('MoinMoin')

from werkzeug.routing import PathConverter
app.url_map.converters['itemname'] = PathConverter


import os, sys

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.util.clock import Clock
from MoinMoin.web.contexts import AllContext
from MoinMoin.web.request import Request
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


def init_unprotected_backends(context):
    """ initialize the backend

        This is separate from init because the conftest request setup needs to be
        able to create fresh data storage backends in between init and init_backend.
    """
    # A ns_mapping consists of several lines, where each line is made up like this:
    # mountpoint, unprotected backend, protection to apply as a dict
    # We don't consider the protection here. That is done in protect_backends.
    ns_mapping = app.cfg.namespace_mapping
    # Just initialize with unprotected backends.
    unprotected_mapping = [(ns, backend) for ns, backend, acls in ns_mapping]
    index_uri = app.cfg.router_index_uri
    context.unprotected_storage = router.RouterBackend(unprotected_mapping, index_uri=index_uri)

    # This makes the first request after server restart potentially much slower...
    import_export_xml(context)


def import_export_xml(context):
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
            backend = context.unprotected_storage
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
        backend = context.unprotected_storage
        serialize(backend, xmlfile)


def protect_backends(context):
    """
    This function is invoked after the user has been set up. setup_user needs access to
    storage and the ACL middleware needs access to the user's name. Hence we first
    init the unprotected backends so setup_user can access storage, and protect the
    backends after the user has been set up.
    """
    amw = acl.AclWrapperBackend
    ns_mapping = app.cfg.namespace_mapping
    # Protect each backend with the acls provided for it in the mapping at position 2
    protected_mapping = [(ns, amw(context, backend, **acls)) for ns, backend, acls in ns_mapping]
    index_uri = app.cfg.router_index_uri
    context.storage = router.RouterBackend(protected_mapping, index_uri=index_uri)


def setup_user(context, session):
    """ Try to retrieve a valid user object from the request, be it
    either through the session or through a login. """
    # first try setting up from session
    userobj = auth.setup_from_session(context, session)
    userobj, olduser = auth.setup_setuid(context, userobj)
    context._setuid_real_user = olduser

    # then handle login/logout forms
    form = context.request.values

    if 'login' in form:
        params = {
            'username': form.get('name'),
            'password': form.get('password'),
            'attended': True,
            'stage': form.get('stage')
        }
        userobj = auth.handle_login(context, userobj, **params)
    elif 'logout' in form:
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
            for l, w in context.request.accept_languages:
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


def setup_i18n_postauth(context):
    """ Determine language for the request after user-id is established. """
    lang = context.user.getLang()
    logging.debug("setup_i18n_postauth returns %r" % lang)
    return lang

@app.template_filter()
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


def setup_jinja_env(context):
    from MoinMoin.items import EDIT_LOG_USERID, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME
    app.jinja_env.filters['datetime_format'] = lambda tm, u = flaskg.user: u.getFormattedDateTime(tm)
    app.jinja_env.filters['date_format'] = lambda tm, u = flaskg.user: u.getFormattedDate(tm)
    app.jinja_env.filters['user_format'] = lambda rev, context = context: \
                                          user.get_printable_editor(context,
                                                                    rev.get(EDIT_LOG_USERID),
                                                                    rev.get(EDIT_LOG_ADDR),
                                                                    rev.get(EDIT_LOG_HOSTNAME))

    from MoinMoin.theme import load_theme_fallback
    theme_name = app.cfg.theme_default if app.cfg.theme_force else flaskg.user.theme_name
    flaskg.theme = load_theme_fallback(context, theme_name)

    app.jinja_env.globals.update({
                            'isinstance': isinstance,
                            'list': list,
                            'theme': flaskg.theme,
                            'user': flaskg.user,
                            'cfg': app.cfg,
                            '_': context.getText,
                            'flaskg': flaskg,
                            'item_name': 'handlers need to give it',
                            'translated_item_name': flaskg.theme.translated_item_name,
                            })


@app.before_request
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

    context = AllContext(Request(request.environ))

    context.lang = setup_i18n_preauth(context)

    context.session = app.cfg.session_service.get_session(context)

    init_unprotected_backends(context)
    flaskg.user = setup_user(context, context.session)

    context.lang = setup_i18n_postauth(context)

    def finish():
        pass

    context.finish = finish

    context.reset()

    protect_backends(context)

    setup_jinja_env(context)

    flaskg.context = context

    flaskg.clock.stop('init')
    # if return value is not None, it is the final response


@app.after_request
def after(response):
    context = flaskg.context
    app.cfg.session_service.finalize(context, context.session)
    context.finish()
    return response


from MoinMoin.apps.frontend import frontend
app.register_module(frontend)

from MoinMoin.apps.admin import admin
app.register_module(admin, url_prefix='/+admin')

from MoinMoin.apps.feed import feed
app.register_module(feed, url_prefix='/+feed')

from MoinMoin.apps.misc import misc
app.register_module(misc, url_prefix='/+misc')

