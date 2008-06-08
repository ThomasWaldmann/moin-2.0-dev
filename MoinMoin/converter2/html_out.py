"""
MoinMoin - HTML output converter

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree

from MoinMoin.util import namespaces

class ElementException(RuntimeError):
    pass

class ConverterBase(object):
    def __call__(self, element):
        return self.visit(element)

    def recurse(self, element, old):
        new = []
        for child in old:
            if isinstance(child, ElementTree.Element):
                r = self.visit(child)
            else:
                r = child
            if r is not None:
                new.append(r)
        element[:] = new
        return element

    def visit(self, elem):
        if elem.tag.uri in self._namespacelist:
            return self._namespacelist[elem.tag.uri](self, elem)

    def visit_html(self, elem):
        return self.recurse(elem, elem)

    def visit_moinpage(self, elem):
        if elem.tag.name in self._taglist_moinpage:
            return self._taglist_moinpage[elem.tag.name](self, elem)
        raise ElementException

    def visit_moinpage_h(self, elem):
        new = ElementTree.Element(ElementTree.QName('hx', namespaces.html))
        return self.recurse(new, elem)

    def visit_moinpage_p(self, elem):
        new = ElementTree.Element(ElementTree.QName('p', namespaces.html))
        return self.recurse(new, elem)

    def visit_moinpage_page(self, elem):
        new = ElementTree.Element(ElementTree.QName('div', namespaces.html))
        return self.recurse(new, elem)

    _namespacelist = {
        namespaces.moin_page: visit_moinpage,
    }

    _taglist_moinpage = {
        'h': visit_moinpage_h,
        'p': visit_moinpage_p,
        'page': visit_moinpage_page,
    }

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

