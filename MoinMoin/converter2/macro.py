# -*- coding: iso-8859-1 -*-
"""
MoinMoin - Macro handling

Expands all macro elements in a internal Moin document.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin import macro, Page, wikiutil
from MoinMoin.util import uri
from MoinMoin.util.tree import html, moin_page

class _PseudoParser(object):
    def __init__(self, request):
        self.request = request
        self.form = request.form

class _PseudoRequest(object):
    def __init__(self, request, name):
        self.__request, self.__name = request, name
        self.__written = False

    def __getattr__(self, name):
        return getattr(self.__request, name)

    def write(self, *text):
        text = ''.join((i.encode('ascii', 'replace') for i in text))
        if text:
            text.replace('\n', ' ')
            if len(text) > 100:
                text = text[:100] + '...'
            from warnings import warn
            message = 'Macro ' + self.__name + ' used request.write: ' + text
            warn(message, DeprecationWarning, stacklevel=2)
            self.__written = True

    @property
    def written(self):
        return self.__written

class Converter(object):
    @classmethod
    def _factory(cls, request, input, output):
        if input == 'application/x-moin-document' and \
                output == 'application/x-moin-document;macros=expandall':
            return cls

    def handle_macro(self, elem, page_name):
        name = elem.get(moin_page.macro_name)
        args = elem.get(moin_page.macro_args)
        context = elem.get(moin_page.macro_context)
        alt = elem.get(moin_page.alt, None)

        elem_body = moin_page.macro_body()

        if not self._handle_macro_new(elem_body, page_name, name, args, context, alt):
            self._handle_macro_old(elem_body, page_name, name, args, context, alt)

        elem.append(elem_body)

    def _error(self, message, context, alt):
        if alt:
            attrib = {html.class_: 'error', moin_page.title: message}
            children = alt
        else:
            attrib = {}
            children = message

        elem = moin_page.strong(attrib=attrib, children=[children])

        if context == 'block':
            return moin_page.p(children=[elem])
        return elem

    def _handle_macro_new(self, elem_body, page_name, name, args, context, alt):
        try:
            cls = wikiutil.importPlugin(self.request.cfg, 'macro2', name, function='Macro')
        except wikiutil.PluginMissingError:
            return False

        macro = cls(self.request, page_name, alt, context, args)
        ret = macro()

        elem_body.append(ret)

        return True

    def _handle_macro_old(self, elem_body, page_name, name, args, context, alt):
        Formatter = wikiutil.searchAndImportPlugin(self.request.cfg, "formatter", 'compatibility')

        request = _PseudoRequest(self.request, name)
        page = Page.Page(request, page_name)
        request.formatter = formatter = Formatter(request, page)

        m = macro.Macro(_PseudoParser(request))

        try:
            ret = m.execute(name, args or None)
        except ImportError, err:
            message = unicode(err)
            if not name in message:
                raise
            elem_body.append(self._error(message, context, alt))
            return
        except AssertionError, e:
            from warnings import warn
            message = 'Macro ' + name + ' get an assertion in the compatibility formatter'
            if e.args:
                message += ': ' + e.args[0]
            warn(message, DeprecationWarning)
            ret = True
        except NotImplementedError, e:
            # Force usage of fallback on not implemented methods
            from warnings import warn
            message = 'Macro ' + name + ' calls methods in the compatibility formatter which are not implemented'
            if e.args:
                message += ': ' + e.args[0]
            warn(message, DeprecationWarning)
            ret = True

        if request.written:
            message = 'Macro ' + name + ' used request.write'
            elem_body.append(self._error(message, context, alt))
            return

        if ret:
            # Fallback to HTML formatter
            HtmlFormatter = wikiutil.searchAndImportPlugin(self.request.cfg, "formatter", 'text/html')
            request.formatter = m.formatter = HtmlFormatter(request)
            m.formatter.setPage(page)

            ret = m.execute(name, args or None)

            # Pipe the result through the HTML parser
            formatter = Formatter(request, page)
            formatter.rawHTML(ret)

        elem_body.extend(formatter.root[:])

    def recurse(self, elem, page_name):
        new_page_href = elem.get(moin_page.page_href)
        if new_page_href:
            # TODO: unicode URI
            u = uri.Uri(new_page_href)
            if u.authority == '' and u.path.startswith('/'):
                page_name = u.path[1:].decode('utf-8')

        if elem.tag == moin_page.macro:
            yield elem, page_name

        for child in elem:
            if isinstance(child, ET.Node):
                for i in self.recurse(child, page_name):
                    yield i

    def __init__(self, request):
        self.request = request

    def __call__(self, tree):
        for elem, page_name in self.recurse(tree, None):
            self.handle_macro(elem, page_name)

        return tree

from _registry import default_registry
default_registry.register(Converter._factory)
