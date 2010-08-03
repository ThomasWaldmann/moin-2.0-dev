"""
MoinMoin - Media Wiki input converter

@copyright: 2000-2002 Juergen Hermann <jh@web.de>,
            2006-2008 MoinMoin:ThomasWaldmann,
            2007 MoinMoin:ReimarBauer,
            2008-2010 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

import re

from werkzeug import url_encode

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import config
from MoinMoin.util.iri import Iri
from MoinMoin.util.tree import html, moin_page, xlink
from MoinMoin.converter2.moinwiki_in import _Iter, _Stack

from ._args import Arguments
from ._args_wiki import parse as parse_arguments
from ._wiki_macro import ConverterMacro

class _TableArguments(object):
    rules = r'''
    (?:
        (?P<arg>
            (?:
                (?P<key> [-\w]+)
                =
            )?
            (?:
                (?P<value_u> [-\w]+)
                |
                "
                (?P<value_q1> .*?)
                (?<!\\)"
                |
                '
                (?P<value_q2> .*?)
                (?<!\\)'
            )
        )
    )
    '''
    _re = re.compile(rules, re.X)

    map_keys = {
        'colspan': 'number-columns-spanned',
        'rowspan': 'number-rows-spanned',
    }

    def arg_repl(self, args, arg, key=None, value_u=None, value_q1=None, value_q2=None):
        key = self.map_keys.get(key, key)
        value = (value_u or value_q1 or value_q2).decode('unicode-escape')

        if key:
            args.keyword[key] = value
        else:
            args.positional.append(value)

    def number_columns_spanned_repl(self, args, number_columns_spanned):
        args.keyword['number-columns-spanned'] = int(number_columns_spanned)

    def number_rows_spanned_repl(self, args, number_rows_spanned):
        args.keyword['number-rows-spanned'] = int(number_rows_spanned)

    def __call__(self, input):
        args = Arguments()

        for match in self._re.finditer(input):
            data = dict(((str(k), v) for k, v in match.groupdict().iteritems() if v is not None))
            getattr(self, '%s_repl' % match.lastgroup)(args, **data)

        return args


class Converter(ConverterMacro):
    @classmethod
    def factory(cls, input, output, **kw):
        return cls()

    def __call__(self, content, arguments=None):
        iter_content = _Iter(content)

        body = self.parse_block(iter_content, arguments)
        root = moin_page.page(children=(body, ))

        return root

    block_comment = r"""
        (?P<comment>
            ^ \#\#
        )
    """

    def block_comment_repl(self, _iter_content, stack, comment):
        # A comment also ends anything
        stack.clear()

    block_head = r"""
        (?P<head>
            ^
            \s*
            (?P<head_head> =+ )
            \s*
            (?P<head_text> .*? )
            \s*
            (?P=head_head)
            \s*
            $
        )
    """

    def block_head_repl(self, _iter_content, stack, head, head_head, head_text):
        stack.clear()

        attrib = {moin_page.outline_level: str(len(head_head))}
        element = moin_page.h(attrib=attrib, children=[head_text])
        stack.top_append(element)

    block_line = r'(?P<line> ^ \s* $ )'
    # empty line that separates paragraphs

    def block_line_repl(self, _iter_content, stack, line):
        stack.clear()

    block_separator = r'(?P<separator> ^ \s* -{4,} \s* $ )'

    def block_separator_repl(self, _iter_content, stack, separator):
        stack.clear()
        stack.top_append(moin_page.separator())


    block_table = r"""
        ^
        (?P<table>
            \{\|
            \s*
            (?P<table_args> .*?)
        )
        $
    """

    table_end = r"""
        ^
        (?P<table_end>
        \|\}
        \s*
        )
        $
    """

    def block_table_lines(self, iter_content):
        "Unescaping generator for the lines in a table block"
        for line in iter_content:
            match = self.table_end_re.match(line)
            if match:
                return
            yield line

    def block_table_repl(self, iter_content, stack, table, table_args=''):
        stack.clear()
        # TODO: table attributes
        elem = moin_page.table()
        stack.push(elem)
        if table_args:
            table_args = _TableArguments()(table_args)
            for key, value in table_args.keyword.iteritems():
                attrib = elem.attrib
                if key in ('class', 'style', 'number-columns-spanned', 'number-rows-spanned'):
                    attrib[moin_page(key)] = value

        element = moin_page.table_body()
        stack.push(element)
        lines = _Iter(self.block_table_lines(iter_content))
        element = moin_page.table_row()
        stack.push(element)
        for line in lines:
            m = self.tablerow_re.match(line)
            if not m:
                return
            if m.group('newrow'):
                stack.pop_name('table-row')
                element = moin_page.table_row()
                stack.push(element)
            cells = m.group('cells')
            if cells:
                cells = cells.split('||')
                for cell in cells:
                    if stack.top_check('table-cell'):
                        stack.pop()

                    cell = re.split(r'\s*\|\s*', cell)
                    element = moin_page.table_cell()
                    if len(cell) > 1:
                        cell_args = _TableArguments()(cell[0])
                        print cell[0],  cell_args
                        for key, value in cell_args.keyword.iteritems():
                            attrib = element.attrib
                            if key in ('class', 'style', 'number-columns-spanned', 'number-rows-spanned'):
                                attrib[moin_page(key)] = value
                        cell = cell[1]
                    else:
                        cell = cell[0]
                    stack.push(element)
                    self.parse_inline(cell, stack, self.inline_re)
            elif m.group('text'):
                self.parse_inline(m.group('text'), stack, self.inline_re)
        stack.pop_name('table')

    block_text = r'(?P<text> .+ )'

    def block_text_repl(self, _iter_content, stack, text):
        if stack.top_check('table', 'table-body', 'list'):
            stack.clear()

        if stack.top_check('body', 'list-item-body'):
            element = moin_page.p()
            stack.push(element)
        # If we are in a paragraph already, don't loose the whitespace
        else:
            stack.top_append('\n')
        self.parse_inline(text, stack, self.inline_re)

    indent = r"""
        ^
        (?P<indent> [*#:]* )
        (?P<list_begin>
            (?P<list_definition> ;
            )
            \s*
            |
            (?P<list_numbers> \# )
            \s+
            |
            (?P<list_bullet> \* )
            \s+
            |
            (?P<list_none> \: )
            \s+
        )
        (?P<text> .*? )
        $
    """

    def indent_iter(self, iter_content, line, level, is_list):
        yield line

        while True:
            line = iter_content.next()

            match = self.indent_re.match(line)

            new_level = 0
            if not match:
                if is_list:
                    iter_content.push(line)
                    return
                else:
                    yield line
                    break

            if match.group('indent'):
                new_level = len(match.group('indent'))

            if match.group('list_begin') or level != new_level:
                iter_content.push(line)
                return

            yield match.group('text')

    def indent_repl(self, iter_content, stack, line,
            indent, text, list_begin=None, list_definition=None,
            list_definition_text=None, list_numbers=None,
            list_bullet=None,
            list_none=None):

        level = len(indent)
        list_type = 'unordered', 'none'
        if list_begin:
            if list_definition:
                list_type = 'definition', None
            elif list_numbers:
                list_type = 'ordered', None
            elif list_bullet:
                list_type = 'unordered', None
            elif list_none:
                list_type = None, None

        element_use = None
        while len(stack) > 1:
            cur = stack.top()
            if cur.tag.name == 'list-item-body':
                if level > cur.level:
                    element_use = cur
                    break
            if cur.tag.name == 'list':
                if level >= cur.level and list_type == cur.list_type:
                    element_use = cur
                    break
            stack.pop()

        if not element_use:
            element_use = stack.top()
        if list_begin:
            if element_use.tag.name != 'list':
                attrib = {}
                if not list_definition:
                    attrib[moin_page.item_label_generate] = list_type[0]
                if list_type[1]:
                    attrib[moin_page.list_style_type] = list_type[1]
                element = moin_page.list(attrib=attrib)
                element.level, element.list_type = level, list_type
                stack.push(element)

            stack.push(moin_page.list_item())
            if list_definition:
                element_label = moin_page.list_item_label()
                stack.top_append(element_label)
                new_stack = _Stack(element_label)
                # TODO: definition list doesn't work,
                #       if definition of the term on the next line
                splited_text = text.split(':')
                list_definition_text=splited_text.pop(0)
                text = ':'.join(splited_text)

                self.parse_inline(list_definition_text, new_stack, self.inline_re)

            element_body = moin_page.list_item_body()
            element_body.level, element_body.type = level, type

            stack.push(element_body)
            new_stack = _Stack(element_body)
        else:
            new_stack = stack
            level = 0

        is_list = list_begin
        iter = _Iter(self.indent_iter(iter_content, text, level, is_list))
        for line in iter:
            match = self.block_re.match(line)
            it = iter
            # XXX: Hack to allow nowiki to ignore the list identation
            if match.lastgroup == 'table' or match.lastgroup == 'nowiki':
                it = iter_content
            self._apply(match, 'block', it, new_stack)

    inline_comment = r"""
        (?P<comment>
            (?P<comment_begin>
                (^|(?<=\s))
                /\*
                \s+
            )
            |
            (?P<comment_end>
                \s+
                \*/
                (?=\s)
            )
        )
    """

    def inline_comment_repl(self, stack, comment, comment_begin=None, comment_end=None):
        # TODO
        pass

    inline_emphstrong = r"""
        (?P<emphstrong>
            '{2,6}
            (?=
                [^']+
                (?P<emphstrong_follow>
                    '{2,3}
                    (?!')
                )
            )?
        )
    """

    def inline_emphstrong_repl(self, stack, emphstrong, emphstrong_follow=''):
        if len(emphstrong) == 5:
            if stack.top_check('emphasis'):
                stack.pop()
                if stack.top_check('strong'):
                    stack.pop()
                else:
                    stack.push(moin_page.strong())
            elif stack.top_check('strong'):
                if stack.top_check('strong'):
                    stack.pop()
                else:
                    stack.push(moin_page.strong())
            else:
                if len(emphstrong_follow) == 3:
                    stack.push(moin_page.emphasis())
                    stack.push(moin_page.strong())
                else:
                    stack.push(moin_page.strong())
                    stack.push(moin_page.emphasis())
        elif len(emphstrong) == 3:
            if stack.top_check('strong'):
                stack.pop()
            else:
                stack.push(moin_page.strong())
        elif len(emphstrong) == 2:
            if stack.top_check('emphasis'):
                stack.pop()
            else:
                stack.push(moin_page.emphasis())

    inline_entity = r"""
        (?P<entity>
            &
            (?:
               # symbolic entity, like &uuml;
               [0-9a-zA-Z]{2,6}
               |
               # numeric decimal entities, like &#42;
               \#\d{1,5}
               |
               # numeric hexadecimal entities, like &#x42;
               \#x[0-9a-fA-F]{1,6}
           )
           ;
       )
    """

    def inline_entity_repl(self, stack, entity):
        if entity[1] == '#':
            if entity[2] == 'x':
                c = int(entity[3:-1], 16)
            else:
                c = int(entity[2:-1], 10)
            c = unichr(c)
        else:
            from htmlentitydefs import name2codepoint
            c = unichr(name2codepoint.get(entity[1:-1], 0xfffe))
        stack.top_append(c)

    inline_strike = r"""
        (?P<strike>
           (?P<strike_begin>
           \<del\>
           |
           \<s\>
           )
           |
           (?P<strike_end>
           \<\/del\>
           |
           \<\/s\>
           )
        )
    """

    def inline_strike_repl(self, stack, strike, strike_begin=None, strike_end=None):
        if strike_begin is not None:
            attrib = {moin_page.text_decoration: 'line-through'}
            stack.push(moin_page.span(attrib=attrib))
        elif strike_end is not None:
            stack.pop()

    inline_subscript = r"""
        (?P<subscript>
            <sub>
            (?P<subscript_text> .*? )
            </sub>
        )
    """

    def inline_subscript_repl(self, stack, subscript, subscript_text):
        attrib = {moin_page.baseline_shift: 'sub'}
        elem = moin_page.span(attrib=attrib, children=[subscript_text])
        stack.top_append(elem)

    inline_superscript = r"""
        (?P<superscript>
            <sup>
            (?P<superscript_text> .*? )
            </sup>
        )
    """

    def inline_superscript_repl(self, stack, superscript, superscript_text):
        attrib = {moin_page.baseline_shift: 'super'}
        elem = moin_page.span(attrib=attrib, children=[superscript_text])
        stack.top_append(elem)

    inline_underline = r"""
        (?P<underline>
            \<u\>
            |
            \<\/u\>
        )
    """

    def inline_underline_repl(self, stack, underline):
        if not stack.top_check('span'):
            attrib = {moin_page.text_decoration: 'underline'}
            stack.push(moin_page.span(attrib=attrib))
        else:
            stack.pop()

    inline_link = r"""
        (?P<link>
            \[\[
            \s*
            (
                (?P<link_url>
                    [a-zA-Z0-9+.-]+
                    ://
                    [^|]+?
                )
                |
                (?P<link_item> [^|]+? )
            )
            \s*
            (
                [|]
                \s*
                (?P<link_text> [^|]*? )
                \s*
            )?
            (
                [|]
                \s*
                (?P<link_args> .*? )
                \s*
            )?
            \]\]
        )
    """

    def inline_link_repl(self, stack, link, link_url=None, link_item=None,
            link_text=None, link_args=None):
        """Handle all kinds of links."""
        if link_args:
            link_args = parse_arguments(link_args) # XXX needs different parsing
            query = url_encode(link_args.keyword, charset=config.charset, encode_keys=True)
        else:
            query = None
        if link_item is not None:
            if '#' in link_item:
                path, fragment = link_item.rsplit('#', 1)
            else:
                path, fragment = link_item, None
            target = Iri(scheme='wiki.local', path=path, query=query, fragment=fragment)
            text = link_item
        else:
            target = Iri(link_url)
            text = link_url
        element = moin_page.a(attrib={xlink.href: target})
        stack.push(element)
        if link_text:
            self.parse_inline(link_text, stack, self.inlinedesc_re)
        else:
            stack.top_append(text)
        stack.pop()

    inline_breakline = r"""
        (?P<breakline>
            \<br\ \/\>
        )
    """

    def inline_breakline_repl(self, stack, breakline):
        stack.top_append(moin_page.line_break())

    inline_nowiki = r"""
        (?P<nowiki>
            <nowiki>
            (?P<nowiki_text> .*? )
            </nowiki>
            |
            <pre>
            (?P<nowiki_text_pre> .*? )
            </pre>
            |
            <code>
            (?P<nowiki_text_code> .*? )
            </code>
            |
            <tt>
            (?P<nowiki_text_tt> .*? )
            </tt>
        )
    """

    def inline_nowiki_repl(self, stack, nowiki, nowiki_text=None,
            nowiki_text_pre=None, pre_args='',
            nowiki_text_code=None, nowiki_text_tt=None):
        text = None

        if nowiki_text is not None:
            text = nowiki_text
            stack.top_append(moin_page.code(children=[text]))
        elif nowiki_text_code is not None:
            text = nowiki_text_code
            stack.top_append(moin_page.code(children=[text]))
        elif nowiki_text_tt is not None:
            text = nowiki_text_tt
            stack.top_append(moin_page.code(children=[text]))
        # Remove empty backtick nowiki samples
        elif nowiki_text_pre:
            # TODO: pre_args parsing
            text = nowiki_text_pre
            stack.top_append(moin_page.blockcode(children=[text]))
        else:
            return

    inline_object = r"""
        (?P<object>
            {{
            \s*
            (
                (?P<object_url>
                    [a-zA-Z0-9+.-]+
                    ://
                    [^|]+?
                )
                |
                (?P<object_item> [^|]+? )
            )
            \s*
            (
                [|]
                \s*
                (?P<object_text> [^|]*? )
                \s*
            )?
            (
                [|]
                \s*
                (?P<object_args> .*? )
                \s*
            )?
            }}
        )
    """

    '''
    def inline_object_repl(self, stack, object, object_url=None, object_item=None,
                           object_text=None, object_args=None):
        """Handles objects included in the page."""
        if object_args:
            args = parse_arguments(object_args).keyword # XXX needs different parsing
        else:
            args = {}
        if object_item is not None:
            if 'do' not in args:
                # by default, we want the item's get url for transclusion of raw data:
                args['do'] = 'get'
            query = url_encode(args, charset=config.charset, encode_keys=True)
            target = Iri(scheme='wiki.local', path=object_item, query=query, fragment=None)
            text = object_item
        else:
            target = Iri(object_url)
            text = object_url

        attrib = {xlink.href: target}
        if object_text is not None:
            attrib[moin_page.alt] = object_text

        element = moin_page.object(attrib)
        stack.push(element)
        if object_text:
            self.parse_inline(object_text, stack, self.inlinedesc_re)
        else:
            stack.top_append(text)
        stack.pop()
    '''

    table = block_table

    tablerow = r"""
        ^
        \|
        (?P<tablerow>
            (?P<caption> \+.* )
            |
            (?P<newrow> \-\s* )
            |
            (?P<cells> .* )
        )
        |
        (?P<text> .* )
        $
    """
    '''
    def tablerow_cell_repl(self, stack, table, row, cell, cell_marker, cell_text, cell_args=None):
        element = moin_page.table_cell()
        stack.push(element)

        if len(cell_marker) / 2 > 1:
            element.set(moin_page.number_columns_spanned, len(cell_marker) / 2)

        if cell_args:
            cell_args = _TableArguments()(cell_args)

            for key, value in cell_args.keyword.iteritems():
                attrib = element.attrib
                if key.startswith('table'):
                    key = key[5:]
                    attrib = table.attrib
                elif key.startswith('row'):
                    key = key[3:]
                    attrib = row.attrib

                if key in ('class', 'style', 'number-columns-spanned', 'number-rows-spanned'):
                    attrib[moin_page(key)] = value

        self.parse_inline(cell_text, stack, self.inline_re)

        stack.pop_name('table-cell')
    '''

    # Block elements
    block = (
        block_line,
        block_table,
        block_comment,
        block_head,
        block_separator,
       # block_macro,
       # block_nowiki,
        block_text,
    )
    block_re = re.compile('|'.join(block), re.X | re.U | re.M)

    indent_re = re.compile(indent, re.X)

    inline = (
        inline_link,
        inline_breakline,
        #inline_macro,
        inline_nowiki,
        inline_object,
        inline_emphstrong,
        inline_comment,
        #inline_size,
        inline_strike,
        inline_subscript,
        inline_superscript,
        inline_underline,
        inline_entity,
    )
    inline_re = re.compile('|'.join(inline), re.X | re.U)

    inlinedesc = (
        #inline_macro,
        inline_breakline,
        inline_nowiki,
        inline_emphstrong,
    )
    inlinedesc_re = re.compile('|'.join(inlinedesc), re.X | re.U)

    # Nowiki end
    #nowiki_end_re = re.compile(nowiki_end, re.X)

    # Table
    table_re = re.compile(table, re.X | re.U)
    table_end_re = re.compile(table_end, re.X)

    # Table row
    tablerow_re = re.compile(tablerow, re.X | re.U)

    def _apply(self, match, prefix, *args):
        """
        Call the _repl method for the last matched group with the given prefix.
        """
        data = dict(((str(k), v) for k, v in match.groupdict().iteritems() if v is not None))
        func = '%s_%s_repl' % (prefix, match.lastgroup)
        #logging.debug("calling %s(%r, %r)" % (func, args, data))
        getattr(self, func)(*args, **data)

    def parse_block(self, iter_content, arguments):
        attrib = {}
        if arguments:
            for key, value in arguments.keyword.iteritems():
                if key in ('style', ):
                    attrib[moin_page(key)] = value
                elif key == '_old':
                    attrib[moin_page.class_] = value.replace('/', ' ')

        body = moin_page.body(attrib=attrib)

        stack = _Stack(body)

        for line in iter_content:
            match = self.indent_re.match(line)
            if match:
                data = dict(((str(k), v) for k, v in match.groupdict().iteritems() if v is not None))
                self.indent_repl(iter_content, stack, line, **data)
            else:
                self.indent_repl(iter_content, stack, line, '', line)

        return body

    def parse_inline(self, text, stack, inline_re):
        """Recognize inline elements within the given text"""

        pos = 0
        for match in inline_re.finditer(text):
            # Handle leading text
            stack.top_append_ifnotempty(text[pos:match.start()])
            pos = match.end()

            self._apply(match, 'inline', stack)

        # Handle trailing text
        stack.top_append_ifnotempty(text[pos:])


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter.factory, Type('x-moin/format;name=mediawiki'), type_moin_document)
