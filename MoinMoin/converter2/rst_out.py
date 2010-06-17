"""
MoinMoin - reStructuredText markup output converter

Converts an internal document tree into reStructuredText markup.

This is preprealpha version, do not use it, it doesn't work.

@copyright: 2008 MoinMoin:BastianBlank
            2010 MoinMoin:DmitryAndreev
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

from MoinMoin.util.tree import moin_page, xlink

from emeraldtree import ElementTree as ET

from re import findall

from MoinMoin.support.werkzeug.utils import unescape


class Cell(object):

    def __init__(self, text):
        self.text = text

    def __call__(self):
        return self.text

    def height(self):
        return len(self.text.split('\n'))

    def width(self):
        max = 0
        for i in self.text.split('\n'):
            if len(i) > max:
                max = len(i)
        return max


class Table(object):

    def __init__(self):
        self.i = -1
        self.j = -1
        self.table = []
        self.header_count = 0

    def add_header(self):
        self.header_count += 1
        return self.add_row()

    def add_row(self):
        row = []
        self.i += 1
        self.j = 0
        self.table.append(row)
        if self.i > 0:
            if len(self.table[-2]) > (self.j):
                self.add_cell(self.table[-2][self.j][0], self.table[-2][self.j][1] - 1, Cell(''))
        return row

    def add_cell(self, cs, rs, cell):
        if cs < 1 or rs < 1:
            return
        self.table[-1].append((cs, rs, cell))
        for i in range(cs-1):
            self.table[-1].append((cs-i-1, rs, Cell('')))
        self.j += cs
        if self.i > 0:
            if len(self.table[-2]) > self.j:
                self.add_cell(self.table[-2][self.j][0], self.table[-2][self.j][1] - 1, Cell(''))
        return

    def height(self):
        return len(self.table)

    def width(self):
        if not self.table:
            return 0
        width = len(self.table[0])
        for row in self.table:
            if len(row) != width:
                return 0
        return width

    def col_width(self, col):
        if self.width() <= col:
            return 0
        width = 0
        for row in self.table:
            if row[col][2].width() > width:
                width = row[col][2].width()
        return width

    def row_height(self, row):
        if self.height() <= row:
            return 0
        height = 0
        for col in self.table[row]:
            if col[2].height() > height:
                height = col[2].height()
        return height

    def complete_line(self):
        if self.i > 0:
            if len(table[-1]) < len(table[-2]):
                pass

    def __str__(self):
        ret = []
        if self.height() and self.width():
            cols = []
            rows = []
            row = self.table[0]
            for col in range(self.width()):
                cols.append(self.col_width(col))
            for row in range(self.height()):
                rows.append(self.row_height(row))
            ret = []
            line = ['+']
            row = self.table[0]
            for col in range(len(cols)):
                line.append('-'*cols[col])
                if self.table[0][col][0] > 1:
                    line.append('-')
                else:
                    line.append('+')
            ret.append(''.join(line))
            for row in range(len(rows)):
                for i in range(rows[row]):
                    line = []
                    line.append('|')
                    for col in range(len(cols)):
                        if self.table[row][col][2].height() <= i:
                            line.append(''.ljust(cols[col])[:cols[col]])
                        else:
                            line.append(self.table[row][col][2]().split('\n')[i].ljust(cols[col])[:cols[col]])
                        if self.table[row][col][0] > 1:
                            line.append(' ')
                        else:
                            line.append('|')

                    ret.append(''.join(line))
                line = ['+']
                for col in range(len(cols)):
                    if self.table[row][col][1] > 1:
                        line.append(' '*cols[col])
                    elif row == self.header_count - 1:
                        line.append('='*cols[col])
                    else:
                        line.append('-'*cols[col])
                    if self.table[row][col][0] > 1:
                        if row + 1 < len(rows) and self.table[row + 1][col][0] > 1 or row + 1 >= len(rows):
                            line.append('-')
                        else:
                            line.append('+')
                    else:
                        line.append('+')
                ret.append(''.join(line))
        return '\n'.join(ret)


class ReST(object):
    """
    ReST syntax elements
    It's dummy
    """
    h = """= - ` : ' " ~ ^ _ * + # < >""".split()
    a_separator = '|'
    verbatim = '::'
    monospace = '``'
    strong = "**"
    emphasis = "*"
    p = '\n'
    linebreak = '\n\n'
    separator = '----'
    list_type = {
        ('definition', None): '',
        ('ordered', None): '1.',
        ('ordered', 'lower-alpha'): 'a.',
        ('ordered', 'upper-alpha'): 'A.',
        ('ordered', 'lower-roman'): 'i.',
        ('ordered', 'upper-roman'): 'I.',
        ('unordered', None): '*',
# Next item is a hack, bug in moinwiki_in converter with ' def:: \n :: lis1\n :: list2' input
        (None, None): '',
        }

    def __init__(self):
        pass


class Converter(object):
    """
    Converter application/x.moin.document -> text/x.moin.rst
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
    def factory(cls, request, input, output, **kw):
        return cls

    def __init__(self):

        # TODO: create class containing all table attributes
        self.table_tableclass = ''
        self.table_tablestyle = ''
        self.table_rowsclass = ''
        self.table_rowsstyle = ''
        self.table_rowstyle = ''
        self.table_rowclass = ''

        self.list_item_labels = ['', ]
        self.list_item_label = ''
        self.list_level = -1

        # 'text' - default status - <p> = '/n' and </p> = '/n'
        # 'table' - text inside table - <p> = '<<BR>>' and </p> = ''
        # 'list' - text inside list - <p> if after </p> = '<<BR>>' and </p> = ''
        # status added because of differences in interpretation of <p> in different places
    def __call__(self, root):
        self.status = ['text', ]
        self.last_closed = None
        self.opened = [None, ]
        self.children = [None, iter([root])]
        self.output = []
        self.list_item_lable = []
        self.subpage = [self.output]
        self.subpage_level = [0, ]
        self.footnotes = []
        while self.children[-1]:
            try:
                next_child = self.children[-1].next()
                if isinstance(next_child, ET.Element):
                    # open function can change self.output
                    ret_open = self.open(next_child)
                    self.output.append(ret_open)
                else:
                    if self.status[-1] == "table":
                        if self.last_closed == "p":
                            self.output.append('\n\n')
                    elif self.status[-1] == "list":
                        if self.last_closed == "p":
                            self.output.append('\n' + ' ' * (self.list_level + 1))
                    elif self.status[-1] == "text":
                        if self.last_closed == "p":
                            self.output.append('\n')
                    self.output.append(next_child)
                    self.last_closed = 'text'
            except StopIteration:
                self.children.pop()
                next_parent = self.opened.pop()
                if next_parent:
                    # close function can change self.output
                    close_ret = self.close(next_parent)
                    self.output.append(close_ret)
        self.output.append("\n\n.. [#]".join(self.footnotes))
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
        self.last_closed = elem.tag.name.replace('-', '_')
        f = getattr(self, n, None)
        if f:
            return f(elem)
        return ''

    def open_moinpage_a(self, elem):
        href = elem.get(xlink.href, None)

        # This part doesn't work in moinwiki_in converter
        params = {}
        params['target'] = elem.get(xlink.target, None)
        params['class'] = elem.get(xlink.class_, None)
        params['title'] = elem.get(xlink.title, None)
        params['accesskey'] = elem.get(xlink.accesskey, None)
        params = ','.join(['%s=%s' % (p, params[p]) for p in params if params[p]])

        # TODO: rewrite this using % formatting
        text = ''.join(elem.itertext())
        return "`%s <%s>`_" % (text, href)

    def close_moinpage_a(self, elem):
        # dummy, open_moinpage_a does all the job
        return ""

    def open_moinpage_blockcode(self, elem):
        text = ''.join(elem.itertext())
        max_subpage_lvl = 3
        text = text.replace('\n', '\n  ')
        ret = "::\n\n  %s\n\n" % text
        return ret

    def close_moinpage_blockcode(self, elem):
        # Dummy, open_moinpage_code is does all the job
        return ''

    def open_moinpage_code(self, elem):
        ret = "%s%s%s" % (ReST.monospace, ''.join(elem.itertext()), ReST.monospace)
        return ret

    def close_moinpage_code(self, elem):
        # Dummy, open_moinpage_code is does all the job
        return ''

    def open_moinpage_emphasis(self, elem):
        ret = ReST.emphasis
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ret

    def close_moinpage_emphasis(self, elem):
        return ReST.emphasis

    def open_moinpage_h(self, elem):
        level = elem.get(moin_page.outline_level, 1)
        text = ''.join(elem.itertext())
        try:
            level = int(level)
        except ValueError:
            raise ElementException('page:outline-level needs to be an integer')
        if level < 1:
            level = 1
        elif level > 6:
            level = 6
        ret = "%s\n%s\n%s\n\n" % (ReST.h[level]*len(text), text, ReST.h[level]*len(text))
        return ret

    def close_moinpage_h():
        # Dummy, open_moinpage_h does all the job
        return ''

    def open_moinpage_line_break(self, elem):
        if self.status[-1] == "list":
            return ReST.linebreak + ' ' * (self.list_level + 1)
        return ReST.linebreak

    def open_moinpage_list(self, elem):
        label_type = (elem.get(moin_page.item_label_generate, None),
                        elem.get(moin_page.list_style_type, None))
        self.list_item_labels.append(
            ReST.list_type.get(label_type, ''))
        self.children.append(iter(elem))
        self.opened.append(elem)
        self.list_level += 1
        ret = ''
        if self.status[-1] != 'text' or self.last_closed:
            ret = '\n'
        self.status.append('list')
        self.last_closed = None
        return ret

    def close_moinpage_list(self, elem):
        self.list_item_labels.pop()
        self.list_level -= 1
        self.status.pop()
        if self.status[-1] == 'list':
            return ''
        return '\n'

    def open_moinpage_list_item(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        self.list_item_label = self.list_item_labels[-1] + ' '
        return ''

    def close_moinpage_list_item(self, elem):
        return ''

    def open_moinpage_list_item_label(self, elem):
        ret = ''
        if self.list_item_labels[-1] == '':
            label = ''.join(elem.itertext())
            if label:
                self.list_item_labels[-1] = ' '
                self.list_item_label = self.list_item_labels[-1] + ' '
                # TODO: rewrite this using % formatting
                ret = ' ' * self.list_level + label
                if self.last_closed:
                    ret = '\n%s' % ret
                else:
                    ret = '%s\n' % ret
                return ret
        return ''

    def close_moinpage_list_item_label(self, elem):
        return ''

    def open_moinpage_list_item_body(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        ret = ''
        if self.last_closed:
            ret = '\n'
        ret += ' ' * self.list_level + self.list_item_label
        if self.list_item_labels[-1] in ['1.', 'i.', 'I.', 'a.', 'A.']:
            self.list_item_labels[-1] = '#.'
        return ret

    def close_moinpage_list_item_body(self, elem):
        return ''

    def open_moinpage_note(self, elem):
        class_ = elem.get(moin_page.note_class, "")
        if class_:
            self.status.append('list')
            self.children.append(iter(elem))
            self.opened.append(elem)
            if class_ == "footnote":
                self.output = []
                self.subpage.append(self.output)
                return '[#]_'
        return ""

    def close_moinpage_note(self, elem):
        self.status.pop()
        self.footnotes.append("".join(self.output))
        self.subpage.pop()
        self.output = self.subpage[-1]
        return ''

    def open_moinpage_object(self, elem):
        # TODO: this can be done with one regex:
        return ''

    def open_moinpage_p(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        self.status.append("p")
        if self.status[-2] == 'text':
            if self.last_closed == 'text':
                return ReST.p * 2
            elif self.last_closed == 'p':
                return ReST.p
            elif self.last_closed:
                return ReST.p
        elif self.status[-2] == 'table':
            if self.last_closed and self.last_closed != 'table_cell'\
                                and self.last_closed != 'table_row':
                return ReST.linebreak
        elif self.status[-2] == 'list':
            if self.last_closed and self.last_closed != 'list_item'\
                                and self.last_closed != 'list_item_header'\
                                and self.last_closed != 'list_item_footer'\
                                and self.last_closed != 'p':
                return ReST.linebreak + ' '* (self.list_level + 1)
            elif self.last_closed and self.last_closed == 'p':
                return ReST.p + ' '* (self.list_level + 1)
        return ''

    def close_moinpage_p(self, elem):
        self.status.pop()
        if self.status[-1] == 'text':
            return ReST.p
        if self.status[-1] == 'list':
            return '\n'
        return ''

    def open_moinpage_page(self, elem):
        self.last_closed = None
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ''

    def close_moinpage_page(self, elem):
        return ''

    def open_moinpage_body(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ''

    def close_moinpage_body(self, elem):
        return ''

    def open_moinpage_part(self, elem):
        type = elem.get(moin_page.content_type, "").split(';')
        if len(type) == 2:
            if type[0] == "x-moin/macro":
                if len(elem) and iter(elem).next().tag.name == "arguments":
                    return "\n.. macro:: <<%s(%s)>>\n" % (type[1].split('=')[1], ','.join([''.join(c.itertext()) for c in iter(elem).next() if c.tag.name == "argument"]))
                else:
                    return "\n.. macro:: <<%s()>>\n" % type[1].split('=')[1]
            elif type[0] == "x-moin/format":
                elem_it = iter(elem)
                ret = "{{{#!%s" % type[1].split('=')[1]
                if len(elem) and elem_it.next().tag.name == "arguments":
                    args = []
                    for arg in iter(elem).next():
                        if arg.tag.name == "argument":
                            args.append("%s=\"%s\"" % (arg.get(moin_page.name, ""), ' '.join(arg.itertext())))
                    ret = '%s(%s)' % (ret, ' '.join(args))
                    elem = elem_it.next()
                ret = "%s\n%s\n}}}\n" % (ret, ' '.join(elem.itertext()))
                return ""
        return unescape(elem.get(moin_page.alt, '')) + "\n"

        return ''

    def close_moinpage_part(self, elem):
        return ''

    def close_moinpage_inline_part(self, elem):
        return ''

    def open_moinpage_inline_part(self, elem):
        # TODO: No inline macro in rst?
        ret = self.open_moinpage_part(elem)
        return ret

    def open_moinpage_separator(self, elem):
        return '\n\n' + ReST.separator + '\n\n'

    def open_moinpage_span(self, elem):
        text_decoration = elem.get(moin_page.text_decoration, '')
        font_size = elem.get(moin_page.font_size, '')
        baseline_shift = elem.get(moin_page.baseline_shift, '')

        if text_decoration == 'line-through':
            self.children.append(iter(elem))
            self.opened.append(elem)
            return ''
        if text_decoration == 'underline':
            self.children.append(iter(elem))
            self.opened.append(elem)
            return ''
        if font_size:
            self.children.append(iter(elem))
            self.opened.append(elem)
            return ''
        if baseline_shift == 'super':
            return ''.join(elem.itertext())
        if baseline_shift == 'sub':
            return ''.join(elem.itertext())
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ''

    def close_moinpage_span(self, elem):
        text_decoration = elem.get(moin_page.text_decoration, '')
        font_size = elem.get(moin_page.font_size, '')
        return ''

    def open_moinpage_strong(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ReST.strong

    def close_moinpage_strong(self, elem):
        return ReST.strong

    def open_moinpage_table(self, elem):
        self.table_tableclass = elem.attrib.get('class', '')
        self.table_tablestyle = elem.attrib.get('style', '')
        self.table_rowsstyle = ''
        self.table_rowsclass = ''
        self.children.append(iter(elem))
        self.opened.append(elem)
        self.status.append('table')
        self.last_closed = None
        self.table = []
        self.tablec = Table()
        return ''

    def close_moinpage_table(self, elem):
        self.status.pop()
        return str(self.tablec) + ReST.linebreak

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
        self.table_rowclass = ' '.join([s for s in [self.table_rowsclass, self.table_rowclass] if s])
        self.table_rowstyle = elem.attrib.get('style', '')
        self.table_rowstyle = ' '.join([s for s in [self.table_rowsstyle, self.table_rowstyle] if s])
        self.children.append(iter(elem))
        self.opened.append(elem)
        self.table.append([])
        self.tablec.add_row()
        return ''

    def close_moinpage_table_row(self, elem):
        self.table_rowstyle = ''
        self.table_rowclass = ''

        return ''

    def open_moinpage_table_cell(self, elem):
        table_cellclass = elem.attrib.get('class', '')
        table_cellstyle = elem.attrib.get('style', '')
        number_columns_spanned = int(elem.get(moin_page.number_columns_spanned, 1))
        number_rows_spanned = int(elem.get(moin_page.number_rows_spanned, 1))

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
            attrib.append('|'+str(number_rows_spanned))

        attrib = ' '.join(attrib)

        self.children.append(iter(elem))
        self.opened.append(elem)
        self.output = []
        self.subpage.append(self.output)
        self.table[-1].append((number_columns_spanned, number_rows_spanned, self.output))
        return ''

    def close_moinpage_table_cell(self, elem):
        self.subpage.pop()
        self.output = self.subpage[-1]
        cell = self.table[-1][-1]
        self.tablec.add_cell(cell[0], cell[1], Cell(''.join(cell[2])))
        return ''

    def open_moinpage_table_of_content(self, elem):
        depth = elem.get(moin_page.outline_level, "")
        ret = "\n.. contents::"
        if depth:
            ret += " :depth: %s" % depth
        return ret + "\n\n"

    def close_moinpage_table_of_content(self, elem):
        return ''

from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter.factory, type_moin_document, Type('x-moin/format;name=rst'))
