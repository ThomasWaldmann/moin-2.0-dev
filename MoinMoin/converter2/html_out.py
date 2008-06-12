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

    def recurse_element(self, children):
        new = []
        for child in children:
            if isinstance(child, ElementTree.Element):
                r = self.visit(child)
            else:
                r = child
            if r is not None:
                new.append(r)
        return new

    def visit(self, elem):
        if elem.tag.uri in self._namespacelist:
            return self._namespacelist[elem.tag.uri](self, elem)

        children = self.recurse_element(elem)
        return ElementTree.Element(elem.tag, children = children)

    def visit_moinpage(self, elem):
        n = 'visit_moinpage_' + elem.tag.name
        f = getattr(self, n, None)
        if f is None:
            # TODO
            raise ElementException
        return f(elem)

    def visit_moinpage_h(self, elem):
        level = elem.get(ElementTree.QName('outline-level', namespaces.moin_page), 1)
        try:
            level = int(level)
        except TypeError:
            raise ElementException
        if level < 1:
            level = 1
        elif level > 6:
            level = 6
        children = self.recurse_element(elem)
        return ElementTree.Element(ElementTree.QName('h%d' % level, namespaces.html), children = children)

    def visit_moinpage_p(self, elem):
        children = self.recurse_element(elem)
        return ElementTree.Element(ElementTree.QName('p', namespaces.html), children = children)

    def visit_moinpage_page(self, elem):
        children = self.recurse_element(elem)
        return ElementTree.Element(ElementTree.QName('div', namespaces.html), children = children)

    _namespacelist = {
        namespaces.moin_page: visit_moinpage,
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

