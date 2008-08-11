"""
MoinMoin - HTML output converter

Converts an internal document tree into a HTML tree.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin import wikiutil
from MoinMoin.util import namespaces

class ElementException(RuntimeError):
    pass

class Attrib(object):
    tag_style = ET.QName('style', namespaces.html)

    def simple_attrib(self, key, value, out, out_style):
        """ Adds the attribute with the HTML namespace to the output. """
        out[ET.QName(key.name, namespaces.html)] = value

    visit_title = simple_attrib

    def simple_style(self, key, value, out, out_style):
        """ Adds the attribute to the HTML style attribute. """
        out_style[key.name] = value

    visit_background_color = simple_style
    visit_font_size = simple_style
    visit_text_align = simple_style
    visit_vertical_align = simple_style

    def __init__(self, element):
        self.element = element

        # Detect if we either namespace of the element matches the input or the
        # output.
        self.default_uri_input = self.default_uri_output = None
        if element.tag.uri == namespaces.moin_page:
            self.default_uri_input = element.tag.uri
        if element.tag.uri in ConverterBase.namespaces_valid_output:
            self.default_uri_output = element.tag.uri

    def get(self, name):
        ret = self.element.get(ET.QName(name, namespaces.moin_page))
        if ret:
            return ret
        if self.default_uri_input:
            return self.element.get(name)

    def new(self):
        new = {}
        new_css = {}
        new_default = {}
        new_default_css = {}

        for key, value in self.element.attrib.iteritems():
            if key.uri == namespaces.moin_page:
                # We never have _ in attribute names, so ignore them instead of
                # create ambigues matches.
                if not '_' in key.name:
                    n = 'visit_' + key.name.replace('-', '_')
                    f = getattr(self, n, None)
                    if f is not None:
                        f(key, value, new, new_css)
            elif key.uri in ConverterBase.namespaces_valid_output:
                new[key] = value
            elif key.uri is None:
                if self.default_uri_input and not '_' in key.name:
                    n = 'visit_' + key.name.replace('-', '_')
                    f = getattr(self, n, None)
                    if f is not None:
                        f(key, value, new_default, new_default_css)
                elif self.default_uri_output:
                    new_default[ET.QName(key.name, self.default_uri_output)] = value

        # Attributes with namespace overrides attributes with empty namespace.
        new_default.update(new)
        new_default_css.update(new_css)

        # Create CSS style attribute
        if new_default_css:
            style = new_default_css.items()
            style.sort(key=lambda i: i[0])
            style = '; '.join((key + ': ' + value for key, value in style))

            style_old = self.element.get(self.tag_style)
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

    tag_html_a = ET.QName('a', namespaces.html)
    tag_html_class = ET.QName('class', namespaces.html)
    tag_html_data = ET.QName('data', namespaces.html)
    tag_html_div = ET.QName('div', namespaces.html)
    tag_html_em = ET.QName('em', namespaces.html)
    tag_html_href = ET.QName('href', namespaces.html)
    tag_html_id = ET.QName('id', namespaces.html)
    tag_html_img = ET.QName('img', namespaces.html)
    tag_html_object = ET.QName('object', namespaces.html)
    tag_html_p = ET.QName('p', namespaces.html)
    tag_html_src = ET.QName('src', namespaces.html)
    tag_html_sup = ET.QName('sup', namespaces.html)
    tag_xlink_href = ET.QName('href', namespaces.xlink)

    def __init__(self, request):
        self.request = request

    def __call__(self, element):
        return self.visit(element)

    def do_children(self, element):
        new = []
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r, )
                new.extend(r)
            else:
                new.append(child)
        return new

    def new(self, tag, attrib={}, children=[]):
        return ET.Element(tag, attrib = attrib, children = children)

    def new_copy(self, tag, element, attrib={}):
        attrib_new = Attrib(element).new()
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

        # Element with unknown namespaces are just copied
        return self.new_copy(elem.tag, elem)

    def visit_moinpage(self, elem):
        n = 'visit_moinpage_' + elem.tag.name.replace('-', '_')
        f = getattr(self, n, None)
        if f:
            return f(elem)

        # Unknown element are just copied
        return self.new_copy(elem.tag, elem)

    def visit_moinpage_a(self, elem):
        attrib = {}

        href = elem.get(self.tag_xlink_href, None)
        if href is not None:
            attrib[self.tag_html_href] = href

        return self.new_copy(self.tag_html_a, elem, attrib)

    def visit_moinpage_blockcode(self, elem):
        pre = self.new_copy(ET.QName('pre', namespaces.html), elem)

        # TODO: Unify somehow
        if elem.get(self.tag_html_class) == 'codearea':
            attrib = {ET.QName('class', namespaces.html): 'codearea'}
            div = self.new(ET.QName('div', namespaces.html), attrib)
            div.append(pre)
            return div

        return pre

    def visit_moinpage_code(self, elem):
        return self.new_copy(ET.QName('tt', namespaces.html), elem)

    def visit_moinpage_div(self, elem):
        return self.new_copy(self.tag_html_div, elem)

    def visit_moinpage_emphasis(self, elem):
        return self.new_copy(self.tag_html_em, elem)

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
        # TODO: attributes?
        return self.new(ET.QName('br', namespaces.html))

    def visit_moinpage_list(self, elem):
        attrib = Attrib(elem)
        generate = attrib.get('item-label-generate')

        if generate:
            if generate == 'ordered':
                ret = self.new(ET.QName('ol', namespaces.html))
            elif generate == 'unordered':
                ret = self.new(ET.QName('ul', namespaces.html))
            else:
                raise ValueError('List label generation not supported: ' + generate)
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

    def visit_moinpage_object(self, elem):
        href = elem.get(self.tag_xlink_href, None)

        if href and wikiutil.isPicture(href):
            out_tag = self.tag_html_img
            out_tag_href = self.tag_html_src
        else:
            out_tag = self.tag_html_object
            out_tag_href = self.tag_html_data

        attrib = {}
        if href is not None:
            attrib[out_tag_href] = href
        return self.new(out_tag, attrib)

    def visit_moinpage_p(self, elem):
        return self.new_copy(self.tag_html_p, elem)

    def visit_moinpage_page(self, elem):
        return self.new_copy(self.tag_html_div, elem)

    def visit_moinpage_separator(self, elem):
        return self.new(ET.QName('hr', namespaces.html))

    def visit_moinpage_span(self, elem):
        # TODO
        return self.new_copy(ET.QName('span', namespaces.html), elem)

    def visit_moinpage_strong(self, elem):
        return self.new_copy(ET.QName('strong', namespaces.html), elem)

    def visit_moinpage_table(self, elem):
        attrib = Attrib(elem).new()
        ret = self.new(ET.QName('table', namespaces.html), attrib)
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

class SpecialPage(object):
    def __init__(self):
        self._footnotes = []
        self._headings = []
        self._tocs = []

    def add_footnote(self, elem):
        self._footnotes.append(elem)

    def add_heading(self, elem, level, id=None):
        self._headings.append((elem, level, id))

    def add_toc(self, elem, maxlevel):
        self._tocs.append((elem, maxlevel))

    def extend(self, page):
        self._headings.extend(page._headings)

    def footnotes(self):
        return iter(self._footnotes)

    def headings(self, maxlevel):
        minlevel = None
        for title, level, id in self._headings:
            if minlevel is None or level < minlevel:
                minlevel = level

        for elem, level, id in self._headings:
            if level > maxlevel:
                continue
            # We crop all overline levels above the first used.
            level = level - minlevel + 1
            yield elem, level, id

    def tocs(self):
        for elem, maxlevel in self._tocs:
            yield elem, self.headings(maxlevel)

class ConverterPage(ConverterBase):
    """
    Converter application/x-moin-document -> application/x-xhtml-moin-page
    """

    @classmethod
    def _factory(cls, request, input, output):
        if input == 'application/x-moin-document' and \
           output == 'application/x-xhtml-moin-page':
            return cls

    def __call__(self, element):
        _ = self.request.getText

        special_root = SpecialPage()
        self._special = [special_root]
        self._special_stack = [special_root]
        self._note_id = 1
        self._toc_id = 0

        ret = super(ConverterPage, self).__call__(element)

        special_root.root = ret

        for special in self._special:
            for elem in special.footnotes():
                special.root.append(elem)

            for elem, headings in special.tocs():
                attrib_h = {ET.QName('class', namespaces.html): 'table-of-contents-heading'}
                elem_h = ET.Element(ET.QName('p', namespaces.html),
                        attrib=attrib_h, children=[_('Contents')])
                elem.append(elem_h)

                stack = [elem]
                def stack_push(elem):
                    stack[-1].append(elem)
                    stack.append(elem)
                def stack_top_append(elem):
                    stack[-1].append(elem)

                last_level = 0
                for elem, level, id in headings:
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
                    text = ''.join(elem.itertext())
                    elem_a = ET.Element(ET.QName('a', namespaces.html), attrib, children=[text])
                    stack_top_append(elem_a)

        return ret

    def visit(self, elem):
        if elem.get(ET.QName('page-href', namespaces.moin_page)):
            self._special_stack.append(SpecialPage())

            ret = super(ConverterPage, self).visit(elem)

            sp = self._special_stack.pop()
            sp.root = ret
            self._special.append(sp)
            self._special_stack[-1].extend(sp)
            return ret
        else:
            return super(ConverterPage, self).visit(elem)

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
            id = 'toc-%d' % self._toc_id
            elem.set(ET.QName('id', namespaces.html), id)
            self._toc_id += 1

        self._special_stack[-1].add_heading(elem, level, id)
        return elem

    def visit_moinpage_note(self, elem):
        # TODO: Check note-class

        body = None
        for child in elem:
            if child.tag.uri == namespaces.moin_page:
                if child.tag.name == 'note-body':
                    body = self.do_children(child)

        id = self._note_id
        self._note_id += 1
        id_note = 'note-%d' % id
        id_ref = 'note-%d-ref' % id

        elem_ref = ET.XML("""
<html:sup xmlns:html="%s" html:id="%s"><html:a html:href="#%s">%s</html:a></html:sup>
""" % (namespaces.html, id_ref, id_note, id))

        elem_note = ET.XML("""
<html:p xmlns:html="%s" html:id="%s"><html:sup><html:a html:href="#%s">%s</html:a></html:sup></html:p>
""" % (namespaces.html, id_note, id_ref, id))

        elem_note.extend(body)

        self._special_stack[-1].add_footnote(elem_note)

        return elem_ref

    def visit_moinpage_macro(self, elem):
        for body in elem:
            if body.tag.uri == namespaces.moin_page and body.tag.name == 'macro-body':
                return self.do_children(body)

    def visit_moinpage_table_of_content(self, elem):
        level = int(elem.get(ET.QName('outline-level', namespaces.moin_page), 6))

        attrib = {ET.QName('class', namespaces.html): 'table-of-contents'}
        elem = self.new(ET.QName('div', namespaces.html), attrib)

        self._special_stack[-1].add_toc(elem, level)
        return elem

class ConverterDocument(ConverterPage):
    """
    Converter application/x-moin-document -> application/xhtml+xml
    """

from _registry import default_registry
default_registry.register(ConverterPage._factory)
