"""
MoinMoin - Include handling

Expands include elements in a internal Moin document.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.util import namespaces

class Converter(object):
    tag_div = ET.QName('div', namespaces.moin_page)
    tag_page_href = ET.QName('page-href', namespaces.moin_page)
    tag_xi_href = ET.QName('href', namespaces.xinclude)
    tag_xi_include = ET.QName('include', namespaces.xinclude)
    tag_xi_xpointer = ET.QName('xpointer', namespaces.xinclude)

    @classmethod
    def _factory(cls, input, output):
        if input == 'application/x-moin-document' and \
                output == 'application/x-moin-document;includes=expandall':
            return cls

    def recurse(self, elem, page_href):
        # TODO: Check for cycles
        page_href = elem.get(self.tag_page_href, page_href)

        if elem.tag == self.tag_xi_include:
            href = elem.get(self.tag_xi_href)
            xpointer = elem.get(self.tag_xi_xpointer)

            if href:
                if href.startswith('wiki:///'):
                    include = href[8:]
                elif href.startswith('wiki.local:'):
                    include = wikiutil.AbsPageName(page_href[8:], href[11:])

                doc = Page(self.request, include).convert_input_cache(self.request)
                pages = ((doc, 'wiki:///' + include),)
            else:
                raise NotImplementedError

            div = ET.Element(self.tag_div)

            for page_doc, page_href in pages:
                page_doc.tag = self.tag_div
                self.recurse(page_doc, page_href)
                div.append(page_doc)

            return div

        for i in xrange(len(elem)):
            child = elem[i]
            if isinstance(child, ET.Node):
                ret = self.recurse(child, page_href)
                if ret:
                    elem[i] = ret

    def __init__(self, request):
        self.request = request

    def __call__(self, tree):
        self.recurse(tree, None)
        return tree

from _registry import default_registry
default_registry.register(Converter._factory)
