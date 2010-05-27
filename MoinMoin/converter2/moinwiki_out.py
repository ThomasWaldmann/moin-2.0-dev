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


class Moinwiki(object):
    '''
    Moinwiki syntax elements
    It's dummy
    '''
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

        self.list_item_labels = []
        self.list_level = 1

        self.request = request

    def __call__(self, root):
        self.opened = [None, ]
        self.children = [None, [root]]
        self.output = []
        self.list_item_lable = []

        while children[-1]:
            if children[-1]:
                next_child = children[-1].pop(0)
                if isinstance(next_child, ET.Element):
                    self.output.append(self.open(next_child))
                else:
                    # if text
                    self.output.append(next_child)
            else:
                next_parent = opened.pop()
                self.output.append(self.close(next_parent))

        return ''.join(output)

    def open(self, elem):
        uri = elem.tag.uri
        name = self.namespaces_visit.get(uri, None)
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
        if elem.children:
            self.children.append(list(elem.children))
            self.opened.append(elem)
        return ''

    def close(self, elem):
        uri = elem.tag.uri
        name = self.namespaces_visit.get(uri, None)
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
        if elem.children:
            self.children.append(list(elem.children))
            self.opened.append(elem)
        return ''

    def open_moinpage_a(self, elem):
        ret = a_open
        ret += elem.get(xlink.href, None)
        if elem.children:
            ret += Moinwiki.a_middle
            ret += ''.join(elem.itertext())
        else:
            href += self.close_moinpage_a(elem)
        return ret + a.close

    def close_moinpage_a(self, elem):
        # dummy, open_moinpage_a does all the job
        return ''

    def open_moinpage_blockcode(self, elem):
        ret = Moinwiki.verbatim_open
        ret += ''.join(elem.itertext())
        ret += Moinwiki.verbatim_open
        return ret

    def close_moinpage_blockcode(self, elem):
        return Moinwiki.verbatim_close

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
        if elem.children:
            self.children.append(list(elem.children))
            self.opened_nodes.append(elem)
        else:
            ret += self.close_moinpage_emphasis(elem)
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
        ret = Moinwiki.h * level
        ret += ''.join(elem.itertext())
        ret += Moinwiki.h * level
        return ret

    def close_moinpage_h():
        # Dummy, open_moinpage_h does all the job
        return ''

    def open_moinpage_line_break(self, elem):
        return Moinwiki.linebreak

    # TODO: create separate class for conversion of tables
    def open_moinpage_list(self, elem):
        if elem.children:
            label_type = (elem.get(moin_page.item_label_generate, None), \
                            elem.get(moin_page.list_style_type, None))
            self.list_item_labels.append(Moinwiki.list_label_type.get(label_type, ''))
            self.children.append(list(elem.children))
            self.opened.append(elem)
            self.list_level += 1
        return ''

    def close__moinpage_list(self, elem):
        self.list_item_labels.pop()
        self.list_level -= 1
        return ''

    def open_moinpage_list_item(self, elem):
        if elem.children:
            self.children.append(list(elem.children))
            self.opened.append(elem)
        return ' ' * self.list_level + self.list_item_labels[-1]

    def close_moinpage_list_item(self, elem):
        return ''

    def open_moinpage_list_label(self, elem):
        if elem.children:
            self.children.append(list(elem.children))
            self.opened.append(elem)
        return ''

    def close_moinpage_list_label(self, elem):
        return ''

    def open_moinpage_list_item_body(self, elem):
        if elem.children:
            self.children.append(list(elem.children))
            self.opened.append(elem)
        return ''

    def close_moinpage_list_item_body(self, elem):
        return ''

    def open_moinpage_object(self, elem):
        # TODO
        return ''

    def open_moinpage_p(self, elem):
        ret = moinpage_list_Moinwiki.p
        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        else:
            ret += close_moinpage_p(elem)
        return ret

    def close_moinpage_p(self, elem):
        return Moinwiki.p

    def open_moinpage_page(self, elem):
        # TODO
        return ''

    def open_moinpage_part(self, elem):
        # TODO
        return ''

    def open_moinpage_separator(self, elem):
        return Moinwiki.separator

    def open_moinpage_span(self, elem):
        # TODO
        return ''

    def open_moinpage_strong(self, elem):
        ret = Moinwiki.strong
        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        else:
            ret += close_moinpage_h(elem)
        return ret

    def close_moinpage_strong(self, elem):
        return Moinwiki.strong

    # TODO: create separate class for conversion of tables
    def open_moinpage_table(self, elem):
        self.table_tableclass = elem.attrib.get('class', '')
        self.table_tablestyle = elem.attrib.get('style', '')
        self.table_rowsstyle = ''
        self.table_rowsclass = ''
        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        return ''

    def close_moinpage_table(self, elem):
        return '\n'

    def open_moinpage_table_header(self, elem):
        # is this correct rowclass?
        self.table_rowsclass = 'table-header'
        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        return ''

    def close_moinpage_table_header(self, elem):
        self.table_rowsclass = ''
        return ''

    def open_moinpage_table_footer(self, elem):
        self.table_rowsclass = 'table-footer'
        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        return ''

    def close_moinpage_table_footer(self, elem):
        self.table_rowsclass = ''
        return ''

    def open_moinpage_table_body(self, elem):
        self.table_rowsclass = ''
        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        return ''

    def close_moinpage_table_body(self, elem):
        return ''

    def open_moinpage_table_row(self, elem):
        self.table_rowclass = elem.attrib.get('class', '')
        self.table_rowclass = ' '.join(filter([self.table_rowsclass, table_rowclass]))
        self.table_rowstyle = elem.attrib.get('style', '')
        self.table_rowstyle = ' '.join(filter([self.table_rowsstyle, table_rowstyle]))
        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        return ''

    def close_moinpage_table_row(self, elem):
        self.table_rowstyle = ''
        self.table_rowclass = ''
        return Moinwiki.table_marker + '\n'

    def open_moinpage_table_cell(self, elem):
        table_cellclass = elem.attrib.get('class', '')
        table_cellstyle = elem.attrib.get('style', '')
        number_columns_spanned = elem.get(moin_page.number_columns_spanned, 1)
        number_rows_spanned = elem.get(moin_page.number_rows_spanned, None)
        ret = Moinwiki.table_marker * number_columns_spanned

        attrib = []

        # TODO: maybe this can be written shorter
        if self.table_tableclass:
            attrib.append('tableclass="'+self.table_tableclass+'"')
            self.table_tableclass = ''
        if self.table_tablestyle:
            attrib.append('tablestyle="'+self.table_tablestyle+'"')
            self.table_tableclass = ''
        if self.table_rowclass:
            attrib.append('rowclass="'+self.table_rowclass+'"')
            self.table_rowclass = ''
        if self.table_rowstyle:
            attrib.append('rowclass="'+self.table_rowstyle+'"')
            self.table_rowstyle = ''
        if table_cellclass:
            attrib.append('class="'+table_cellclass+'"')
        if table_cellstyle:
            attrib.append('style="'+table_cellstyle+'"')
        if number_rows_spanned:
            attrib.append('|'+number_rows_spanned)

        attrib = ' '.join(attrib)

        if attrib:
            ret += '<' + attrib + '>'

        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        return ret

    def close_moinpage_table_cell(self, elem):
        return ''

from . import default_registry
default_registry.register(Converter._factory)
