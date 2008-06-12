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
    namespaces = {
        namespaces.moin_page: 'moinpage',
    }

    def __call__(self, element):
        return self.visit(element)

    def do_attribs(self, element):
        new = {}
        for key, value in element.attrib.iteritems():
            if key.uri != namespaces.moin_page:
                new[key] = value
        return new

    def do_children(self, element):
        new = []
        for child in element:
            if isinstance(child, ElementTree.Element):
                r = self.visit(child)
                if r is not None:
                    new.append(r)
            else:
                new.append(child)
        return new

    def new(self, tag, attrib, children):
        return ElementTree.Element(tag, attrib = attrib, children = children)

    def new_copy(self, tag, element, attrib = {}):
        attrib_new = self.do_attribs(element)
        attrib_new.update(attrib)
        children = self.do_children(element)
        return self.new(tag, attrib_new, children)

    def visit(self, elem):
        uri = elem.tag.uri
        name = self.namespaces.get(uri, None)
        if name is not None:
            n = 'visit_' + name
            f = getattr(self, n, None)
            if f is not None:
                return f(elem)

        return self.new_copy(elem.tag, elem)

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
        return self.new_copy(ElementTree.QName('h%d' % level, namespaces.html), elem)

    def visit_moinpage_p(self, elem):
        return self.new_copy(ElementTree.QName('p', namespaces.html), elem)

    def visit_moinpage_page(self, elem):
        return self.new_copy(ElementTree.QName('div', namespaces.html), elem)

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

