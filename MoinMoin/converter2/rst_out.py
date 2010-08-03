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

import re

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
    """
    An object of this class collects the structure of a table
    and represent it in ReStructuredText syntax.
    """

    def __init__(self):
        self.i = -1
        self.j = -1
        self.table = []
        self.header_count = 0
        self.rowclass = ''

    def add_row(self):
        """
        Add new row to the table.
        """
        if self.rowclass == 'table-header':
            self.header_count += 1
        row = []
        self.i += 1
        self.j = 0
        self.table.append(row)
        if self.i > 0:
            if len(self.table[-2]) > (self.j):
                self.add_cell(self.table[-2][self.j][0],
                                self.table[-2][self.j][1] - 1, Cell(''))
        return row

    def end_row(self):
        """
        Adds empyt cells to current row if it's too short.

        Moves the row to the head of the table if it is table header.
        """
        if len(self.table) > 1:
            if len(self.table[-2]) > len(self.table[-1]):
                self.add_cell(1, 1, Cell(''))
                self.end_row()
            if self.rowclass == 'table-header':
                self.table.insert(self.header_count - 1, self.table.pop())

    def add_cell(self, cs, rs, cell):
        """
        Adds cell to the row.

        @param cs: number of columns spanned
        """
        if cs < 1 or rs < 1:
            return
        self.table[-1].append((cs, rs, cell))
        for i in range(cs-1):
            self.table[-1].append((cs-i-1, rs, Cell('')))
        self.j += cs
        if self.i > 0:
            if len(self.table[-2]) > self.j:
                self.add_cell(self.table[-2][self.j][0],
                                self.table[-2][self.j][1] - 1, Cell(''))
        return

    def height(self):
        """
        @return: number of rows in the table
        """
        return len(self.table)

    def width(self):
        """
        @return: width of rows in the table or zero if rows have different width
        """
        if not self.table:
            return 0
        width = len(self.table[0])
        for row in self.table:
            if len(row) != width:
                return 0
        return width

    def col_width(self, col):
        """
        Counts the width of the column in ReSturcturedText representation.

        @param col: index of the column
        @return: number of characters
        """
        if self.width() <= col:
            return 0
        width = 0
        for row in self.table:
            if row[col][2].width() > width:
                width = row[col][2].width()
        return width

    def row_height(self, row):
        """
        Counts lines in ReSturcturedText representation of the row

        @param row: index of the row
        @return: number of lines
        """
        if self.height() <= row:
            return 0
        height = 0
        for col in self.table[row]:
            if col[2].height() > height:
                height = col[2].height()
        return height

    def __repr__(self):
        """
        Represent table using ReStructuredText syntax.
        """
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
            line = [u'+']
            row = self.table[0]
            for col in range(len(cols)):
                line.append(u'-'*cols[col])
                if self.table[0][col][0] > 1:
                    line.append(u'-')
                else:
                    line.append(u'+')
            ret.append(''.join(line))
            for row in range(len(rows)):
                for i in range(rows[row]):
                    line = []
                    line.append(u'|')
                    for col in range(len(cols)):
                        if self.table[row][col][2].height() <= i:
                            line.append(''.ljust(cols[col])[:cols[col]])
                        else:
                            line.append(
                                self.table[row][col][2]().split(
                                    u'\n')[i].ljust(cols[col])[:cols[col]])
                        if self.table[row][col][0] > 1:
                            line.append(' ')
                        else:
                            line.append(u'|')

                    ret.append(''.join(line))
                line = [u'+']
                for col in range(len(cols)):
                    if self.table[row][col][1] > 1:
                        line.append(' '*cols[col])
                    elif row == self.header_count - 1:
                        line.append(u'='*cols[col])
                    else:
                        line.append(u'-'*cols[col])
                    if self.table[row][col][0] > 1:
                        if row + 1 < len(rows)\
                                and self.table[row + 1][col][0] > 1\
                                or row + 1 >= len(rows):
                            line.append(u'-')
                        else:
                            line.append(u'+')
                    else:
                        line.append(u'+')
                ret.append(''.join(line))
        return u'\n'.join(ret)


class ReST(object):
    """
    ReST syntax elements
    It's dummy
    """
    h = u"""= - ` : ' " ~ ^ _ * + # < >""".split()
    a_separator = u'|'
    verbatim = u'::'
    monospace = u'``'
    strong = u"**"
    emphasis = u"*"
    p = u'\n'
    linebreak = u'\n\n'
    separator = u'----'
    list_type = {
        (u'definition', None): u'',
        (u'ordered', None): u'1.',
        (u'ordered', u'lower-alpha'): u'a.',
        (u'ordered', u'upper-alpha'): u'A.',
        (u'ordered', u'lower-roman'): u'i.',
        (u'ordered', u'upper-roman'): u'I.',
        (u'unordered', None): u'*',
        (None, None): u' ',
        }


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
        self.table_tableclass = u''
        self.table_tablestyle = u''
        self.table_rowsclass = u''
        self.table_rowsstyle = u''
        self.table_rowstyle = u''
        self.table_rowclass = u''

        self.list_item_labels = []
        self.list_item_label = u''
        self.list_level = -1

        # 'text' - default status - <p> = '/n' and </p> = '/n'
        # 'table' - text inside table - <p> = '<<BR>>' and </p> = ''
        # 'list' - text inside list -
        #       <p> if after </p> = '<<BR>>' and </p> = ''
        # status added because of
        #  differences in interpretation of <p> in different places
    def __call__(self, root):
        self.status = ['text', ]
        self.last_closed = None
        self.opened = [None, ]
        self.children = [None, iter([root])]
        self.output = []
        self.list_item_label = []
        self.subpage = [self.output]
        self.subpage_level = [0, ]
        self.footnotes = []
        self.objects = []
        self.all_used_references = []
        self.anonymous_reference = None
        self.used_references = []
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
                            self.output.append(u'\n\n')
                    elif self.status[-1] == "list":
                        next_child =\
                            re.sub(r"\n(.)", lambda m: u"\n%s%s" % (u' '*(len(u''.join(self.list_item_labels)) + len(self.list_item_labels)), m.group(1)), next_child)
                        if self.last_closed == "p":
                            self.output.append(u'\n'\
                                    + u' '\
                                    * (len(''.join(self.list_item_labels))\
                                       + len(self.list_item_labels)))
                    elif self.status[-1] == "text":
                        if self.last_closed == "p":
                            self.define_references()
                            self.output.append(u'\n')
                        #if self.last_closed == "list":
                        #    self.output.append('\n')
                    elif self.status[-2] == "list":
                        next_child =\
                            re.sub(r"\n(.)", lambda m: u"\n%s%s" % (u' '*(len(u''.join(self.list_item_labels)) + len(self.list_item_labels)), m.group(1)), next_child)
                    self.output.append(next_child)
                    self.last_closed = 'text'
            except StopIteration:
                self.children.pop()
                next_parent = self.opened.pop()
                if next_parent:
                    # close function can change self.output
                    close_ret = self.close(next_parent)
                    self.output.append(close_ret)
                    if self.status[-1] == "text":
                        if self.last_closed == "p":
                            self.define_references()
        self.define_references()
        notes = u"\n\n".join(u".. [#] %s" % note.replace(u"\n", u"\n  ") for note in self.footnotes)
        if notes:
            self.output.append(u"\n\n%s\n\n" % notes)

        return u''.join(self.output)

    def open(self, elem):
        uri = elem.tag.uri
        name = self.namespaces.get(uri, None)
        if name is not None:
            n = 'open_' + name
            f = getattr(self, n, None)
            if f is not None:
                return f(elem)
        return u''

    def open_moinpage(self, elem):
        n = 'open_moinpage_' + elem.tag.name.replace('-', '_')
        f = getattr(self, n, None)
        if f:
            return f(elem)
        self.children.append(iter(elem))
        self.opened.append(elem)
        return u''

    def close(self, elem):
        uri = elem.tag.uri
        name = self.namespaces.get(uri, None)
        if name is not None:
            n = 'close_' + name
            f = getattr(self, n, None)
            if f is not None:
                return f(elem)
        return u''

    def close_moinpage(self, elem):
        n = 'close_moinpage_' + elem.tag.name.replace('-', '_')
        f = getattr(self, n, None)
        if f:
            close = f(elem)
        self.last_closed = elem.tag.name.replace('-', '_')
        if f:
            return close
        return u''

    def open_moinpage_a(self, elem):
        href = elem.get(xlink.href, None)
        text = u''.join(elem.itertext()).replace(u'\n', u' ')
        # TODO: check that links have different alt texts
        if text in [t for (t, h) in self.all_used_references]:
            if (text, href) in self.all_used_references:
                return u"`%s`_" % text
            if not self.anonymous_reference:
                self.anonymous_reference = href
                self.used_references.insert(0, (u"_", href))
                return u"`%s`__" % text
            else:
                while text in [t for (t, h) in self.all_used_references]:
                    text = text + u"~"
        self.used_references.append((text, href))
        self.all_used_references.append((text, href))
        #self.objects.append("\n\n.. _%s: %s\n\n" % (text, href))
        return u"`%s`_" % text

    def close_moinpage_a(self, elem):
        # dummy, open_moinpage_a does all the job
        return u""

    def open_moinpage_blockcode(self, elem):
        text = u''.join(elem.itertext())
        max_subpage_lvl = 3
        text = text.replace(u'\n', u'\n  '\
                                  + u' ' * (len(u''.join(self.list_item_labels))\
                                         + len(self.list_item_labels)))
        if self.list_level >= 0:
            while self.output and re.match(r'(\n*)\Z', self.output[-1]):
                self.output.pop()
            last_newlines = r'(\n*)\Z'
            if self.output:
                i = -len(re.search(last_newlines, self.output[-1]).groups(1)[0])
                if i:
                    self.output[-1] = self.output[-1][:i]

        ret = u"::\n\n  %s%s\n\n" % (u' '\
                                    * (len(u''.join(self.list_item_labels))\
                                       + len(self.list_item_labels)), text)
        return ret

    def close_moinpage_blockcode(self, elem):
        # Dummy, open_moinpage_code is does all the job
        return u''

    def open_moinpage_code(self, elem):
        ret = u"%s%s%s" % (ReST.monospace,\
                          u''.join(elem.itertext()),\
                          ReST.monospace)
        return ret

    def close_moinpage_code(self, elem):
        # Dummy, open_moinpage_code is does all the job
        return u''

    def open_moinpage_emphasis(self, elem):
        ret = ReST.emphasis
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ret

    def close_moinpage_emphasis(self, elem):
        return ReST.emphasis

    def open_moinpage_h(self, elem):
        level = elem.get(moin_page.outline_level, 1)
        text = u''.join(elem.itertext())
        try:
            level = int(level)
        except ValueError:
            raise ElementException(u'page:outline-level needs to be an integer')
        if level < 1:
            level = 1
        elif level > 6:
            level = 6
        ret = u"\n\n%s\n%s\n%s\n\n" % (ReST.h[level]*len(text),\
                                      text,\
                                      ReST.h[level]*len(text))
        return ret

    def close_moinpage_h():
        # Dummy, open_moinpage_h does all the job
        return u''

    def open_moinpage_line_break(self, elem):
        if self.status[-1] == "list":
            return ReST.linebreak\
                   + u' '\
                     * (len(u''.join(self.list_item_labels))\
                        + len(self.list_item_labels))
        self.last_closed = 'line_break'
        return ReST.linebreak

    def close_moinpage_line_break(self, elem):
        return u''

    def open_moinpage_list(self, elem):
        label_type = (elem.get(moin_page.item_label_generate, None),
                        elem.get(moin_page.list_style_type, None))
        self.list_item_labels.append(
            ReST.list_type.get(label_type, u' '))
        self.children.append(iter(elem))
        self.opened.append(elem)
        self.list_level += 1
        ret = u''
        if self.status[-1] == 'text' and self.last_closed:
            ret = u'\n\n'
        elif self.status[-1] != 'text' or self.last_closed:
            ret = u'\n'
        self.status.append('list')
        self.last_closed = None
        return ret

    def close_moinpage_list(self, elem):
        self.list_item_labels.pop()
        self.list_level -= 1
        self.status.pop()
        if self.status[-1] == 'list':
            return u''
        return u'\n'

    def open_moinpage_list_item(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        self.list_item_label = self.list_item_labels[-1] + u' '
        return u''

    def close_moinpage_list_item(self, elem):
        return u''

    def open_moinpage_list_item_label(self, elem):
        ret = u''
        if self.list_item_labels[-1] == u'' or self.list_item_labels[-1] == u' ':
            self.children.append(iter(elem))
            self.opened.append(elem)
            self.list_item_labels[-1] = u' '
            self.list_item_label = self.list_item_labels[-1] + u' '
                # TODO: rewrite this using % formatting
            space_bonus = 0
            if len(u''.join(self.list_item_labels[:-1])): space_bonus = 1
            ret = u' '\
                  * (len(u''.join(self.list_item_labels[:-1]))\
                     + len(self.list_item_labels[:-1]))
            if self.last_closed and self.last_closed != 'list':
                ret = u'\n%s' % ret
            return ret
        return u''

    def close_moinpage_list_item_label(self, elem):
        return u''

    def open_moinpage_list_item_body(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        self.define_references()
        ret = u''
        if self.last_closed:
            ret = u'\n'
        space_bonus = 0
        ret += u' ' * (len(u''.join(self.list_item_labels[:-1]))\
                      + len(self.list_item_labels[:-1]))\
               + self.list_item_label
        if self.list_item_labels[-1] in [u'1.', u'i.', u'I.', u'a.', u'A.']:
            self.list_item_labels[-1] = u'#.'
        return ret

    def close_moinpage_list_item_body(self, elem):
        if self.last_closed == "text":
            return u'\n'
        return u""

    def open_moinpage_note(self, elem):
        class_ = elem.get(moin_page.note_class, u"")
        if class_:
            self.status.append('list')
            self.children.append(iter(elem))
            self.opened.append(elem)
            if class_ == u"footnote":
                self.output = []
                self.subpage.append(self.output)
                return u''
        return u""

    def close_moinpage_note(self, elem):
        self.status.pop()
        self.footnotes.append(u"".join(self.output))
        self.subpage.pop()
        self.output = self.subpage[-1]
        return u' [#]_ '

    def open_moinpage_object(self, elem):
        # TODO: object parametrs support
        href = elem.get(xlink.href, u'')
        href = href.split(u'?')
        args = u''
        if len(href) > 1:
            args =[s for s in re.findall(r'(?:^|;|,|&|)(\w+=\w+)(?:,|&|$)',
                                            href[1]) if s[:3] != u'do=']
        href = href[0]
        alt = elem.get(moin_page.alt, u'')
        if not alt:
            ret = u''
        else:
            ret = u'|%s|' % alt
        args_text = u''
        if args:
            args_text = u"\n  %s" % u'\n  '.join(u':%s: %s' % (arg.split(u'=')[0], arg.split(u'=')[1]) for arg in args)
        self.objects.append(u".. %s image:: %s%s" % (ret, href, args_text))
        return ret

    def open_moinpage_p(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        if self.status[-1] == 'text':
            self.status.append('p')
            self.define_references()
            if self.last_closed == 'text':
                return ReST.p * 2
            elif self.last_closed == 'p':
                return ReST.p
            elif self.last_closed:
                return ReST.p
        elif self.status[-1] == 'table':
            self.status.append('p')
            if self.last_closed and self.last_closed != 'table_cell'\
                                and self.last_closed != 'table_row'\
                                and self.last_closed != 'table_header'\
                                and self.last_closed != 'table_footer'\
                                and self.last_closed != 'table_body'\
                                and self.last_closed != 'line_break':
          #                      and self.last_closed != 'p':
                return ReST.linebreak
            elif self.last_closed == 'p' or self.last_closed == 'line_break':
                return u''
        elif self.status[-1] == 'list':
            self.status.append('p')
            if self.last_closed and self.last_closed == 'list_item_label':
                return u''
            if self.last_closed and self.last_closed != 'list_item'\
                                and self.last_closed != 'list_item_header'\
                                and self.last_closed != 'list_item_footer'\
                                and self.last_closed != 'p':
                return ReST.linebreak + u' '\
                                        * (len(u''.join(self.list_item_labels))\
                                           + len(self.list_item_labels))
            elif self.last_closed and self.last_closed == 'p':
                #return ReST.p +\
                return u"\n" + u' ' * (len(u''.join(self.list_item_labels))\
                                   + len(self.list_item_labels))
        return u''

    def close_moinpage_p(self, elem):
        self.status.pop()
        if self.status[-1] == 'text':
            return ReST.p
        if self.status[-1] == 'list':
            return u'\n'
        return u''

    def open_moinpage_page(self, elem):
        self.last_closed = None
        self.children.append(iter(elem))
        self.opened.append(elem)
        return u''

    def close_moinpage_page(self, elem):
        return u''

    def open_moinpage_body(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        return u''

    def close_moinpage_body(self, elem):
        return u''

    def open_moinpage_part(self, elem):
        type = elem.get(moin_page.content_type, u"").split(u';')
        if len(type) == 2:
            if type[0] == u"x-moin/macro":
                if len(elem) and iter(elem).next().tag.name == "arguments":
                    alt = u"<<%s(%s)>>"  % (type[1].split(u'=')[1],
                                    u','.join([u''.join(c.itertext())\
                                        for c in iter(elem).next()\
                                        if c.tag.name == "argument"]))
                else:
                    alt = u"<<%s()>>" % type[1].split(u'=')[1]

                obj = u".. |%s| macro:: %s" % (alt, alt)
                self.objects.append(obj)
                return u" |%s| " % alt
            elif type[0] == u"x-moin/format":
                elem_it = iter(elem)
                ret = u"\n\n.. parser:%s" % type[1].split(u'=')[1]
                if len(elem) and elem_it.next().tag.name == "arguments":
                    args = []
                    for arg in iter(elem).next():
                        if arg.tag.name == "argument":
                            args.append(u"%s=\"%s\""\
                                        % (arg.get(moin_page.name, u""),
                                           u' '.join(arg.itertext())))
                    ret = u'%s %s' % (ret, u' '.join(args))
                    elem = elem_it.next()
                ret = u"%s\n  %s" % (ret, u' '.join(elem.itertext()))
                return ret
        return elem.get(moin_page.alt, u'') + u"\n"

    def close_moinpage_part(self, elem):
        return u''

    def close_moinpage_inline_part(self, elem):
        return u''

    def open_moinpage_inline_part(self, elem):
        ret = self.open_moinpage_part(elem)
        return ret

    def open_moinpage_separator(self, elem):
        return u'\n\n' + ReST.separator + u'\n\n'

    def open_moinpage_span(self, elem):
        baseline_shift = elem.get(moin_page.baseline_shift, u'')

        # No text decoration and text size in rst, this can be deleted
        """
        text_decoration = elem.get(moin_page.text_decoration, u'')
        font_size = elem.get(moin_page.font_size, u'')
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
        """
        if baseline_shift == 'super':
            return u"\\ :sup:`%s`\\ " % u''.join(elem.itertext())
        if baseline_shift == 'sub':
            return u"\\ :sub:`%s`\\ " % u''.join(elem.itertext())
        self.children.append(iter(elem))
        self.opened.append(elem)
        return u''

    def close_moinpage_span(self, elem):
        return u''

    def open_moinpage_strong(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ReST.strong

    def close_moinpage_strong(self, elem):
        return ReST.strong

    def open_moinpage_table(self, elem):
        self.table_tableclass = elem.attrib.get('class', u'')
        self.table_tablestyle = elem.attrib.get('style', u'')
        self.table_rowsstyle = u''
        self.table_rowsclass = u''
        self.children.append(iter(elem))
        self.opened.append(elem)
        self.status.append('table')
        self.last_closed = None
        self.table = []
        self.tablec = Table()
        return u''

    def close_moinpage_table(self, elem):
        self.status.pop()
        table = repr(self.tablec)
        if self.status[-1] == "list":
            table =\
                re.sub(r"\n(.)", lambda m: u"\n%s%s" % (u' '*(len(u''.join(self.list_item_labels)) + len(self.list_item_labels)), m.group(1)), u"\n" + table)
            return table + ReST.p
        return table + ReST.linebreak

    def open_moinpage_table_header(self, elem):
        # is this correct rowclass?
        self.tablec.rowclass = 'table-header'
        self.children.append(iter(elem))
        self.opened.append(elem)
        return u''

    def close_moinpage_table_header(self, elem):
        return u''

    # No table footer support, TODO if needed
    """
    def open_moinpage_table_footer(self, elem):
        self.tablec.rowclass = 'table-footer'
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ''

    def close_moinpage_table_footer(self, elem):
        self.table_rowsclass = ''
        return ''
    """

    def open_moinpage_table_body(self, elem):
        self.tablec.rowclass = 'table-body'
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ''

    def close_moinpage_table_body(self, elem):
        return ''

    def open_moinpage_table_row(self, elem):
        self.table_rowclass = elem.attrib.get('class', u'')
        self.table_rowclass = u' '.join([s for s in [self.table_rowsclass,
                                                    self.table_rowclass] if s])
        self.table_rowstyle = elem.attrib.get('style', u'')
        self.table_rowstyle = u' '.join([s for s in [self.table_rowsstyle,
                                                    self.table_rowstyle] if s])
        self.children.append(iter(elem))
        self.opened.append(elem)
        self.table.append([])
        self.tablec.add_row()
        return u''

    def close_moinpage_table_row(self, elem):
        self.table_rowstyle = ''
        self.table_rowclass = ''
        self.tablec.end_row()
        return u''

    def open_moinpage_table_cell(self, elem):
        table_cellclass = elem.attrib.get('class', u'')
        table_cellstyle = elem.attrib.get('style', u'')
        number_cols_spanned\
                = int(elem.get(moin_page.number_cols_spanned, 1))
        number_rows_spanned\
                = int(elem.get(moin_page.number_rows_spanned, 1))

        attrib = []

        # TODO: styles and classes
        """
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
        """
        self.children.append(iter(elem))
        self.opened.append(elem)
        self.output = []
        self.subpage.append(self.output)
        self.table[-1].append((number_cols_spanned,
                                number_rows_spanned,
                                self.output))
        return u''

    def close_moinpage_table_cell(self, elem):
        self.subpage.pop()
        self.output = self.subpage[-1]
        cell = self.table[-1][-1]
        self.tablec.add_cell(cell[0], cell[1], Cell(u''.join(cell[2])))
        return u''

    def open_moinpage_table_of_content(self, elem):
        depth = elem.get(moin_page.outline_level, u"")
        ret = u"\n\n.. contents::"
        if depth:
            ret += u"\n   :depth: %s" % depth
        return ret + u"\n\n"

    def close_moinpage_table_of_content(self, elem):
        return u''

    def define_references(self):
        """
        Adds defenitions of founded links and objects to the converter output.
        """
        self.all_used_references.extend(self.used_references)
        definitions = [u" " * (len(u''.join(self.list_item_labels))\
                                    + len(self.list_item_labels))\
                                  + u".. _%s: %s"\
                                    % link for link in self.used_references]
        definitions.extend(u" " * (len(u''.join(self.list_item_labels))\
                                     + len(self.list_item_labels))\
                                  + link for link in self.objects)
        definition_block = u"\n\n".join(definitions)

        if definitions:
            if self.last_closed == 'list_item_label':
                self.output.append(u"\n%s\n\n" % definition_block)
            else:
                self.output.append(u"\n\n%s\n\n" % definition_block)

        self.used_references = []
        self.objects = []
        self.anonymous_reference = None
        return


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter.factory,
                          type_moin_document,
                          Type('x-moin/format;name=rst'))
