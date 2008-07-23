"""
MoinMoin - HTML output converter

Converts an internal document into HTML.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin.util import namespaces

class ElementException(RuntimeError):
    pass

class Attrib(object):
    tag_style = ET.QName('style', namespaces.html)

    def simple_css(self, key, value, out, out_style):
        out_style[key.name] = value

    visit_background_color = simple_css
    visit_font_size = simple_css

    def __call__(self, element):
        new = {}
        new_css = {}
        new_default = {}
        new_default_css = {}

        default_uri_input = default_uri_output = None
        if element.tag.uri == namespaces.moin_page:
            default_uri_input = element.tag.uri
        if element.tag.uri in ConverterBase.namespaces_valid_output:
            default_uri_output = element.tag.uri

        for key, value in element.attrib.iteritems():
            if key.uri == namespaces.moin_page:
                if not '_' in key.name:
                    n = 'visit_' + key.name.replace('-', '_')
                    f = getattr(self, n, None)
                    if f is not None:
                        f(key, value, new, new_css)
            elif key.uri in ConverterBase.namespaces_valid_output:
                new[key] = value
            elif key.uri is None:
                if default_uri_input and not '_' in key.name:
                    n = 'visit_' + key.name.replace('-', '_')
                    f = getattr(self, n, None)
                    if f is not None:
                        f(key, value, new_default, new_default_css)
                elif default_uri_output:
                    new_default[ET.QName(key.name, default_uri_output)] = value

        new_default.update(new)
        new_default_css.update(new_css)

        if new_default_css:
            style = new_default_css.items()
            style.sort(key=lambda i: i[0])
            style = '; '.join((key + ': ' + value for key, value in style))

            style_old = element.get(self.tag_style)
            if style_old:
                style += '; ' + style_old

            new_default[self.tag_style] = style

        return new_default

class ConverterBase(object):
    namespaces_visit = {
        namespaces.moin_page: 'moinpage',
    }
    namespaces_valid_output = frozenset([
        namespaces.html,
    ])

    def __call__(self, element, request):
        return self.visit(element)

    def do_children(self, element):
        new = []
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r,)
                new.extend(r)
            else:
                new.append(child)
        return new

    def new(self, tag, attrib={}, children=[]):
        return ET.Element(tag, attrib = attrib, children = children)

    def new_copy(self, tag, element, attrib={}):
        attrib_new = Attrib()(element)
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
        if f:
            return f(elem)

        return self.new_copy(elem.tag, elem)

    def visit_moinpage_a(self, elem):
        # TODO
        attrib = {}

        tag_href_xlink = ET.QName('href', namespaces.xlink)
        tag_href = ET.QName('href', namespaces.html)
        href = elem.get(tag_href_xlink, None)
        if href is not None:
            attrib[tag_href] = href

        return self.new_copy(ET.QName('a', namespaces.html), elem, attrib)

    def visit_moinpage_blockcode(self, elem):
        return self.new_copy(ET.QName('pre', namespaces.html), elem)

    def visit_moinpage_code(self, elem):
        return self.new_copy(ET.QName('tt', namespaces.html), elem)

    def visit_moinpage_div(self, elem):
        # TODO
        return self.new_copy(ET.QName('div', namespaces.html), elem)

    def visit_moinpage_emphasis(self, elem):
        return self.new_copy(ET.QName('em', namespaces.html), elem)

    def visit_moinpage_h(self, elem):
        level = elem.get(ET.QName('outline-level', namespaces.moin_page), 1)
        try:
            level = int(level)
        except ValueError:
            raise ElementException
        if level < 1:
            level = 1
        elif level > 6:
            level = 6
        return self.new_copy(ET.QName('h%d' % level, namespaces.html), elem)

    def visit_moinpage_line_break(self, elem):
        return self.new(ET.QName('br', namespaces.html))

    def visit_moinpage_list(self, elem):
        generate = elem.get(ET.QName('item-label-generate', namespaces.moin_page))
        
        if generate == 'ordered':
            ret = self.new(ET.QName('ol', namespaces.html))
        elif generate:
            ret = self.new(ET.QName('ul', namespaces.html))
        else:
            ret = self.new(ET.QName('dl', namespaces.html))

        for item in elem:
            if item.tag.uri == namespaces.moin_page and item.tag.name == 'list-item':
                if not generate:
                    for label in item:
                        if label.tag.uri == namespaces.moin_page and label.tag.name == 'list-item-label':
                            ret_label = self.new_copy(ET.QName('dt', namespaces.html), label)
                            ret.append(ret_label)

                for body in item:
                    if body.tag.uri == namespaces.moin_page and body.tag.name == 'list-item-body':
                        if generate:
                            ret_body = self.new_copy(ET.QName('li', namespaces.html), body)
                        else:
                            ret_body = self.new_copy(ET.QName('dd', namespaces.html), body)
                        ret.append(ret_body)
                        break

        return ret

    def visit_moinpage_note(self, elem):
        # TODO
        pass

    def visit_moinpage_object(self, elem):
        attrib = {}

        tag_href_xlink = ET.QName('href', namespaces.xlink)
        tag_data = ET.QName('data', namespaces.html)
        href = elem.get(tag_href_xlink, None)
        if href is not None:
            attrib[tag_data] = href

        return self.new(ET.QName('object', namespaces.html), attrib)

    def visit_moinpage_p(self, elem):
        return self.new_copy(ET.QName('p', namespaces.html), elem)

    def visit_moinpage_page(self, elem):
        return self.new_copy(ET.QName('div', namespaces.html), elem)

    def visit_moinpage_separator(self, elem):
        return self.new(ET.QName('hr', namespaces.html))

    def visit_moinpage_span(self, elem):
        # TODO
        return self.new_copy(ET.QName('span', namespaces.html), elem)

    def visit_moinpage_strong(self, elem):
        return self.new_copy(ET.QName('strong', namespaces.html), elem)

    def visit_moinpage_table(self, elem):
        ret = self.new(ET.QName('table', namespaces.html))
        for item in elem:
            tag = None
            if item.tag.uri == namespaces.moin_page:
                if item.tag.name == 'table-body':
                    tag = ET.QName('tbody', namespaces.html)
                elif item.tag.name == 'table-header':
                    tag = ET.QName('thead', namespaces.html)
                elif item.tag.name == 'table-footer':
                    tag = ET.QName('tfoot', namespaces.html)
            elif item.tag.uri == namespaces.html and \
                    item.tag.name in ('tbody', 'thead', 'tfoot'):
                tag = item.tag
            if tag is not None:
                ret.append(self.new_copy(tag, item))
        return ret

    def visit_moinpage_table_cell(self, elem):
        return self.new_copy(ET.QName('td', namespaces.html), elem)

    def visit_moinpage_table_row(self, elem):
        return self.new_copy(ET.QName('tr', namespaces.html), elem)

class Converter(ConverterBase):
    """
    Converter application/x-moin-document -> application/x-moin-document
    """

class ConverterPage(ConverterBase):
    """
    Converter application/x-moin-document -> application/x-xhtml-moin-page
    """

    @classmethod
    def _factory(cls, input, output):
        if input == 'application/x-moin-document' and \
           output == 'application/x-xhtml-moin-page':
            return cls()

    def __call__(self, element, request):
        self._table_of_content_element = None
        self._table_of_content_id = 0
        self._table_of_content_maxlevel = -1
        self._table_of_content_list = []

        ret = super(ConverterPage, self).__call__(element, request)

        elem = self._table_of_content_element
        if elem:
            # TODO: gettext
            attrib_h = {ET.QName('class', namespaces.html): 'table-of-contents-heading'}
            elem_h = ET.Element(ET.QName('p', namespaces.html),
                    attrib=attrib_h, children=['Contents'])
            elem.append(elem_h)

            stack = [elem]
            def stack_push(elem):
                stack[-1].append(elem)
                stack.append(elem)
            def stack_top_append(elem):
                stack[-1].append(elem)

            last_level = 0
            for level, id, text in self._table_of_content_list:
                if level > self._table_of_content_maxlevel:
                    continue

                need_item = last_level >= level
                while last_level > level:
                    stack.pop()
                    stack.pop()
                    last_level -= 1
                while last_level < level:
                    stack_push(ET.Element(ET.QName('ol', namespaces.html)))
                    stack_push(ET.Element(ET.QName('li', namespaces.html)))
                    last_level += 1
                if need_item:
                    stack.pop()
                    stack_push(ET.Element(ET.QName('li', namespaces.html)))

                attrib = {ET.QName('href', namespaces.html): '#' + id}
                elem = ET.Element(ET.QName('a', namespaces.html), attrib, children=[text])
                stack_top_append(elem)

        return ret

    def visit_moinpage(self, elem):
        n = 'visit_moinpage_' + elem.tag.name.replace('-', '_')
        f = getattr(self, n, None)
        if f:
            return f(elem)

        raise ElementException(n)

    def visit_moinpage_h(self, elem):
        level = elem.get(ET.QName('outline-level', namespaces.moin_page), 1)
        try:
            level = int(level)
        except ValueError:
            raise ElementException
        if level < 1:
            level = 1
        elif level > 6:
            level = 6
        elem = self.new_copy(ET.QName('h%d' % level, namespaces.html), elem)

        id = elem.get(ET.QName('id', namespaces.html))
        if not id:
            id = 'toc-%d' % self._table_of_content_id
            elem.set(ET.QName('id', namespaces.html), id)
            self._table_of_content_id += 1

        text = u''.join(elem.itertext())
        self._table_of_content_list.append((level, id, text))
        return elem

    def visit_moinpage_macro(self, elem):
        for body in elem:
            if body.tag.uri == namespaces.moin_page and body.tag.name == 'macro-body':
                return self.do_children(body)

    def visit_moinpage_table_of_content(self, elem):
        level = int(elem.get(ET.QName('outline-level', namespaces.moin_page), 6))

        attrib = {ET.QName('class', namespaces.html): 'table-of-contents'}
        elem = self.new(ET.QName('div', namespaces.html), attrib)

        self._table_of_content_element = elem
        self._table_of_content_maxlevel = level
        return elem

class ConverterDocument(ConverterPage):
    """
    Converter application/x-moin-document -> application/xhtml+xml
    """

from _registry import default_registry
default_registry.register(ConverterPage._factory)
