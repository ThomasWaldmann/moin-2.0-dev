# -*- coding: iso-8859-1 -*-
"""
MoinMoin - Macro handling

Expands all macro elements in a internal Moin document.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET
import htmlentitydefs
from HTMLParser import HTMLParser as _HTMLParserBase

from MoinMoin import macro, Page, wikiutil
from MoinMoin.util import namespaces

class _PseudoParser(object):
    def __init__(self, request):
        self.request = request
        self.form = request.form

class Converter(object):
    tag_alt = ET.QName('alt', namespaces.moin_page)
    tag_macro = ET.QName('macro', namespaces.moin_page)
    tag_macro_args = ET.QName('macro-args', namespaces.moin_page)
    tag_macro_body = ET.QName('macro-body', namespaces.moin_page)
    tag_macro_name = ET.QName('macro-name', namespaces.moin_page)
    tag_macro_type = ET.QName('macro-type', namespaces.moin_page)
    tag_page_href = ET.QName('page-href', namespaces.moin_page)

    @classmethod
    def _factory(cls, input, output):
        if input == 'application/x-moin-document' and \
                output == 'application/x-moin-document;macros=expandall':
            return cls()

    def handle_macro(self, elem, page_href):
        name = elem.get(self.tag_macro_name)
        args = elem.get(self.tag_macro_args)
        context = elem.get(self.tag_macro_type)
        alt = elem.get(self.tag_alt, None)

        elem_body = ET.Element(self.tag_macro_body)

        if not self._handle_macro_new(elem_body, page_href, name, args, context, alt):
            self._handle_macro_old(elem_body, page_href, name, args, alt)

        elem.append(elem_body)

    def _handle_macro_new(self, elem_body, page_href, name, args, context, alt):
        page_name = page_href[8:]

        try:
            cls = wikiutil.importPlugin(self.request.cfg, 'macro2', name, function='Macro')
        except wikiutil.PluginMissingError:
            return False

        macro = cls(self.request, page_name, alt, context, args)
        ret = macro()

        elem_body.append(ret)

        return True

    def _handle_macro_old(self, elem_body, page_href, name, args, alt):
        m = macro.Macro(_PseudoParser(self.request))

        formatter = wikiutil.searchAndImportPlugin(self.request.cfg, "formatter", 'compatibility')
        page = Page.Page(self.request, page_href[8:])
        m.formatter = formatter = formatter(self.request, page)

        # XXX: Some macros uses macro.request.formatter instead of macro.formatter
        self.request.formatter.setPage(page)

        try:
            ret = m.execute(name, args)
        except ImportError, err:
            errmsg = unicode(err)
            if not name in errmsg:
                raise
            if alt:
                attrib_error = {ET.QName('title', namespaces.moin_page): errmsg}
                elem_error = ET.Element(ET.QName('span', namespaces.moin_page), attrib=attrib_error)
                elem_error.append(alt)
                elem_body.append(elem_error)
            else:
                elem_body.append(errmsg)
            elem.append(elem_body)
            return
        except NotImplementedError, e:
            # Force usage of fallback
            from warnings import warn
            message = 'Macro ' + name + ' calls methods in the compatibility formatter which are not implemented'
            if e.message:
                message += ': ' + e.message
            warn(message, DeprecationWarning)
            ret = True

        if ret:
            # Fallback to included parser
            formatter = wikiutil.searchAndImportPlugin(self.request.cfg, "formatter", 'text/html')
            m.formatter = formatter(self.request)
            m.formatter.setPage(page)

            ret = m.execute(name, args)

            formatter = wikiutil.searchAndImportPlugin(self.request.cfg, "formatter", 'compatibility')
            formatter = formatter(self.request, page)
            formatter.rawHTML(ret)

        elem_body.extend(formatter.root[:])

    def recurse(self, elem, page_href):
        page_href = elem.get(self.tag_page_href, page_href)

        if elem.tag == self.tag_macro:
            yield elem, page_href

        for child in elem:
            if isinstance(child, ET.Node):
                for i in self.recurse(child, page_href):
                    yield i

    def __call__(self, tree, request):
        self.request = request

        for elem, page_href in self.recurse(tree, None):
            self.handle_macro(elem, page_href)

        return tree

from _registry import default_registry
default_registry.register(Converter._factory)
