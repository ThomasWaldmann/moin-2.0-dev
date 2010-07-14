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
    h = u'='
    a_open = u'[['
    a_separator = u'|'
    a_close = u']]'
    verbatim_open = u'{' # * 3
    verbatim_close = u'}'# * 3
    monospace = u'`'
    strong = u"'''"
    emphasis = u"''"
    underline = u'__'
    stroke_open = u'--('
    stroke_close = u')--'
    table_marker = u'||'
    p = u'\n'
    linebreak = u'<<BR>>'
    larger_open = u'~+'
    larger_close = u'+~'
    smaller_open = u'~-'
    smaller_close = u'-~'
    object_open = u'{{'
    object_close = u'}}'
    definition_list_marker = u'::'
    separator = u'----'
    # TODO: definition list
    list_type = {
        (u'definition', None): u'',
        (u'ordered', None): u'1.',
        (u'ordered', u'lower-alpha'): u'a.',
        (u'ordered', u'upper-alpha'): u'A.',
        (u'ordered', u'lower-roman'): u'i.',
        (u'ordered', u'upper-roman'): u'I.',
        (u'unordered', None): u'*',
        (None, None): u'::',
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

        self.list_item_labels = [u'', ]
        self.list_item_label = u''
        self.list_level = 0

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
        self.list_item_label = []
        self.subpage = [self.output]
        self.subpage_level = [0, ]
        while self.children[-1]:
            try:
                next_child = self.children[-1].next()
                if isinstance(next_child, ET.Element):
                    # open function can change self.output
                    ret_open = self.open(next_child)
                    self.output.append(ret_open)
                else:
                    if self.status[-1] == "table" or self.status[-1] == "list":
                        if self.last_closed == "p":
                            self.output.append(u'<<BR>>')
                    elif self.status[-1] == "text":
                        if self.last_closed == "p":
                            self.output.append(u'\n')
                    self.output.append(next_child)
                    self.last_closed = 'text'
            except StopIteration:
                self.children.pop()
                next_parent = self.opened.pop()
                if next_parent:
                    # close function can change self.output
                    close_ret = self.close(next_parent)
                    self.output.append(close_ret)

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
        self.last_closed = elem.tag.name.replace('-', '_')
        f = getattr(self, n, None)
        if f:
            return f(elem)
        return u''

    def open_moinpage_a(self, elem):
        href = elem.get(xlink.href, None)

        # This part doesn't work in moinwiki_in converter
        params = {}
        params['target'] = elem.get(xlink.target, None)
        params['class'] = elem.get(xlink.class_, None)
        params['title'] = elem.get(xlink.title, None)
        params['accesskey'] = elem.get(xlink.accesskey, None)
        params = u','.join([u'%s=%s' % (p, params[p]) for p in params if params[p]])

        # TODO: this can be done using one regex, can it?
        href = href.split(u'?')
        args = u''
        if len(href) > 1:
            # With normal
            args = u','.join([u'&'+s for s in findall(r'(?:^|;|,|&|)(\w+=\w+)(?:,|&|$|)', href[1])])
        href = href[0].split(u'wiki.local:')[-1]
        args = u','.join(s for s in [args, params] if s)

        # TODO: rewrite this using % formatting
        ret = Moinwiki.a_open
        ret += href
        text = u''.join(elem.itertext())
        if not args and text == href:
            text = u''
        if text:
            ret += Moinwiki.a_separator + text
        if args:
            ret += Moinwiki.a_separator + args
        return ret + Moinwiki.a_close

    def close_moinpage_a(self, elem):
        # dummy, open_moinpage_a does all the job
        return Moinwiki.a_close

    def open_moinpage_blockcode(self, elem):
        text = u''.join(elem.itertext())
        max_subpage_lvl = 3
        for s in findall(r'}+', text):
            if max_subpage_lvl <= len(s):
                max_subpage_lvl = len(s) + 1
        if max_subpage_lvl >= self.subpage_level[-1]:
            self.subpage_level[-1] = max_subpage_lvl + 1
        ret = u'%s\n%s\n%s\n' % (Moinwiki.verbatim_open * max_subpage_lvl, text, Moinwiki.verbatim_close * max_subpage_lvl)
        return ret

    def close_moinpage_blockcode(self, elem):
        # Dummy, open_moinpage_code is does all the job
        return u''

    def open_moinpage_code(self, elem):
        ret = Moinwiki.monospace
        ret += u''.join(elem.itertext())
        ret += Moinwiki.monospace
        return ret

    def close_moinpage_code(self, elem):
        # Dummy, open_moinpage_code is does all the job
        return u''

    def open_moinpage_div(self, elem):
        return u''

    def close_moinpage_div(self, elem):
        return u''

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
        ret = Moinwiki.h * level + u' '
        ret += u''.join(elem.itertext())
        ret += u' %s\n' % (Moinwiki.h * level)
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
            Moinwiki.list_type.get(label_type, u''))
        self.children.append(iter(elem))
        self.opened.append(elem)
        self.list_level += 1
        ret = u''
        if self.status[-1] != 'text' or self.last_closed:
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
        if self.list_item_labels[-1] == u'' or self.list_item_labels[-1] == Moinwiki.definition_list_marker:
            self.list_item_labels[-1] = Moinwiki.definition_list_marker
            self.list_item_label = self.list_item_labels[-1] + u' '
            self.children.append(iter(elem))
            self.opened.append(elem)
            # TODO: rewrite this using % formatting
            # TODO: delete self.list_level from everywhere
            ret = u' ' * (len(u''.join(self.list_item_labels[:-1])) + len(self.list_item_labels[:-1]))# self.list_level
            if self.last_closed:
                ret = u'\n%s' % ret
            return ret
        return u''

    def close_moinpage_list_item_label(self, elem):
        return Moinwiki.definition_list_marker

    def open_moinpage_list_item_body(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        ret = u''
        if self.last_closed:
            ret = u'\n'
        ret += u' ' * (len(u''.join(self.list_item_labels[:-1])) + len(self.list_item_labels[:-1])) + self.list_item_label
        return ret

    def close_moinpage_list_item_body(self, elem):
        return u''

    def open_moinpage_note(self, elem):
        class_ = elem.get(moin_page.note_class, u"")
        if class_:
            self.status.append('table')
            self.children.append(iter(elem))
            self.opened.append(elem)
            if class_ == "footnote":
                return u'<<FootNote('
        return u""

    def close_moinpage_note(self, elem):
        self.status.pop()
        return u')>>'

    def open_moinpage_object(self, elem):
        # TODO: this can be done with one regex:
        href = elem.get(xlink.href, u'')
        href = href.split(u'?')
        args = u''
        if len(href) > 1:
            args =u' '.join([s for s in findall(r'(?:^|;|,|&|)(\w+=\w+)(?:,|&|$)', href[1]) if s[:3] != u'do='])
        href = href[0].split(u'wiki.local:')[-1]
        # TODO: add '|' to Moinwiki class and rewrite this using % formatting
        ret = Moinwiki.object_open
        ret += href
        alt = elem.get(moin_page.alt, u'')
        if alt and alt != href:
            ret += u'|' + alt
            if args:
                ret += u'|' + args
        ret += Moinwiki.object_close
        return ret

    def open_moinpage_p(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        self.status.append("p")
        if self.status[-2] == 'text':
            if self.last_closed == 'text':
                return Moinwiki.p * 2
            elif self.last_closed == 'p':
                return Moinwiki.p
            elif self.last_closed:
                return Moinwiki.p
        elif self.status[-2] == 'table':
            if self.last_closed and self.last_closed != 'table_cell'\
                                and self.last_closed != 'table_row':
                return Moinwiki.linebreak
        elif self.status[-2] == 'list':
            if self.last_closed and self.last_closed != 'list_item'\
                                and self.last_closed != 'list_item_header'\
                                and self.last_closed != 'list_item_footer'\
                                and self.last_closed != 'list_item_label':
                return Moinwiki.linebreak
        return u''

    def close_moinpage_p(self, elem):
        self.status.pop()
        if self.status[-1] == 'text':
                return Moinwiki.p
        return u''

    def open_moinpage_page(self, elem):
        self.last_closed = None
        self.children.append(iter(elem))
        self.opened.append(elem)
        ret = u''
        if len(self.status) > 1:
            self.subpage.append([])
            self.subpage_level.append(3)
            self.output = self.subpage[-1]
            ret = u"#!wiki"
        self.status.append('text')
        return ret

    def close_moinpage_page(self, elem):
        self.status.pop()
        ret = u''
        if len(self.status) > 1:
            ret = u"{"*self.subpage_level[-1] + u''.join(self.subpage.pop()) + u"}"*self.subpage_level[-1] + u"\n"
            subpage_lvl = self.subpage_level.pop()
            if subpage_lvl >= self.subpage_level[-1]:
                self.subpage_level[-1] = subpage_lvl + 1
            self.output = self.subpage[-1]
        return ret

    def open_moinpage_body(self, elem):
        self.children.append(iter(elem))
        self.opened.append(elem)
        class_ = elem.get(moin_page.class_, u'').replace(u' ', u'/')
        if class_:
            return u' %s\n' % class_
        if len(self.status) > 2:
            return u'\n'
        return u''

    def close_moinpage_body(self, elem):
        return u''

    def open_moinpage_part(self, elem):
        type = elem.get(moin_page.content_type, u"").split(u';')
        if len(type) == 2:
            if type[0] == "x-moin/macro":
                if len(elem) and iter(elem).next().tag.name == "arguments":
                    return u"<<%s(%s)>>\n" % (type[1].split(u'=')[1], u','.join([u''.join(c.itertext()) for c in iter(elem).next() if c.tag.name == u"argument"]))
                else:
                    return u"<<%s()>>\n" % type[1].split(u'=')[1]
            elif type[0] == "x-moin/format":
                elem_it = iter(elem)
                ret = u"{{{#!%s" % type[1].split(u'=')[1]
                if len(elem) and elem_it.next().tag.name == "arguments":
                    args = []
                    for arg in iter(elem).next():
                        if arg.tag.name == "argument":
                            args.append(u"%s=\"%s\"" % (arg.get(moin_page.name, u""), u' '.join(arg.itertext())))
                    ret = u'%s(%s)' % (ret, u' '.join(args))
                    elem = elem_it.next()
                ret = u"%s\n%s\n}}}\n" % (ret, u' '.join(elem.itertext()))
                return ret
        return unescape(elem.get(moin_page.alt, u'')) + u"\n"

    def open_moinpage_inline_part(self, elem):
        ret = self.open_moinpage_part(elem)
        if ret[-1] == u'\n':
            ret = ret[:-1]
        return ret

    def close_moinpage_inline_part(self, elem):
        return u''

    def close_moinpage_part(self, elem):
        return u''

    def open_moinpage_separator(self, elem):
        return Moinwiki.separator + u'\n'

    def open_moinpage_span(self, elem):
        text_decoration = elem.get(moin_page.text_decoration, u'')
        font_size = elem.get(moin_page.font_size, u'')
        baseline_shift = elem.get(moin_page.baseline_shift, u'')

        if text_decoration == u'line-through':
            self.children.append(iter(elem))
            self.opened.append(elem)
            return Moinwiki.stroke_open
        if text_decoration == u'underline':
            self.children.append(iter(elem))
            self.opened.append(elem)
            return Moinwiki.underline
        if font_size:
            self.children.append(iter(elem))
            self.opened.append(elem)
            return Moinwiki.larger_open if font_size == u"120%" \
                                        else Moinwiki.smaller_open
        if baseline_shift == u'super':
            return u'^%s^' % u''.join(elem.itertext())
        if baseline_shift == u'sub':
            return u',,%s,,' % u''.join(elem.itertext())
        self.children.append(iter(elem))
        self.opened.append(elem)
        return u''

    def close_moinpage_span(self, elem):
        text_decoration = elem.get(moin_page.text_decoration, '')
        font_size = elem.get(moin_page.font_size, '')

        if text_decoration == u'line-through':
            return Moinwiki.stroke_close
        if text_decoration == u'underline':
            return Moinwiki.underline
        if font_size:
            return Moinwiki.larger_close if font_size == u"120%" \
                                         else Moinwiki.smaller_close
        return u''

    def open_moinpage_strong(self, elem):
        ret = Moinwiki.strong
        self.children.append(iter(elem))
        self.opened.append(elem)
        return ret

    def close_moinpage_strong(self, elem):
        return Moinwiki.strong

    def open_moinpage_table(self, elem):
        self.table_tableclass = elem.attrib.get('class', u'')
        self.table_tablestyle = elem.attrib.get('style', u'')
        self.table_rowsstyle = u''
        self.table_rowsclass = u''
        self.children.append(iter(elem))
        self.opened.append(elem)
        self.status.append('table')
        self.last_closed = None
        return u''

    def close_moinpage_table(self, elem):
        self.status.pop()
        return u''

    def open_moinpage_table_header(self, elem):
        # is this correct rowclass?
        self.table_rowsclass = 'table-header'
        self.children.append(iter(elem))
        self.opened.append(elem)
        return u''

    def close_moinpage_table_header(self, elem):
        self.table_rowsclass = u''
        return u''

    def open_moinpage_table_footer(self, elem):
        self.table_rowsclass = 'table-footer'
        self.children.append(iter(elem))
        self.opened.append(elem)
        return u''

    def close_moinpage_table_footer(self, elem):
        self.table_rowsclass = ''
        return u''

    def open_moinpage_table_body(self, elem):
        self.table_rowsclass = ''
        self.children.append(iter(elem))
        self.opened.append(elem)
        return u''

    def close_moinpage_table_body(self, elem):
        return u''

    def open_moinpage_table_row(self, elem):
        self.table_rowclass = elem.attrib.get('class', u'')
        self.table_rowclass = u' '.join([s for s in [self.table_rowsclass, self.table_rowclass] if s])
        self.table_rowstyle = elem.attrib.get('style', u'')
        self.table_rowstyle = u' '.join([s for s in [self.table_rowsstyle, self.table_rowstyle] if s])
        self.children.append(iter(elem))
        self.opened.append(elem)
        return u''

    def close_moinpage_table_row(self, elem):
        self.table_rowstyle = ''
        self.table_rowclass = ''
        return Moinwiki.table_marker + u'\n'

    def open_moinpage_table_cell(self, elem):
        table_cellclass = elem.attrib.get('class', u'')
        table_cellstyle = elem.attrib.get('style', u'')
        number_columns_spanned = int(elem.get(moin_page.number_columns_spanned, 1))
        number_rows_spanned = elem.get(moin_page.number_rows_spanned, None)
        ret = Moinwiki.table_marker * number_columns_spanned

        attrib = []

        # TODO: maybe this can be written shorter
        if self.table_tableclass:
            attrib.append(u'tableclass="%s"' % self.table_tableclass)
            self.table_tableclass = u''
        if self.table_tablestyle:
            attrib.append(u'tablestyle="%s"' % self.table_tablestyle)
            self.table_tableclass = u''
        if self.table_rowclass:
            attrib.append(u'rowclass="%s"' % self.table_rowclass)
            self.table_rowclass = u''
        if self.table_rowstyle:
            attrib.append(u'rowclass="%s"' % self.table_rowstyle)
            self.table_rowstyle = u''
        if table_cellclass:
            attrib.append(u'class="%s"' % table_cellclass)
        if table_cellstyle:
            attrib.append(u'style="%s"' % table_cellstyle)
        if number_rows_spanned:
            attrib.append(u'|'+number_rows_spanned)

        attrib = u' '.join(attrib)

        if attrib:
            ret += u'<%s>' % attrib

        self.children.append(iter(elem))
        self.opened.append(elem)
        return ret

    def close_moinpage_table_cell(self, elem):
        return u''

    def open_moinpage_table_of_content(self, elem):
        return u"<<TableOfContents(%s)>>\n" % elem.get(moin_page.outline_level, u"")

    def close_moinpage_table_of_content(self, elem):
        return u''

from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document, type_moin_wiki
default_registry.register(Converter.factory, type_moin_document, type_moin_wiki)
default_registry.register(Converter.factory, type_moin_document, Type('x-moin/format;name=wiki'))
