"""
MoinMoin - Moin Wiki input converter

@copyright: 2000-2002 Juergen Hermann <jh@web.de>
            2006-2008 MoinMoin:ThomasWaldmann
            2007 MoinMoin:ReimarBauer
            2008,2009 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import re
from emeraldtree import ElementTree as ET

from MoinMoin import config, wikiutil
from MoinMoin.util import iri
from MoinMoin.util.mime import Type
from MoinMoin.util.tree import html, moin_page, xlink
from MoinMoin.converter2._args_wiki import parse as parse_arguments
from MoinMoin.converter2._registry import default_registry
from MoinMoin.converter2._wiki_macro import ConverterMacro


class _Iter(object):
    """
    Iterator with push back support

    Collected items can be pushed back into the iterator and further calls will
    return them.
    """

    def __init__(self, parent):
        self.__finished = False
        self.__parent = iter(parent)
        self.__prepend = []

    def __iter__(self):
        return self

    def next(self):
        if self.__finished:
            raise StopIteration

        if self.__prepend:
            return self.__prepend.pop(0)

        try:
            return self.__parent.next()
        except StopIteration:
            self.__finished = True
            raise

    def push(self, item):
        self.__prepend.append(item)


class _Stack(list):
    def clear(self):
        del self[1:]

    def pop_name(self, *names):
        """
        Remove anything from the stack including the given node.
        """
        while len(self) > 2 and not self.top_check(*names):
            self.pop()
        self.pop()

    def push(self, elem):
        self.top_append(elem)
        self.append(elem)

    def top(self):
        return self[-1]

    def top_append(self, elem):
        self[-1].append(elem)

    def top_append_ifnotempty(self, elem):
        if elem:
            self.top_append(elem)

    def top_check(self, *names):
        """
        Checks if the name of the top of the stack matches the parameters.
        """
        tag = self[-1].tag
        return tag.uri == moin_page.namespace and tag.name in names


class Converter(ConverterMacro):
    @classmethod
    def factory(cls, _request, input, output):
        if output.type == 'application' and output.subtype == 'x.moin.document':
            if input.type == 'text' and input.subtype == 'x.moin.wiki':
                return cls
            if (input.type == 'x-moin' and input.subtype == 'format' and
                    input.parameters.get('name') == 'wiki'):
                return cls

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

    block_list = r"""
        (?P<list>
            ^
            (?P<list_indent> \s+ )
            (
                (?P<list_numbers> [0-9]+\.\s )
                |
                (?P<list_alpha> [aA]\.\s )
                |
                (?P<list_roman> [iI]\.\s )
                |
                (?P<list_bullet> \* )
                |
                (?P<list_none> \. )
            )
            \s*
            (?P<list_text> .*? )
            $
        )
    """

    def block_list_repl(self, _iter_content, stack,
            list, list_indent, list_numbers=None,
            list_alpha=None, list_roman=None, list_bullet=None,
            list_none=None, list_text=None):

        level = len(list_indent)

        type = 'unordered'
        style_type = None
        if list_numbers:
            type = 'ordered'
        elif list_alpha:
            type = 'ordered'
            style_type = 'upper-alpha'
        elif list_roman:
            type = 'ordered'
            style_type = 'upper-roman'
        elif list_none:
            style_type = 'none'

        while True:
            cur = stack.top()
            if cur.tag.name in ('body', 'blockquote'):
                break
            if cur.tag.name == 'list-item-body':
                if level > cur.level:
                    break
            if cur.tag.name == 'list':
                if (level >= cur.level and type == cur.type and
                        style_type == cur.style_type):
                    break
            stack.pop()

        if cur.tag.name != 'list':
            attrib = {moin_page.item_label_generate: type}
            if style_type:
                attrib[moin_page.list_style_type] = style_type
            element = moin_page.list(attrib=attrib)
            element.level, element.type = level, type
            element.style_type = style_type
            stack.push(element)

        element = moin_page.list_item()
        element_body = moin_page.list_item_body()
        element_body.level, element_body.type = level, type

        stack.push(element)
        stack.push(element_body)

        self.parse_inline(list_text, stack)

    block_macro = r"""
        ^
        \s*
        (?P<macro>
            <<
            (?P<macro_name> \w+ )
            (
                \(
                (?P<macro_args> .*? )
                \)
            )?
            \s*
            (
                [|]
                \s*
                (?P<macro_text> .+? )
                \s*
            )?
            >>
        )
        \s*
        $
    """

    def block_macro_repl(self, _iter_content, stack, macro, macro_name, macro_args=u''):
        """Handles macros using the placeholder syntax."""

        stack.clear()
        elem = self.macro(macro_name, macro_args, macro, True)
        stack.top_append_ifnotempty(elem)

    block_nowiki = r"""
        (?P<nowiki>
            ^
            \s*
            (?P<nowiki_marker> \{{3,} )
            \s*
            (?P<nowiki_interpret>
                \#!
                \s*
                (?P<nowiki_name> [\w/-]+ )?
                \s*
                (:?
                    \(
                    (?P<nowiki_args> .*? )
                    \)
                )?
            )?
            \s*
            $
        )
    """
    # Matches the beginning of a nowiki block

    nowiki_end = r"""
        ^
        (?P<marker> }{3,} )
        \s*
        $
    """
    # Matches the possibly escaped end of a nowiki block

    def block_nowiki_lines(self, iter_content, marker_len):
        "Unescaping generator for the lines in a nowiki block"

        for line in iter_content:
            match = self.nowiki_end_re.match(line)
            if match:
                marker = match.group('marker')
                if len(marker) >= marker_len:
                    return
            yield line

    def block_nowiki_repl(self, iter_content, stack, nowiki, nowiki_marker,
            nowiki_interpret=None, nowiki_name=None, nowiki_args=None):
        stack.clear()

        nowiki_marker_len = len(nowiki_marker)

        lines = _Iter(self.block_nowiki_lines(iter_content, nowiki_marker_len))

        if nowiki_interpret:
            if nowiki_args:
                nowiki_args = parse_arguments(nowiki_args)

            # Parse it directly if the type is ourself
            if not nowiki_name:
                body = self.parse_block(lines, nowiki_args)
                elem = moin_page.page(children=(body, ))
                stack.top_append(elem)

            else:
                if '/' in nowiki_name:
                    type = Type(nowiki_name)
                else:
                    type = Type(type='x-moin', subtype='format', parameters={'name': nowiki_name})

                converter = default_registry.get(self.request, type, Type('application/x.moin.document'))

                doc = converter(self.request)(lines, nowiki_args)
                stack.top_append(doc)

        else:
            elem = moin_page.blockcode()
            stack.top_append(elem)

            for line in lines:
                if len(elem):
                    elem.append('\n')
                elem.append(line)

    block_separator = r'(?P<separator> ^ \s* -{4,} \s* $ )'

    def block_separator_repl(self, _iter_content, stack, separator):
        stack.clear()
        stack.top_append(moin_page.separator())

    block_table = r"""
        ^
        \s*
        (?P<table>
            \|\|
            .*
        )
        \|\|
        \s*
        $
    """

    def block_table_repl(self, iter_content, stack, table):
        stack.clear()

        element = moin_page.table()
        stack.push(element)
        element = moin_page.table_body()
        stack.push(element)

        self.block_table_row(table, stack)

        for line in iter_content:
            match = self.table_re.match(line)
            if not match:
                # Allow the mainloop to take care of the line after a list.
                iter_content.push(line)
                break

            self.block_table_row(match.group('table'), stack)

    def block_table_row(self, content, stack):
        element = moin_page.table_row()
        stack.push(element)

        for match in self.tablerow_re.finditer(content):
            self._apply(match, 'tablerow', stack)

        stack.pop()

    block_text = r'(?P<text> .+ )'

    def block_text_repl(self, _iter_content, stack, text):
        if stack.top_check('table', 'table-body', 'list'):
            stack.clear()

        if stack.top_check('body'):
            element = moin_page.p()
            stack.push(element)
        # If we are in a paragraph already, don't loose the whitespace
        else:
            stack.top_append('\n')
        self.parse_inline(text, stack)

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

    inline_size = r"""
        (?P<size>
           (?P<size_begin>
              ~[-+]
           )
           |
           (?P<size_end>
              [-+]~
           )
        )
    """

    def inline_size_repl(self, stack, size, size_begin=None, size_end=None):
        if size_begin:
            size = size[1] == '+' and '120%' or '85%'
            attrib = {moin_page.font_size: size}
            elem = moin_page.span(attrib=attrib)
            stack.push(elem)
        else:
            stack.pop()

    inline_strike = r"""
        (?P<strike>
           (?P<strike_begin>)
           --\(
           |
           \)--
        )
    """

    def inline_strike_repl(self, stack,strike, strike_begin=None):
        if strike_begin is not None:
            attrib = {moin_page.text_decoration: 'line-through'}
            stack.push(moin_page.span(attrib=attrib))
        else:
            stack.pop()

    inline_subscript = r"""
        (?P<subscript>
            ,,
            (?P<subscript_text> .*? )
            ,,
        )
    """

    def inline_subscript_repl(self, stack, subscript, subscript_text):
        attrib = {moin_page.baseline_shift: 'sub'}
        elem = moin_page.span(attrib=attrib, children=[subscript_text])
        stack.top_append(elem)

    inline_superscript = r"""
        (?P<superscript>
            \^
            (?P<superscript_text> .*? )
            \^
        )
    """

    def inline_superscript_repl(self, stack, superscript, superscript_text):
        attrib = {moin_page.baseline_shift: 'super'}
        elem = moin_page.span(attrib=attrib, children=[superscript_text])
        stack.top_append(elem)

    inline_underline = r"""
        (?P<underline>
            __
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
                (?P<link_page> [^|]+? )
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

    def inline_link_repl(self, stack, link, link_url=None, link_page=None,
            link_text=None, link_args=None):
        """Handle all kinds of links."""

        # TODO: Query string / fragment
        if link_page is not None:
            if '#' in link_page:
                path, fragment = link_page.rsplit('#', 1)
            else:
                path, fragment = link_page, None
            target = unicode(iri.Iri(scheme='wiki.local', path=path, fragment=fragment))
            text = link_page
        else:
            target = unicode(iri.Iri(link_url))
            text = link_url
        element = moin_page.a(attrib={xlink.href: target})
        stack.push(element)
        if link_text:
            self.parse_inline(link_text, stack, self.inlinedesc_re)
        else:
            stack.top_append(text)
        stack.pop()

    inline_macro = r"""
        (?P<macro>
            <<
            (?P<macro_name> \w+ )
            (
                \(
                (?P<macro_args> .*? )
                \)
            )?
            \s*
            (
                [|]
                \s*
                (?P<macro_text> .+? )
                \s*
            )?
            >>
        )
    """

    def inline_macro_repl(self, stack, macro, macro_name, macro_args=u''):
        """Handles macros using the placeholder syntax."""

        elem = self.macro(macro_name, macro_args, macro)
        stack.top_append(elem)

    inline_nowiki = r"""
        (?P<nowiki>
            {{{
            (?P<nowiki_text>.*?}*)
            }}}
            |
            `
            (?P<nowiki_text_backtick> .*? )
            `
        )
    """

    def inline_nowiki_repl(self, stack, nowiki, nowiki_text=None,
            nowiki_text_backtick=None):
        text = None
        if nowiki_text is not None:
            text = nowiki_text
        # Remove empty backtick nowiki samples
        elif nowiki_text_backtick:
            text = nowiki_text_backtick
        else:
            return

        stack.top_append(moin_page.code(children=[text]))

    inline_object = r"""
        (?P<object>
            {{
            (?P<object_target> .+? )
            \s*
            (
                [|]
                \s*
                (?P<object_text> .+? )
                \s*
            )?
            }}
        )
    """

    def inline_object_repl(self, stack, object, object_target, object_text=None):
        """Handles objects included in the page."""

        target = unicode(iri.Iri(object_target))

        attrib = {xlink.href: target}
        if object_text is not None:
            attrib[moin_page.alt] = object_text

        element = moin_page.object(attrib)
        stack.top_append(element)

    inline_freelink = r"""
         (?:
          (?<![%(u)s%(l)s/])  # require anything not upper/lower/slash before
          |
          ^  # ... or beginning of line
         )
         (?P<freelink_bang>\!)?  # configurable: avoid getting CamelCase rendered as link
         (?P<freelink>
          (?P<freelink_interwiki_ref>
           [A-Z][a-zA-Z]+
          )
          \:
          (?P<freelink_interwiki_page>
           (?=\S*[%(u)s%(l)s0..9]\S* )  # make sure there is something non-blank with at least one alphanum letter following
           [^\s"\'}\]|:,.\)?!]+  # we take all until we hit some blank or punctuation char ...
          )
          |
          (?P<freelink_page>
           (?:
            (%(parent)s)*  # there might be either ../ parent prefix(es)
            |
            ((?<!%(child)s)%(child)s)?  # or maybe a single / child prefix (but not if we already had it before)
           )
           (
            ((?<!%(child)s)%(child)s)?  # there might be / child prefix (but not if we already had it before)
            (?:[%(u)s][%(l)s]+){2,}  # at least 2 upper>lower transitions make CamelCase
           )+  # we can have MainPage/SubPage/SubSubPage ...
           (?:
            \#  # anchor separator          TODO check if this does not make trouble at places where word_rule is used
            \S+  # some anchor name
           )?
          )
          |
          (?P<freelink_email>
           [-\w._+]+  # name
           \@  # at
           [\w-]+(\.[\w-]+)+  # server/domain
          )
         )
         (?:
          (?![%(u)s%(l)s/])  # require anything not upper/lower/slash following
          |
          $  # ... or end of line
         )
    """ % {
        'u': config.chars_upper,
        'l': config.chars_lower,
        'child': re.escape(wikiutil.CHILD_PREFIX),
        'parent': re.escape(wikiutil.PARENT_PREFIX),
    }

    def inline_freelink_repl(self, stack, freelink, freelink_bang=None,
            freelink_interwiki_page=None, freelink_interwiki_ref=None,
            freelink_page=None, freelink_email=None):
        if freelink_bang:
            stack.top_append(freelink)
            return

        attrib = {}

        if freelink_page:
            page = freelink_page.encode('utf-8')
            if '#' in page:
                path, fragment = page.rsplit('#', 1)
            else:
                path, fragment = page, None
            link = iri.Iri(scheme='wiki.local', path=path, fragment=fragment)
            text = freelink_page

        elif freelink_email:
            link = 'mailto:' + freelink_email
            text = freelink_email

        else:
            wikitag_bad = wikiutil.resolve_interwiki(self.request,
                    freelink_interwiki_ref, freelink_interwiki_page)[3]
            if wikitag_bad:
                stack.top_append(freelink)
                return

            link = iri.Iri(scheme='wiki',
                    authority=freelink_interwiki_ref,
                    path='/' + freelink_interwiki_page)
            text = freelink_interwiki_page

        attrib[xlink.href] = unicode(link)

        element = moin_page.a(attrib, children=[text])
        stack.top_append(element)

    inline_url = r"""
        (?P<url>
            (
                ^
                |
                (?<=
                    \s
                    |
                    [.,:;!?()/=]
                )
            )
            (?P<url_target>
                # TODO: config.url_schemas
                (http|https|ftp|nntp|news|mailto|telnet|file|irc):
                \S+?
            )
            (
                $
                |
                (?=
                    \s
                    |
                    [,.:;!?()]
                    (\s | $)
                )
            )
        )
    """

    def inline_url_repl(self, stack, url, url_target):
        url = unicode(iri.Iri(url_target))
        attrib = {xlink.href: url}
        element = moin_page.a(attrib=attrib, children=[url_target])
        stack.top_append(element)

    table = block_table

    tablerow = r"""
        (?P<cell>
            (?P<cell_marker>
                (\|\|)+
            )
            (
                <
                (?P<cell_args> .*? )
                >
            )?
            \s*
            (?P<cell_text> .*? )
            \s*
            (?=
                \|\|
                |
                $
            )
        )
    """

    def tablerow_cell_repl(self, stack, cell, cell_marker, cell_text, cell_args=None):
        element = moin_page.table_cell()
        stack.push(element)

        self.parse_inline(cell_text, stack)

        stack.pop_name('table-cell')

    # Block elements
    block = (
        block_line,
        block_comment,
        block_head,
        block_separator,
        block_macro,
        block_nowiki,
        block_list,
        block_table,
        block_text,
    )
    block_re = re.compile('|'.join(block), re.X | re.U | re.M)

    inline = (
        inline_link,
        inline_macro,
        inline_nowiki,
        inline_object,
        inline_emphstrong,
        inline_comment,
        inline_size,
        inline_strike,
        inline_subscript,
        inline_superscript,
        inline_underline,
        inline_freelink,
        inline_url,
        inline_entity,
    )
    inline_re = re.compile('|'.join(inline), re.X | re.U)

    inlinedesc = (
        inline_macro,
        inline_nowiki,
        inline_emphstrong,
    )
    inlinedesc_re = re.compile('|'.join(inlinedesc), re.X | re.U)

    # Nowiki end
    nowiki_end_re = re.compile(nowiki_end, re.X)

    # Table
    table_re = re.compile(table, re.X | re.U)

    # Table row
    tablerow_re = re.compile(tablerow, re.X | re.U)

    def _apply(self, match, prefix, *args):
        """
        Call the _repl method for the last matched group with the given prefix.
        """
        data = dict(((str(k), v) for k, v in match.groupdict().iteritems() if v is not None))
        getattr(self, '%s_%s_repl' % (prefix, match.lastgroup))(*args, **data)

    def parse_block(self, iter_content, arguments):
        attrib = {}
        if arguments:
            for key, value in arguments.keyword.iteritems():
                if key in ('background-color', 'color'):
                    attrib[moin_page(key)] = value

        body = moin_page.body(attrib=attrib)

        stack = _Stack([body])

        for line in iter_content:
            match = self.block_re.match(line)
            self._apply(match, 'block', iter_content, stack)

        return body

    def parse_inline(self, text, stack, inline_re=inline_re):
        """Recognize inline elements within the given text"""

        pos = 0
        for match in inline_re.finditer(text):
            # Handle leading text
            stack.top_append_ifnotempty(text[pos:match.start()])
            pos = match.end()

            self._apply(match, 'inline', stack)

        # Handle trailing text
        stack.top_append_ifnotempty(text[pos:])


default_registry.register(Converter.factory)
