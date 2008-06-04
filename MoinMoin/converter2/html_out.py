"""
MoinMoin - HTML output converter

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree

from MoinMoin.util import namespaces

class ConverterBase(object):
    def recurse(self, element):
        new = []
        for child in element:
            if isinstance(child, ElementTree.Element):
                r = self.visit(child)
            else:
                r = child
            if r is not None:
                new.append(r)
        element[:] = new

    def visit(self, elem):
        if elem.tag.uri == namespaces.moin_page:
            return self.visit_moinpage(elem)
        # TODO
        raise Exception

    def visit_moinpage(self, elem):
        return elem

class Converter(ConverterBase):
    """
    Converter application/x-moin-document -> application/x-moin-document
    """

class ConverterPage(ConverterBase):
    """
    Converter application/x-moin-document -> application/x-xhtml-moin-page
    """

class ConverterDocument(ConverterPage):
    """
    Converter application/x-moin-document -> application/xhtml+xml
    """

