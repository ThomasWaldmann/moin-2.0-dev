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
    namespaces_visit = {
        namespaces.moin_page: 'moinpage',
    }
    namespaces_valid_output = frozenset([
        namespaces.html,
    ])

    def __call__(self, element):
        return self.visit(element)

    def do_attribs(self, element):
        default_uri = None
        if element.tag.uri in self.namespaces_valid_output:
            default_uri = element.tag.uri

        new = {}
        new_default = {}
        for key, value in element.attrib.iteritems():
            if key.uri in self.namespaces_valid_output:
                new[key] = value
            if default_uri is not None and key.uri is None:
                new_default[ElementTree.QName(key.name, default_uri)] = value
        new_default.update(new)
        return new_default

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

    def new(self, tag, attrib={}, children=[]):
        return ElementTree.Element(tag, attrib = attrib, children = children)

    def new_copy(self, tag, element, attrib = {}):
        attrib_new = self.do_attribs(element)
        attrib_new.update(attrib)
        children = self.do_children(element)
        return self.new(tag, attrib_new, children)

    def visit(self, elem):
        uri = elem.tag.uri
        name = self.namespaces_visit.get(uri, None)
        if name is not None:
            n = 'visit_' + name
            f = getattr(self, n, None)
            if f is not None:
                return f(elem)

        return self.new_copy(elem.tag, elem)

    def visit_moinpage(self, elem):
        n = 'visit_moinpage_' + elem.tag.name.replace('-', '_')
        f = getattr(self, n, None)
        if f is None:
            # TODO
            raise ElementException
        return f(elem)

    def visit_moinpage_a(self, elem):
        raise NotImplementedError

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

    def visit_moinpage_line_break(self, elem):
        return self.new(ElementTree.QName('br', namespaces.html))

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

