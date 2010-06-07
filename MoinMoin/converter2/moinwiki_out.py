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

from re import findall

from MoinMoin.support.werkzeug.utils import unescape

class Moinwiki(object):
    '''
    Moinwiki syntax elements
    It's dummy
    '''
    h = '='
    a_open = '[['
    a_separator = '|'
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
    p = '\n'
    linebreak = '<<BR>>'
    larger_open = '~+'
    larger_close = '+~'
    smaller_open = '~-'
    smaller_close = '-~'
    object_open = '{{'
    object_close = '}}'
    definition_list_marker = '::'
    separator = '----'
    # TODO: definition list
    list_type = {
        ('definition', None): '',
        ('ordered', None): '1.',
        ('ordered', 'lower-alpha'): 'a.',
        ('ordered', 'upper-alpha'): 'A.',
        ('ordered', 'lower-roman'): 'i.',
        ('ordered', 'upper-roman'): 'I.',
        ('unordered', None): '*',
# Next item is a hack, bug in moinwiki_in converter with ' def:: \n :: lis1\n :: list2' input
        (None, None): '::',
        }

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
        while self.children[-1]:
            try:
                next_child = self.children[-1].next()
                if isinstance(next_child, ET.Element):
                    self.output.append(self.open(next_child))
                else:
                    self.output.append(next_child)
                    self.last_closed = 'text'
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

        # TODO: this can be done using one regex, can it?
        href = href.split('?')
        args = ''
        if len(href) > 1:
            # With normal
            print href
            args = ','.join(['&'+s for s in findall(r'(?:^|;|,|&|)(\w+=\w+)(?:,|&|$|)', href[1])])
        href = href[0].split('wiki.local:')[-1]
        print args
        args = ','.join(s for s in [args, params] if s)

        # TODO: rewrite this using % formatting
        ret = Moinwiki.a_open
        ret += href
        text = ''.join(elem.itertext())
        if not args and text == href:
            text = ''
        if text:
            ret += Moinwiki.a_separator + text
        if args:
            ret += Moinwiki.a_separator + args
        return ret + Moinwiki.a_close

    def close_moinpage_a(self, elem):
        # dummy, open_moinpage_a does all the job
        return Moinwiki.a_close

    def open_moinpage_blockcode(self, elem):
        ret = '%s\n%s\n%s\n' % (Moinwiki.verbatim_open, ''.join(elem.itertext()), Moinwiki.verbatim_close)
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
        ret += ' %s\n' % (Moinwiki.h * level)
        return ret

    def close_moinpage_h():
        # Dummy, open_moinpage_h does all the job
        return ''

    def open_moinpage_line_break(self, elem):
        return Moinwiki.linebreak

    def open_moinpage_list(self, elem):
        label_type = (elem.get(moin_page.item_label_generate, None),
                        elem.get(moin_page.list_style_type, None))
        self.list_item_labels.append(
            Moinwiki.list_type.get(label_type, ''))
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
        if self.list_item_labels[-1] == '' or self.list_item_labels[-1] == Moinwiki.definition_list_marker:
            label = ''.join(elem.itertext())
            if label:
                self.list_item_labels[-1] = Moinwiki.definition_list_marker
                self.list_item_label = self.list_item_labels[-1] + ' '
                # TODO: rewrite this using % formatting
                ret = ' ' * self.list_level + label + Moinwiki.definition_list_marker
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
        return ret

    def close_moinpage_list_item_body(self, elem):
        return ''

    def open_moinpage_object(self, elem):
        # TODO: this can be done with one regex:
        href = elem.get(xlink.href, '')
        href = href.split('?')
        args = ''
        if len(href) > 1:
            args =' '.join([s for s in findall(r'(?:^|;|,|&|)(\w+=\w+)(?:,|&|$)', href[1]) if s[:3] != 'do='])
        href = href[0].split('wiki.local:')[-1]
        # TODO: add '|' to Moinwiki class and rewrite this using % formatting
        ret = Moinwiki.object_open
        ret += href
        alt = elem.get(moin_page.alt, '')
        if alt and alt != href:
            ret += '|' + alt
            if args:
                ret += '|' + args
        ret += Moinwiki.object_close
        return ret

    def open_moinpage_p(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        if self.status[-1] == 'text':
            if self.last_closed == 'text':
                return Moinwiki.p * 2
            elif self.last_closed == 'p':
                return Moinwiki.p
            elif self.last_closed:
                return Moinwiki.p
        elif self.status[-1] == 'table':
            if self.last_closed and self.last_closed != 'table_cell':
                return Moinwiki.linebreak
        elif self.status[-1] == 'list':
            if self.last_closed and self.last_closed != 'list_item'\
                                and self.last_closed != 'list_item_header'\
                                and self.last_closed != 'list_item_footer':
                return Moinwiki.linebreak
        return ''

    def close_moinpage_p(self, elem):
        if self.status[-1] == 'text':
                return Moinwiki.p
        return ''

    def open_moinpage_page(self, elem):
        self.last_closed = None
        self.children.append(iter(elem))
        self.opened.append(elem)
        ret = ''
        print self.status
        if len(self.status) > 1:
            ret = "{{{#!"
            # ret += parser
            # but we do not have the required attribute
        self.status.append('text')
        return ret

    def close_moinpage_page(self, elem):
        self.status.pop()
        ret = ''
        if len(self.status) > 1:
            ret = "}}}\n"
        return ret

    def open_moinpage_body(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        class_ = elem.get(moin_page.class_,'').replace(' ', '/')
        if class_:
            return ' %s\n' % class_
        if len(self.status) > 2:
            return '\n'
        return ''
        
    def close_moinpage_body(self, elem):
        return ''
 
    def open_moinpage_part(self, elem):
        ret = unescape(elem.get(moin_page.alt, ''))
        return ret

    def close_moinpage_part(self, elem):
        return ''

    def open_moinpage_separator(self, elem):
        return Moinwiki.separator + '\n'

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
        self.status.append('table')
        self.last_closed = None
        return ''

    def close_moinpage_table(self, elem):
        self.status.pop()
        return ''

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
