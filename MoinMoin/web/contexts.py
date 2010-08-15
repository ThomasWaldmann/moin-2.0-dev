# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Context objects which are passed thru instead of the classic
               request objects. Currently contains legacy wrapper code for
               a single request object.

    @copyright: 2008-2008 MoinMoin:FlorianKrupicka
    @license: GNU GPL, see COPYING for details.
"""

import sys

from flask import flaskg

from werkzeug import create_environ

from MoinMoin import i18n, user, config, wikiutil
from MoinMoin.formatter import text_html
from MoinMoin.theme import load_theme_fallback
from MoinMoin.web.request import Request
from MoinMoin.web.utils import UniqueIDGenerator

from MoinMoin import log
logging = log.getLogger(__name__)

NoDefault = object()

class EnvironProxy(property):
    """ Proxy attribute lookups to keys in the environ. """
    def __init__(self, name, default=NoDefault):
        """
        An entry will be proxied to the supplied name in the .environ
        object of the property holder. A factory can be supplied, for
        values that need to be preinstantiated. If given as first
        parameter name is taken from the callable too.

        @param name: key (or factory for convenience)
        @param default: literal object or callable
        """
        if not isinstance(name, basestring):
            default = name
            name = default.__name__
        self.name = 'moin.' + name
        self.default = default
        property.__init__(self, self.get, self.set, self.delete)

    def get(self, obj):
        if self.name in obj.environ:
            res = obj.environ[self.name]
        else:
            factory = self.default
            if factory is NoDefault:
                raise AttributeError(self.name)
            elif hasattr(factory, '__call__'):
                res = obj.environ.setdefault(self.name, factory(obj))
            else:
                res = obj.environ.setdefault(self.name, factory)
        return res

    def set(self, obj, value):
        obj.environ[self.name] = value

    def delete(self, obj):
        del obj.environ[self.name]

    def __repr__(self):
        return "<%s for '%s'>" % (self.__class__.__name__,
                                  self.name)

class Context(object):
    """ Standard implementation for the context interface.

    This one wraps up a Moin-Request object and the associated
    environ and also keeps track of it's changes.
    """
    def __init__(self, request):
        assert isinstance(request, Request)

        self.request = request
        self.environ = environ = request.environ
        self.personalities = self.environ.setdefault(
            'context.personalities', []
        )
        self.personalities.append(self.__class__.__name__)

    def become(self, cls):
        """ Become another context, based on given class.

        @param cls: class to change to, must be a sister class
        @rtype: boolean
        @return: wether a class change took place
        """
        if self.__class__ is cls:
            return False
        else:
            self.personalities.append(cls)
            self.__class__ = cls
            return True

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.personalities)


class BaseContext(Context):
    """ Implements a basic context, that provides some common attributes.
    Most attributes are lazily initialized via descriptors. """

    action = EnvironProxy('do', lambda o: o.request.values.get('do', 'show'))
    user = EnvironProxy('user', lambda o: user.User(o, auth_method='request:invalid'))

    lang = EnvironProxy('lang')
    content_lang = EnvironProxy('content_lang', lambda o: o.cfg.language_default)
    current_lang = EnvironProxy('current_lang')

    html_formatter = EnvironProxy('html_formatter', lambda o: text_html.Formatter(o))
    formatter = EnvironProxy('formatter', lambda o: o.html_formatter)

    page = EnvironProxy('page', None) # TODO deprecated, get rid of this
    item_name = EnvironProxy('item_name', None) # TODO deprecated, get rid of this

    def getText(self):
        lang = self.lang
        def _(text, i18n=i18n, request=self, lang=lang, **kw):
            return i18n.getText(text, request, lang, **kw)
        return _

    getText = property(getText)
    _ = getText

    def rootpage(self):
        # DEPRECATED, use rootitem!
        from MoinMoin.Page import RootPage
        return RootPage(self)
    rootpage = EnvironProxy(rootpage)

    def rootitem(self):
        from MoinMoin.items import Item
        return Item(self, u'')
    rootitem = EnvironProxy(rootitem)

    def _theme(self):
        self.initTheme()
        return self.theme
    theme = EnvironProxy('theme', _theme)

    def initTheme(self):
        """ Set theme - forced theme, user theme or wiki default """
        if self.cfg.theme_force:
            theme_name = self.cfg.theme_default
        else:
            theme_name = self.user.theme_name
        load_theme_fallback(self, theme_name)


class HTTPContext(BaseContext):
    """ Context that holds attributes and methods for manipulation of
    incoming and outgoing HTTP data. """

    session = EnvironProxy('session')

    # proxy some descriptors of the underlying WSGI request, since
    # setting on those does not work over __(g|s)etattr__-proxies
    class _proxy(property):
        def __init__(self, name):
            self.name = name
            property.__init__(self, self.get, self.set, self.delete)
        def get(self, obj):
            return getattr(obj.request, self.name)
        def set(self, obj, value):
            setattr(obj.request, self.name, value)
        def delete(self, obj):
            delattr(obj.request, self.name)

    mimetype = _proxy('mimetype')
    content_type = _proxy('content_type')
    status = _proxy('status')
    status_code = _proxy('status_code')

    del _proxy

    # proxy further attribute lookups to the underlying request first
    def __getattr__(self, name):
        try:
            return getattr(self.request, name)
        except AttributeError, e:
            return super(HTTPContext, self).__getattribute__(name)

    # methods regarding manipulation of HTTP related data
    def read(self, n=None):
        """ Read n bytes (or everything) from input stream. """
        if n is None:
            return self.request.stream.read()
        else:
            return self.request.stream.read(n)

    # the output related methods
    def write(self, *data):
        """ Write to output stream. """
        self.request.out_stream.writelines(data)

    def getQualifiedURL(self, uri=''):
        """ Return an absolute URL starting with schema and host.

        Already qualified urls are returned unchanged.

        @param uri: server rooted uri e.g /scriptname/pagename.
                    It must start with a slash. Must be ascii and url encoded.
        """
        import urlparse
        scheme = urlparse.urlparse(uri)[0]
        if scheme:
            return uri

        host_url = self.request.host_url.rstrip('/')
        result = "%s%s" % (host_url, uri)

        # This might break qualified urls in redirects!
        # e.g. mapping 'http://netloc' -> '/'
        result = wikiutil.mapURL(self, result)
        return result

class AuxilaryMixin(object):
    """
    Mixin for diverse attributes and methods that aren't clearly assignable
    to a particular phase of the request.
    """
    # several attributes used by other code to hold state across calls
    _login_messages = EnvironProxy('_login_messages', lambda o: [])
    _login_multistage = EnvironProxy('_login_multistage', None)
    _login_multistage_name = EnvironProxy('_login_multistage_name', None)
    _setuid_real_user = EnvironProxy('_setuid_real_user', None)

    def uid_generator(self):
        pagename = None
        if hasattr(self, 'page') and hasattr(self.page, 'page_name'):
            pagename = self.page.page_name
        return UniqueIDGenerator(pagename=pagename)
    uid_generator = EnvironProxy(uid_generator)

    def dicts(self):
        """ Lazy initialize the dicts on the first access """
        dicts = self.cfg.dicts(self)
        return dicts
    dicts = EnvironProxy(dicts)

    def groups(self):
        """ Lazy initialize the groups on the first access """
        groups = self.cfg.groups(self)
        return groups
    groups = EnvironProxy(groups)

    def reset(self):
        self.current_lang = self.cfg.language_default
        if hasattr(self, 'uid_generator'):
            del self.uid_generator

class AllContext(HTTPContext, AuxilaryMixin):
    """ Catchall context to be able to quickly test old Moin code. """

class ScriptContext(AllContext):
    """ Context to act in scripting environments (e.g. former request_cli).

    For input, sys.stdin is used as 'wsgi.input', output is written directly
    to sys.stdout though.
    """
    def __init__(self, url=None, pagename=''):
        if url is None:
            url = 'http://localhost:0/' # just some somehow valid dummy URL
        environ = create_environ(base_url=url) # XXX is base_url correct? (was necessary for make underlay which is now gone)
        environ['HTTP_USER_AGENT'] = 'CLI/Script'
        environ['wsgi.input'] = sys.stdin
        request = Request(environ)
        super(ScriptContext, self).__init__(request)
        from MoinMoin import wsgiapp
        wsgiapp.init(self)

    def write(self, *data):
        for d in data:
            if isinstance(d, unicode):
                d = d.encode(config.charset)
            else:
                d = str(d)
            sys.stdout.write(d)
