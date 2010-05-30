"""
MoinMoin - Moinwiki markup output converter

Converts an internal document tree into moinwiki markup.

This is preprealpha version, do not use it, it doesn't work.

@copyright: 2008 MoinMoin:BastianBlank
            2010 MoinMoin:DmitryAndreev
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

from MoinMoin.util.tree import moin_page, xlink

from emeraldtree import ElementTree as ET


class Moinwiki(object):
    '''
    Moinwiki syntax elements
    It's dummy
    '''
    h = '='
    a_open = '[['
    a_middle = '|'
    a_close = ']]'
    verbatim_open = '{{{'
    verbatim_close = '}}}'
    monospace = '`'
    strong = "'''"
    emphasis = "''"
    underline = '__'
    stroke_open = '--('
    stroke_close = ')--'
    table_marker = '||'
    p = '\n\n'
    linebreak = '<<BR>>'
    larger_open = '~+'
    larger_close = '+~'
    smaller_open = '~-'
    smaller_close = '-~'

    # TODO: definition list
    list_type = {\
        ('definition', None): '',\
        ('ordered', None): '1.',\
        ('ordered', 'lower-alpha'): 'a.',\
        ('ordered', 'upper-alpha'): 'A.',\
        ('ordered', 'lower-roman'): 'i.',\
        ('ordered', 'upper-roman'): 'I.',\
        ('unordered', None): '*'}

    def __init__(self):
        pass


class Converter(object):
    """
    Converter application/x.moin.document -> text/x.moin.wiki
    """
    namespaces = {
        moin_page.namespace: 'moinpage'}

    supported_tag = {
        'moinpage': (
                'a',
                'blockcode',
                'break_line',
                'code',
                'div',
                'emphasis',
                'h',
                'list',
                'list_item',
                'list_item_label',
                'list_item_body',
                'p',
                'page',
                'separator',
                'span',
                'strong',
                'object',
                'table',
                'table_header',
                'teble_footer',
                'table_body',
                'table_row',
                'table_cell')}

    @classmethod
    def _factory(cls, request, input, output, **kw):
        if input == 'application/x.moin.document' and \
                output == 'text/x.moin.wiki':
            return cls

    def __init__(self, request):

        # TODO: create class containing all table attributes
        self.table_tableclass = ''
        self.table_tablestyle = ''
        self.table_rowsclass = ''
        self.table_rowsstyle = ''
        self.table_rowstyle = ''
        self.table_rowclass = ''

        self.list_item_labels = ['', ]
        self.list_item_label = ''
        self.list_level = 0

        self.request = request

    def __call__(self, root):
        self.opened = [None, ]
        self.children = [None, iter([root])]
        self.output = []
        self.list_item_lable = []
        while self.children[-1]:
            try:
                next_child = self.children[-1].next()
                if isinstance(next_child, ET.Element):
                    self.output.append(self.open(next_child))
                else:
                    self.output.append(next_child)
            except StopIteration:
                self.children.pop()
                next_parent = self.opened.pop()
                if next_parent:
                    self.output.append(self.close(next_parent))

        return ''.join(self.output)

    def open(self, elem):
        uri = elem.tag.uri
        name = self.namespaces.get(uri, None)
        if name is not None:
            n = 'open_' + name
            f = getattr(self, n, None)
            if f is not None:
                return f(elem)
        return ''

    def open_moinpage(self, elem):
        n = 'open_moinpage_' + elem.tag.name.replace('-', '_')
        f = getattr(self, n, None)
        if f:
            return f(elem)
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ''

    def close(self, elem):
        uri = elem.tag.uri
        name = self.namespaces.get(uri, None)
        if name is not None:
            n = 'close_' + name
            f = getattr(self, n, None)
            if f is not None:
                return f(elem)
        return ''

    def close_moinpage(self, elem):
        n = 'close_moinpage_' + elem.tag.name.replace('-', '_')
        f = getattr(self, n, None)
        if f:
            return f(elem)
        return ''

    def open_moinpage_a(self, elem):
        ret = a_open
        ret += elem.get(xlink.href, None)
        text = ''.join(elem.itertext())
        if text:
            ret += Moinwiki.a_middle
            ret += text
        return ret + a.close

    def close_moinpage_a(self, elem):
        # dummy, open_moinpage_a does all the job
        return a.close

    def open_moinpage_blockcode(self, elem):
        ret = Moinwiki.verbatim_open
        ret += ''.join(elem.itertext())
        ret += Moinwiki.verbatim_close
        return ret

    def close_moinpage_blockcode(self, elem):
        # Dummy, open_moinpage_code is does all the job
        return ''

    def open_moinpage_code(self, elem):
        ret = Moinwiki.monospace
        ret += ''.join(elem.itertext())
        ret += Moinwiki.monospace
        return ret

    def close_moinpage_code(self, elem):
        # Dummy, open_moinpage_code is does all the job
        return ''

    def open_moinpage_div(self, elem):
        return ''

    def close_moinpage_div(self, elem):
        return ''

    def open_moinpage_emphasis(self, elem):
        ret = Moinwiki.emphasis
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ret

    def close_moinpage_emphasis(self, elem):
        return Moinwiki.emphasis

    def open_moinpage_h(self, elem):
        level = elem.get(moin_page.outline_level, 1)
        try:
            level = int(level)
        except ValueError:
            raise ElementException('page:outline-level needs to be an integer')
        if level < 1:
            level = 1
        elif level > 6:
            level = 6
        ret = Moinwiki.h * level + ' '
        ret += ''.join(elem.itertext())
        ret += ' ' + Moinwiki.h * level
        return ret

    def close_moinpage_h():
        # Dummy, open_moinpage_h does all the job
        return ''

    def open_moinpage_line_break(self, elem):
        return Moinwiki.linebreak

    def open_moinpage_list(self, elem):
        label_type = (elem.get(moin_page.item_label_generate, None), \
                        elem.get(moin_page.list_style_type, None))
        print label_type
        self.list_item_labels.append(\
            Moinwiki.list_type.get(label_type, ''))
        self.children.append(iter(elem))
        self.opened.append(elem)
        self.list_level += 1
        return ''

    def close__moinpage_list(self, elem):
        self.list_item_labels.pop()
        self.list_level -= 1
        return ''

    def open_moinpage_list_item(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        self.list_item_label = self.list_item_labels[-1] + ' '
        return ' ' * self.list_level + self.list_item_label

    def close_moinpage_list_item(self, elem):
        return '\n'

    def open_moinpage_list_item_label(self, elem):
        return ''

    def close_moinpage_list_item_label(self, elem):
        return ''

    def open_moinpage_list_item_body(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ''

    def close_moinpage_list_item_body(self, elem):
        return ''

    def open_moinpage_object(self, elem):
        # TODO
        return ''

    def open_moinpage_p(self, elem):
        ret = Moinwiki.p
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ret

    def close_moinpage_p(self, elem):
        return ''

    def open_moinpage_page(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ''

    def open_moinpage_part(self, elem):
        # TODO
        return ''

    def open_moinpage_separator(self, elem):
        return Moinwiki.separator

    def open_moinpage_span(self, elem):
        text_decoration = elem.get(moin_page.text_decoration, '')
        font_size = elem.get(moin_page.font_size, '')
        baseline_shift = elem.get(moin_page.baseline_shift, '')

        if text_decoration == 'line-through':
            self.children.append(iter(elem))
            self.opened.append(elem)
            return Moinwiki.stroke_open
        if text_decoration == 'underline':
            self.children.append(iter(elem))
            self.opened.append(elem)
            return Moinwiki.underline
        if font_size:
            self.children.append(iter(elem))
            self.opened.append(elem)
            return Moinwiki.larger_open if font_size == "120%" \
                                        else Moinwiki.smaller_open
        if baseline_shift == 'super':
            return '^%s^' % ''.join(elem.itertext())
        if baseline_shift == 'sub':
            return ',,%s,,' % ''.join(elem.itertext())
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ''

    def close_moinpage_span(self, elem):
        text_decoration = elem.get(moin_page.text_decoration, '')
        font_size = elem.get(moin_page.font_size, '')

        if text_decoration == 'line-through':
            return Moinwiki.stroke_close
        if text_decoration == 'underline':
            return Moinwiki.underline
        if font_size:
            return Moinwiki.larger_close if font_size == "120%" \
                                         else Moinwiki.smaller_close
        return ''

    def open_moinpage_strong(self, elem):
        ret = Moinwiki.strong
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ret

    def close_moinpage_strong(self, elem):
        return Moinwiki.strong

    def open_moinpage_table(self, elem):
        self.table_tableclass = elem.attrib.get('class', '')
        self.table_tablestyle = elem.attrib.get('style', '')
        self.table_rowsstyle = ''
        self.table_rowsclass = ''
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ''

    def close_moinpage_table(self, elem):
        return '\n'

    def open_moinpage_table_header(self, elem):
        # is this correct rowclass?
        self.table_rowsclass = 'table-header'
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ''

    def close_moinpage_table_header(self, elem):
        self.table_rowsclass = ''
        return ''

    def open_moinpage_table_footer(self, elem):
        self.table_rowsclass = 'table-footer'
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ''

    def close_moinpage_table_footer(self, elem):
        self.table_rowsclass = ''
        return ''

    def open_moinpage_table_body(self, elem):
        self.table_rowsclass = ''
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ''

    def close_moinpage_table_body(self, elem):
        return ''

    def open_moinpage_table_row(self, elem):
        self.table_rowclass = elem.attrib.get('class', '')
        self.table_rowclass = ' '.join(filter(None, [self.table_rowsclass, self.table_rowclass]))
        self.table_rowstyle = elem.attrib.get('style', '')
        self.table_rowstyle = ' '.join(filter(None, [self.table_rowsstyle, self.table_rowstyle]))
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ''

    def close_moinpage_table_row(self, elem):
        self.table_rowstyle = ''
        self.table_rowclass = ''
        return Moinwiki.table_marker + '\n'

    def open_moinpage_table_cell(self, elem):
        table_cellclass = elem.attrib.get('class', '')
        table_cellstyle = elem.attrib.get('style', '')
        number_columns_spanned = int(elem.get(moin_page.number_columns_spanned, 1))
        number_rows_spanned = elem.get(moin_page.number_rows_spanned, None)
        ret = Moinwiki.table_marker * number_columns_spanned

        attrib = []

        # TODO: maybe this can be written shorter
        if self.table_tableclass:
            attrib.append('tableclass="%s"' % self.table_tableclass)
            self.table_tableclass = ''
        if self.table_tablestyle:
            attrib.append('tablestyle="%s"' % self.table_tablestyle)
            self.table_tableclass = ''
        if self.table_rowclass:
            attrib.append('rowclass="%s"' % self.table_rowclass)
            self.table_rowclass = ''
        if self.table_rowstyle:
            attrib.append('rowclass="%s"' % self.table_rowstyle)
            self.table_rowstyle = ''
        if table_cellclass:
            attrib.append('class="%s"' % table_cellclass)
        if table_cellstyle:
            attrib.append('style="%s"' % table_cellstyle)
        if number_rows_spanned:
            attrib.append('|'+number_rows_spanned)

        attrib = ' '.join(attrib)

        if attrib:
            ret += '<%s>' % attrib

        self.children.append(iter(elem))
        self.opened.append(elem)
        return ret

    def close_moinpage_table_cell(self, elem):
        return ''

from . import default_registry
default_registry.register(Converter._factory)
