# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - WSGI application

    @copyright: 2003-2008 MoinMoin:ThomasWaldmann,
                2008-2008 MoinMoin:FlorianKrupicka
    @license: GNU GPL, see COPYING for details.
"""
import threading

from MoinMoin.web.contexts import AllContext, Context, XMLRPCContext
from MoinMoin.web.exceptions import HTTPException, Forbidden
from MoinMoin.web.request import Request, MoinMoinFinish, HeaderSet
from MoinMoin.web.utils import check_forbidden, check_surge_protect, fatal_response, \
    redirect_last_visited
from MoinMoin.storage.error import AccessDeniedError, StorageError
from MoinMoin.storage.serialization import unserialize
from MoinMoin.storage.backends import router, acl, memory, clone
from MoinMoin.Page import Page
from MoinMoin import auth, i18n, user, wikiutil, xmlrpc, error

from MoinMoin import log
logging = log.getLogger(__name__)

def init(request):
    """
    Wraps an incoming WSGI request in a Context object and initializes
    several important attributes.
    """
    if isinstance(request, Context):
        context, request = request, request.request
    else:
        context = AllContext(request)
    context.clock.start('total')
    context.clock.start('init')

    context.lang = setup_i18n_preauth(context)

    context.session = context.cfg.session_service.get_session(context)

    init_unprotected_backends(context)
    context.user = setup_user(context, context.session)

    context.lang = setup_i18n_postauth(context)

    def finish():
        pass

    context.finish = finish

    context.reset()

    context.clock.stop('init')
    return context


def init_unprotected_backends(context):
    """ initialize the backend

        This is separate from init because the conftest request setup needs to be
        able to create fresh data storage backends in between init and init_backend.
    """
    # TODO: Find a better term than 'line'
    # A mapping consists of several lines, where each line is made up like this:
    # mountpoint, unprotected backend, protection to apply
    mapping = context.cfg.namespace_mapping
    # Just initialize with unprotected backends.
    mapping = [(line[0], line[1]) for line in mapping]
    context.unprotected_storage = router.RouterBackend(mapping)

    # Preload xml in a seperate thread since this may be a very long-running operation
    threading.Thread(target=preload_xml, args=(context,)).start()


def preload_xml(context):
    # This makes the first request after server restart potentially slower.
    xmlfile = context.cfg.preloaded_xml
    if xmlfile:
        context.cfg.preloaded_xml = None
        try:
            backend = context.unprotected_storage
            tmp_backend = memory.MemoryBackend()
            unserialize(tmp_backend, xmlfile)
            for item in tmp_backend.iteritems():
                item = backend.get_item(item.name)
        except StorageError:
            # if there is some exception, we assume that backend needs to be filled
            clone(tmp_backend, backend)


def protect_backends(context):
    amw = acl.AclWrapperBackend
    mapping = context.cfg.namespace_mapping
    # Protect each backend with the acls provided for it in the mapping
    mapping = [(line[0], amw(context, line[1], **line[2])) for line in mapping]
    context.storage = router.RouterBackend(mapping)


def run(context):
    """ Run a context trough the application. """
    context.clock.start('run')
    request = context.request

    # preliminary access checks (forbidden, bots, surge protection)
    try:
        try:
            check_forbidden(context)
            check_surge_protect(context)

            action_name = context.action

            # handle XMLRPC calls
            if action_name == 'xmlrpc':
                response = xmlrpc.xmlrpc(XMLRPCContext(request))
            elif action_name == 'xmlrpc2':
                response = xmlrpc.xmlrpc2(XMLRPCContext(request))
            else:
                response = dispatch(request, context, action_name)
            context.cfg.session_service.finalize(context, context.session)
            return response
        except MoinMoinFinish:
            return request
        except AccessDeniedError, ade:
            forbidden = Forbidden()
            forbidden.description = ade.message
            return forbidden
    finally:
        context.finish()
        context.clock.stop('run')

def remove_prefix(path, prefix=None):
    """ Remove an url prefix from the path info and return shortened path. """
    # we can have all action URLs like this: /action/ActionName/PageName?action=ActionName&...
    # this is just for robots.txt being able to forbid them for crawlers
    if prefix is not None:
        prefix = '/%s/' % prefix # e.g. '/action/'
        if path.startswith(prefix):
            # remove prefix and action name
            path = path[len(prefix):]
            action, path = (path.split('/', 1) + ['', ''])[:2]
            path = '/' + path
    return path

def dispatch(request, context, action_name='show'):
    cfg = context.cfg

    # The last component in path_info is the page name, if any
    path = remove_prefix(request.path, cfg.url_prefix_action)

    if path.startswith('/'):
        pagename = wikiutil.normalize_pagename(path, cfg)
    else:
        pagename = None

    # need to inform caches that content changes based on:
    # * cookie (even if we aren't sending one now)
    # * User-Agent (because a bot might be denied and get no content)
    # * Accept-Language (except if moin is told to ignore browser language)
    hs = HeaderSet(('Cookie', 'User-Agent'))
    if not cfg.language_ignore_browser:
        hs.add('Accept-Language')
    request.headers.add('Vary', str(hs))

    # Handle request. We have these options:
    # 1. jump to page where user left off
    if not pagename and context.user.remember_last_visit and action_name == 'show':
        response = redirect_last_visited(context)
    # 2. handle action
    else:
        response = handle_action(context, pagename, action_name)
    if isinstance(response, Context):
        response = response.request
    return response

def handle_action(context, pagename, action_name='show'):
    """ Actual dispatcher function for non-XMLRPC actions.

    Also sets up the Page object for this request, normalizes and
    redirects to canonical pagenames and checks for non-allowed
    actions.
    """
    _ = context.getText
    cfg = context.cfg

    # pagename could be empty after normalization e.g. '///' -> ''
    # Use localized FrontPage if pagename is empty
    if not pagename:
        context.page = wikiutil.getFrontPage(context)
    else:
        context.page = Page(context, pagename)
        if '_' in pagename and not context.page.exists():
            pagename = pagename.replace('_', ' ')
            page = Page(context, pagename)
            if page.exists():
                url = page.url(context)
                return context.http_redirect(url)

    try:
        from MoinMoin import action
        handler = action.getHandler(cfg, action_name)
    except ValueError, err:
        msg = str(err) # XXX i18n problems!
        context.theme.add_msg(msg, "error")
        # use a handler that should work ever:
        handler = action.getHandler(cfg, 'show')

    handler(context.page.page_name, context)

    return context

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
            'openid_identifier': form.get('openid_identifier'),
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

    cfg = context.cfg
    lang = None
    if i18n.languages and not cfg.language_ignore_browser:
        for l in context.request.accept_languages:
            if l in i18n.languages:
                lang = l
                break
    if lang is None and cfg.language_default in i18n.languages:
        lang = cfg.language_default
    else:
        lang = 'en'
    return lang

def setup_i18n_postauth(context):
    """ Determine language for the request after user-id is established. """
    user = context.user
    if user and user.valid and user.language:
        return user.language
    else:
        return context.lang

class Application(object):
    def __init__(self, app_config=None):

        class AppRequest(Request):
            given_config = app_config

        self.Request = AppRequest

    def __call__(self, environ, start_response):
        try:
            request = self.Request(environ)
            context = init(request)
            protect_backends(context)
            response = run(context)
            context.clock.stop('total')
        except HTTPException, e:
            response = e
        except error.ConfigurationError, e:
            # this is stuff the user should see on the web interface:
            response = fatal_response(e)
        except Exception, e:
            # have exceptions logged within the moin logging framework:
            logging.exception("An exception has occurred.")
            # re-raise exception, so e.g. the debugger middleware gets it
            raise

        return response(environ, start_response)

#XXX: default application using the default config from disk
application = Application()
