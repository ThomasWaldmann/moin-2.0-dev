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
        return self.visit_all(element)

    def recurse(self, func, element, old):
        new = []
        for child in old:
            if isinstance(child, ElementTree.Element):
                r = func(child)
            else:
                r = child
            if r is not None:
                new.append(r)
        element[:] = new
        return element

    def visit_all(self, elem):
        if elem.tag.uri in self._namespacelist_all:
            return self._namespacelist_block[elem.tag.uri](elem)

    def visit_inline(self, elem):
        if elem.tag.uri in self._namespacelist_inline:
            return self._namespacelist_block[elem.tag.uri](elem)

    def visit_html(self, elem):
        return self.recurse(self.visit_all, elem, elem)

    def visit_moinpage_all(self, elem):
        if elem.tag.name in self._taglist_moinpage_all:
            return self._taglist_moinpage_all[elem.tag.name](elem)

    def visit_moinpage_inline(self, elem):
        if elem.tag.name in self._taglist_moinpage_inline:
            return self._taglist_moinpage_inline[elem.tag.name](elem)

    def visit_moinpage_h(self, elem):
        new = ElementTree.Element(ElementTree.QName('hx', namespace.html))
        return self.recurse(self.visit_inline, new, elem)

    def visit_moinpage_p(self, elem):
        new = ElementTree.Element(ElementTree.QName('p', namespace.html))
        return self.recurse(self.visit_inline, new, elem)

    _namespacelist_all = {
        namespaces.moin_page: visit_moinpage_all,
    }

    _namespacelist_inline = {
        namespaces.moin_page: visit_moinpage_inline,
    }

    _taglist_moinpage_block = {
        'h': visit_moinpage_h,
        'p': visit_moinpage_p,
    }

    _taglist_moinpage_inline = {
    }

    _taglist_moinpage_all = _taglist_moinpage_block.copy().update(_taglist_moinpage_inline)

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

