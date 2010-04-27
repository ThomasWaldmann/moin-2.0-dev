# -*- coding: iso-8859-1 -*-
"""
MoinMoin - Macro handling

Expands all macro elements in a internal Moin document.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

from emeraldtree import ElementTree as ET
import logging
logger = logging.getLogger(__name__)

from MoinMoin import macro, Page, wikiutil
from MoinMoin.converter2._args import Arguments
from MoinMoin.util import iri
from MoinMoin.util.mime import type_moin_document
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
    def _factory(cls, _request, input, output, macros=None, **kw):
        if (type_moin_document.issupertype(input) and
                type_moin_document.issupertype(output) and
                macros == 'expandall'):
            return cls

    def handle_macro(self, elem, page):
        type = elem.get(moin_page.content_type)
        alt = elem.get(moin_page.alt)

        # TODO
        if not type or not type.startswith('x-moin/macro;name='):
            return
        name = type[18:]

        context_block = elem.tag == moin_page.part

        args_tree = None
        for item in elem:
            if item.tag.uri == moin_page.namespace:
                if item.tag.name in ('body', 'inline-body'):
                    return
                if item.tag.name == 'arguments':
                    args_tree = item

        args = None
        if args_tree:
            args = Arguments()
            for arg in args_tree:
                key = arg.get(moin_page.name)
                value = arg[0]
                if key:
                    args.keyword[key] = value
                else:
                    args.positional.append(value)

        elem_body = context_block and moin_page.body() or moin_page.inline_body()
        elem_error = moin_page.error()

        if not self._handle_macro_new(elem_body, elem_error, page, name, args, context_block, alt):
            self._handle_macro_old(elem_body, elem_error, page, name, args, context_block, alt)

        if len(elem_body):
            elem.append(elem_body)
        if len(elem_error):
            elem.append(elem_error)

    def _handle_macro_new(self, elem_body, elem_error, page, name, args, context_block, alt):
        try:
            cls = wikiutil.importPlugin(self.request.cfg, 'macro2', name, function='Macro')
        except wikiutil.PluginMissingError:
            return False

        try:
            macro = cls(self.request)
            ret = macro((), args, page, alt, context_block)

            elem_body.append(ret)
        except Exception, e:
            # we do not want that a faulty macro aborts rendering of the page
            # and makes the wiki UI unusable (by emitting a Server Error),
            # thus, in case of exceptions, we just log the problem and return
            # some standard text.
            logger.exception("Macro %s raised an exception:" % name)
            _ = self.request.getText
            elem_error.append(_('<<%(macro_name)s: execution failed [%(error_msg)s] (see also the log)>>') % {
                    'macro_name': name,
                    'error_msg': unicode(e),
                })

        return True

    def _handle_macro_old(self, elem_body, elem_error, page, name, args, context, alt):
        Formatter = wikiutil.searchAndImportPlugin(self.request.cfg, "formatter", 'compatibility')

        request = _PseudoRequest(self.request, name)
        page = Page.Page(request, unicode(page.path)[1:])
        request.formatter = formatter = Formatter(request, page)

        m = macro.Macro(_PseudoParser(request))

        try:
            ret = m.execute(name, args or None)
        except ImportError, err:
            message = unicode(err)
            if not name in message:
                raise
            elem_error.append(message)
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
        except Exception, e:
            # we do not want that a faulty macro aborts rendering of the page
            # and makes the wiki UI unusable (by emitting a Server Error),
            # thus, in case of exceptions, we just log the problem and return
            # some standard text.
            logger.exception("Macro %s raised an exception:" % name)
            _ = self.request.getText
            elem_error.append(_('<<%(macro_name)s: execution failed [%(error_msg)s] (see also the log)>>') % {
                    'macro_name': name,
                    'error_msg': unicode(e),
                })
            return

        if request.written:
            message = 'Macro ' + name + ' used request.write'
            elem_error.append(message)
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

    def recurse(self, elem, page):
        new_page_href = elem.get(moin_page.page_href)
        if new_page_href:
            page = iri.Iri(new_page_href)

        if elem.tag in (moin_page.part, moin_page.inline_part):
            yield elem, page

        for child in elem:
            if isinstance(child, ET.Node):
                for i in self.recurse(child, page):
                    yield i

    def __init__(self, request):
        self.request = request

    def __call__(self, tree):
        for elem, page in self.recurse(tree, None):
            self.handle_macro(elem, page)

        return tree

from . import default_registry
default_registry.register(Converter._factory)

