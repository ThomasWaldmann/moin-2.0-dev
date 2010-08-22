# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Context objects which are passed thru instead of the classic
               request objects. Currently contains legacy wrapper code for
               a single request object.

    @copyright: 2008-2008 MoinMoin:FlorianKrupicka
    @license: GNU GPL, see COPYING for details.
"""

import sys

from werkzeug import create_environ

from flask import current_app as app

from MoinMoin.formatter import text_html
from MoinMoin.web.request import Request
from MoinMoin.web.utils import UniqueIDGenerator

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
        return "<%s for '%s'>" % (self.__class__.__name__, self.name)


class AllContext(object):
    def __init__(self, request):
        assert isinstance(request, Request)

        self.request = request
        self.environ = environ = request.environ
        self.personalities = self.environ.setdefault('context.personalities', [])
        self.personalities.append(self.__class__.__name__)

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.personalities)

    html_formatter = EnvironProxy('html_formatter', lambda o: text_html.Formatter(o))
    formatter = EnvironProxy('formatter', lambda o: o.html_formatter)

    def rootpage(self):
        # DEPRECATED, use rootitem!
        from MoinMoin.Page import RootPage
        return RootPage(self)
    rootpage = EnvironProxy(rootpage)

    def rootitem(self):
        from MoinMoin.items import Item
        return Item(self, u'')
    rootitem = EnvironProxy(rootitem)

    # proxy further attribute lookups to the underlying request first
    def __getattr__(self, name):
        try:
            return getattr(self.request, name)
        except AttributeError, e:
            return super(AllContext, self).__getattribute__(name)

    def uid_generator(self):
        pagename = None
        if hasattr(self, 'page') and hasattr(self.page, 'page_name'):
            pagename = self.page.page_name
        return UniqueIDGenerator(pagename=pagename)
    uid_generator = EnvironProxy(uid_generator)

    def reset(self):
        if hasattr(self, 'uid_generator'):
            del self.uid_generator


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
