"""
MoinMoin - HTML output converter

Converts an internal document tree into a HTML tree.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin import wikiutil
from MoinMoin.util.tree import html, moin_page, xlink


class ElementException(RuntimeError):
    pass


class Attribute(object):
    """ Adds the attribute with the HTML namespace to the output. """
    def __init__(self, key):
        self.key = html(key)

    def __call__(self, key, value, out):
        out[self.key] = value


class AttributeSimple(object):
    """ Adds the attribute with the HTML namespace to the output. """
    def __call__(self, key, value, out):
        out[html(key.name)] = value


class Attributes(object):
    namespaces_valid_output = frozenset([
        html.namespace,
    ])

    visit_number_columns_spanned = Attribute('colspan')
    visit_number_rows_spanned = Attribute('rowspan')
    visit_style = AttributeSimple()
    visit_title = AttributeSimple()

    def __init__(self, element):
        self.element = element

        # Detect if we either namespace of the element matches the input or the
        # output.
        self.default_uri_input = self.default_uri_output = None
        if element.tag.uri == moin_page.namespace:
            self.default_uri_input = element.tag.uri
        if element.tag.uri in self.namespaces_valid_output:
            self.default_uri_output = element.tag.uri

    def get(self, name):
        ret = self.element.get(moin_page(name))
        if ret:
            return ret
        if self.default_uri_input:
            return self.element.get(name)

    def convert(self):
        new = {}
        new_default = {}

        for key, value in self.element.attrib.iteritems():
            if key.uri == moin_page.namespace:
                # We never have _ in attribute names, so ignore them instead of
                # create ambigues matches.
                if not '_' in key.name:
                    n = 'visit_' + key.name.replace('-', '_')
                    f = getattr(self, n, None)
                    if f is not None:
                        f(key, value, new)
            elif key.uri in self.namespaces_valid_output:
                new[key] = value
            elif key.uri is None:
                if self.default_uri_input and not '_' in key.name:
                    n = 'visit_' + key.name.replace('-', '_')
                    f = getattr(self, n, None)
                    if f is not None:
                        f(key, value, new_default)
                elif self.default_uri_output:
                    new_default[ET.QName(key.name, self.default_uri_output)] = value

        # Attributes with namespace overrides attributes with empty namespace.
        new_default.update(new)

        return new_default


class Converter(object):
    """
    Converter application/x.moin.document -> application/x.moin.document
    """

    namespaces_visit = {
        moin_page.namespace: 'moinpage',
    }

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
        return ET.Element(tag, attrib=attrib, children=children)

    def new_copy(self, tag, element, attrib={}):
        attrib_new = Attributes(element).convert()
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

        href = elem.get(xlink.href, None)
        if href is not None:
            attrib[html.href] = href

        return self.new_copy(html.a, elem, attrib)

    def visit_moinpage_blockcode(self, elem):
        pre = self.new_copy(html.pre, elem)

        # TODO: Unify somehow
        if elem.get(html.class_) == 'codearea':
            attrib = {html.class_: 'codearea'}
            div = self.new(html.div, attrib)
            div.append(pre)
            return div

        return pre

    def visit_moinpage_code(self, elem):
        return self.new_copy(html.tt, elem)

    def visit_moinpage_div(self, elem):
        return self.new_copy(html.div, elem)

    def visit_moinpage_emphasis(self, elem):
        return self.new_copy(html.em, elem)

    def visit_moinpage_h(self, elem):
        level = elem.get(moin_page.outline_level, 1)
        try:
            level = int(level)
        except ValueError:
            raise ElementException('page:outline-level needs to be an integer')
        if level < 1:
            level = 1
        elif level > 6:
            level = 6
        return self.new_copy(ET.QName('h%d' % level, html.namespace), elem)

    def visit_moinpage_inline_part(self, elem):
        body = error = None

        for item in elem:
            if item.tag.uri == moin_page.namespace:
                if item.tag.name == 'inline-body':
                    body = item
                elif item.tag.name == 'error':
                    error = item

        if body:
            return self.new_copy(html.span, item)

        if error:
            if len(error):
                ret = html.span(children=error)
            else:
                ret = html.span(children=('Error', ))
            # XXX: Mark as error
            return ret

        # XXX: Move handling of namespace-less attributes into emeraldtree
        alt = elem.get(moin_page.alt, elem.get('alt'))
        if alt:
            return html.span(children=(alt, ))

        return html.span()

    def visit_moinpage_line_break(self, elem):
        # TODO: attributes?
        return self.new(html.br)

    def visit_moinpage_list(self, elem):
        attrib = Attributes(elem)
        attrib_new = attrib.convert()
        generate = attrib.get('item-label-generate')

        if generate:
            if generate == 'ordered':
                ret = self.new(html.ol, attrib_new)
            elif generate == 'unordered':
                ret = self.new(html.ul, attrib_new)
            else:
                raise ElementException('page:item-label-generate does not support "%s"' % generate)
        else:
            ret = self.new(html.dl, attrib_new)

        for item in elem:
            if item.tag.uri == moin_page.namespace and item.tag.name == 'list-item':
                if not generate:
                    for label in item:
                        if label.tag.uri == moin_page.namespace and label.tag.name == 'list-item-label':
                            ret_label = self.new_copy(html.dt, label)
                            ret.append(ret_label)

                for body in item:
                    if body.tag.uri == moin_page.namespace and body.tag.name == 'list-item-body':
                        if generate:
                            ret_body = self.new_copy(html.li, body)
                        else:
                            ret_body = self.new_copy(html.dd, body)
                        ret.append(ret_body)
                        break

        return ret

    def visit_moinpage_object(self, elem):
        href = elem.get(xlink.href, None)

        if href and wikiutil.isPicture(href):
            out_tag = html.img
            out_tag_href = html.src
        else:
            out_tag = html.object
            out_tag_href = html.data

        attrib = {}
        if href is not None:
            attrib[out_tag_href] = href
        return self.new(out_tag, attrib)

    def visit_moinpage_p(self, elem):
        return self.new_copy(html.p, elem)

    def visit_moinpage_page(self, elem):
        for item in elem:
            if item.tag.uri == moin_page.namespace and item.tag.name == 'body':
                return self.new_copy(html.div, item)

        raise RuntimeError('page:page need to contain exactly one page:body tag, got %r' % elem[:])

    def visit_moinpage_part(self, elem):
        body = error = None

        for item in elem:
            if item.tag.uri == moin_page.namespace:
                if item.tag.name == 'body':
                    body = item
                elif item.tag.name == 'error':
                    error = item

        if body:
            return self.new_copy(html.div, item)

        elif error:
            if len(error):
                ret = html.p(children=error)
            else:
                ret = html.p(children=('Error', ))
            # XXX: Mark as error
            return ret

        # XXX: Move handling of namespace-less attributes into emeraldtree
        alt = elem.get(moin_page.alt, elem.get('alt'))
        if alt:
            return html.p(children=(alt, ))

        return html.p()

    def visit_moinpage_separator(self, elem):
        return self.new(html.hr)

    def visit_moinpage_span(self, elem):
        # TODO
        return self.new_copy(html.span, elem)

    def visit_moinpage_strong(self, elem):
        return self.new_copy(html.strong, elem)

    def visit_moinpage_table(self, elem):
        attrib = Attributes(elem).convert()
        ret = self.new(html.table, attrib)
        for item in elem:
            tag = None
            if item.tag.uri == moin_page.namespace:
                if item.tag.name == 'table-body':
                    tag = html.tbody
                elif item.tag.name == 'table-header':
                    tag = html.thead
                elif item.tag.name == 'table-footer':
                    tag = html.tfoot
            elif item.tag.uri == html.namespace and \
                    item.tag.name in ('tbody', 'thead', 'tfoot'):
                tag = item.tag
            if tag is not None:
                ret.append(self.new_copy(tag, item))
        return ret

    def visit_moinpage_table_cell(self, elem):
        return self.new_copy(html.td, elem)

    def visit_moinpage_table_row(self, elem):
        return self.new_copy(html.tr, elem)


class SpecialId(object):
    def __init__(self):
        self._ids = {}

    def gen_id(self, id):
        nr = self._ids[id] = self._ids.get(id, 0) + 1
        return nr

    def gen_text(self, text):
        id = wikiutil.anchor_name_from_text(text)
        nr = self._ids[id] = self._ids.get(id, 0) + 1
        if nr == 1:
            return id
        return id + u'-%d' % nr


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


class ConverterPage(Converter):
    """
    Converter application/x.moin.document -> application/x-xhtml-moin-page
    """

    @classmethod
    def _factory(cls, request, input, output):
        if input == 'application/x.moin.document' and \
           output == 'application/x-xhtml-moin-page':
            return cls

    def __call__(self, element):
        _ = self.request.getText

        special_root = SpecialPage()
        self._special = [special_root]
        self._special_stack = [special_root]
        self._id = SpecialId()

        ret = super(ConverterPage, self).__call__(element)

        special_root.root = ret

        for special in self._special:
            for elem in special.footnotes():
                special.root.append(elem)

            for elem, headings in special.tocs():
                attrib_h = {html.class_: 'table-of-contents-heading'}
                elem_h = html.p(
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
                        stack_push(html.ol())
                        stack_push(html.li())
                        last_level += 1
                    if need_item:
                        stack.pop()
                        stack_push(html.li())

                    attrib = {html.href: '#' + id}
                    text = ''.join(elem.itertext())
                    elem_a = html.a(attrib, children=[text])
                    stack_top_append(elem_a)

        return ret

    def visit(self, elem):
        if elem.get(moin_page.page_href):
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

        raise ElementException('Unable to handle page:%s' % elem.tag.name)

    def visit_moinpage_h(self, elem):
        level = elem.get(moin_page.outline_level, 1)
        try:
            level = int(level)
        except ValueError:
            raise ElementException('page:outline-level needs to be an integer')
        if level < 1:
            level = 1
        elif level > 6:
            level = 6
        elem = self.new_copy(ET.QName('h%d' % level, html.namespace), elem)

        id = elem.get(html.id)
        if not id:
            id = self._id.gen_text(''.join(elem.itertext()))
            elem.set(html.id, id)

        self._special_stack[-1].add_heading(elem, level, id)
        return elem

    def visit_moinpage_note(self, elem):
        # TODO: Check note-class

        body = None
        for child in elem:
            if child.tag.uri == moin_page.namespace:
                if child.tag.name == 'note-body':
                    body = self.do_children(child)

        id = self._id.gen_id('note')

        elem_ref = ET.XML("""
<html:sup xmlns:html="%s" html:id="note-%d-ref"><html:a html:href="#note-%d">%d</html:a></html:sup>
""" % (html.namespace, id, id, id))

        elem_note = ET.XML("""
<html:p xmlns:html="%s" html:id="note-%d"><html:sup><html:a html:href="#note-%d-ref">%d</html:a></html:sup></html:p>
""" % (html.namespace, id, id, id))

        elem_note.extend(body)

        self._special_stack[-1].add_footnote(elem_note)

        return elem_ref

    def visit_moinpage_table_of_content(self, elem):
        level = int(elem.get(moin_page.outline_level, 6))

        attrib = {html.class_: 'table-of-contents'}
        elem = self.new(html.div, attrib)

        self._special_stack[-1].add_toc(elem, level)
        return elem


class ConverterDocument(ConverterPage):
    """
    Converter application/x.moin.document -> application/xhtml+xml
    """


from _registry import default_registry
default_registry.register(ConverterPage._factory)
