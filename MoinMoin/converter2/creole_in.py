# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Creole input converter

    See http://wikicreole.org/ for latest specs.

    Notes:
    * No markup allowed in headings.
      Creole 1.0 does not require us to support this.
    * No markup allowed in table headings.
      Creole 1.0 does not require us to support this.
    * No (non-bracketed) generic url recognition: this is "mission impossible"
      except if you want to risk lots of false positives. Only known protocols
      are recognized.
    * We do not allow ":" before "//" italic markup to avoid urls with
      unrecognized schemes (like wtf://server/path) triggering italic rendering
      for the rest of the paragraph.

    @copyright: 2007 MoinMoin:RadomirDopieralski (creole 0.5 implementation),
                2007 MoinMoin:ThomasWaldmann (updates)
                2008 MoinMoin:BastianBlank
    @license: GNU GPL, see COPYING for details.
"""

import re
from emeraldtree import ElementTree as ET

from MoinMoin import wikiutil
from MoinMoin.util import iri
from MoinMoin.util.tree import moin_page, xlink
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

class Converter(ConverterMacro):
    tag_a = moin_page.a
    tag_alt = moin_page.alt
    tag_blockcode = moin_page.blockcode
    tag_code = moin_page.code
    tag_div = moin_page.div
    tag_emphasis = moin_page.emphasis
    tag_h = moin_page.h
    tag_href = xlink.href
    tag_line_break = moin_page.line_break
    tag_list = moin_page.list
    tag_list_item_body = moin_page.list_item_body
    tag_list_item = moin_page.list_item
    tag_object = moin_page.object
    tag_outline_level = moin_page.outline_level
    tag_p = moin_page.p
    tag_separator = moin_page.separator
    tag_strong = moin_page.strong
    tag_table_body = moin_page.table_body
    tag_table_cell = moin_page.table_cell
    tag_table = moin_page.table
    tag_table_row = moin_page.table_row

    @classmethod
    def factory(cls, _request, input, output):
        if input == 'text/creole' and output == 'application/x-moin-document':
            return cls

    def __init__(self, request, page_url=None, _args=None):
        super(Converter, self).__init__(request)
        self.page_url = page_url

        self._stack = []

    def __call__(self, content):
        attrib = {}
        if self.page_url:
            attrib[moin_page.page_href] = unicode(self.page_url)

        body = moin_page.body()
        root = moin_page.page(attrib=attrib, children=[body])

        self._stack = [body]
        iter_content = _Iter(content)

        # Please note that the iterator can be modified by other functions
        for line in iter_content:
            match = self.block_re.match(line)
            self._apply(match, 'block', iter_content)

        return root

    block_head = r"""
        (?P<head>
            ^ \s*
            (?P<head_head>=+) \s*
            (?P<head_text> .*? ) \s*
            =* \s*
            $
        )
    """

    def block_head_repl(self, _iter_content, head, head_head, head_text):
        self.stack_clear()

        attrib = {self.tag_outline_level: str(len(head_head))}
        element = ET.Element(self.tag_h, attrib=attrib, children=[head_text])
        self.stack_top_append(element)

    block_line = r'(?P<line> ^ \s* $ )'
    # empty line that separates paragraphs

    def block_line_repl(self, _iter_content, line):
        self.stack_clear()

    block_list = r"""
        (?P<list>
            ^ \s* [*\#][^*\#].* $
        )
    """
    # Matches the beginning of a list. All lines within a list are handled by
    # list_*.

    def block_list_repl(self, iter_content, list):
        iter_content.push(list)

        for line in iter_content:
            match = self.list_re.match(line)
            self._apply(match, 'list', iter_content)

            if match.group('end') is not None:
                # Allow the mainloop to take care of the line after a list.
                iter_content.push(line)
                break

    block_macro = r"""
        ^
        \s*?
        (?P<macro>
            <<
            (?P<macro_name> \w+)
            (\( (?P<macro_args> .*?) \))? \s*
            ([|] \s* (?P<macro_text> .+?) \s* )?
            >>
        )
        \s*?
        $
    """

    def block_macro_repl(self, _iter_content, macro, macro_name,
            macro_args=u''):
        """Handles macros using the placeholder syntax."""
        self.stack_clear()

        elem = self.macro(macro_name, macro_args, macro, 'block')
        if elem:
            self.stack_top_append(elem)

    block_nowiki = r"""
        (?P<nowiki>
            ^{{{ \s* $
        )
    """
    # Matches the beginning of a nowiki block

    nowiki_end = r"""
        ^ (?P<escape> ~ )? (?P<rest> }}} \s* ) $
    """
    # Matches the possibly escaped end of a nowiki block

    def block_nowiki_lines(self, iter_content):
        "Unescaping generator for the lines in a nowiki block"

        for line in iter_content:
            match = self.nowiki_end_re.match(line)
            if match:
                if not match.group('escape'):
                    return
                line = match.group('rest')
            yield line

    def block_nowiki_repl(self, iter_content, nowiki):
        "Handles a complete nowiki block"

        self.stack_clear()

        try:
            firstline = iter_content.next()
        except StopIteration:
            self.stack_push(ET.Element(self.tag_blockcode))
            return

        # Stop directly if we got an end marker in the first line
        match = self.nowiki_end_re.match(firstline)
        if match and not match.group('escape'):
            self.stack_push(ET.Element(self.tag_blockcode))
            return

        lines = _Iter(self.block_nowiki_lines(iter_content))

        if firstline.startswith('#!'):
            args = wikiutil.parse_quoted_separated(
                    firstline[2:].strip(), separator=None)
            name = args[0].pop(0)

            # Parse it directly if the type is ourself
            if name in ('creole', ):
                attrib = {}

                for key, value in args[1].iteritems():
                    if key in ('background-color', 'color'):
                        attrib[ET.QName(key, moin_page.namespace)] = value

                self.stack_push(moin_page.page(attrib))

                for line in lines:
                    match = self.block_re.match(line)
                    self._apply(match, 'block', lines)

                self.stack_clear()
                self.stack_pop()

            else:
                from MoinMoin.converter2 import default_registry as reg

                mimetype = wikiutil.MimeType(name).mime_type()
                converter = reg.get(self.request, mimetype, 'application/x-moin-document')

                elem = ET.Element(self.tag_div)
                self.stack_top_append(elem)

                doc = converter(self.request, self.page_url, ' '.join(args[0]))(lines)
                elem.extend(doc)

        else:
            elem = ET.Element(self.tag_blockcode, children=[firstline])
            self.stack_top_append(elem)

            for line in lines:
                elem.append('\n')
                elem.append(line)

    block_separator = r'(?P<separator> ^ \s* ---- \s* $ )'

    def block_separator_repl(self, _iter_content, separator):
        self.stack_clear()
        self.stack_top_append(ET.Element(self.tag_separator))

    block_table = r"""
        (?P<table>
            ^ \s* \| .* $
        )
    """

    def block_table_repl(self, iter_content, table):
        self.stack_clear()

        element = ET.Element(self.tag_table)
        self.stack_push(element)
        element = ET.Element(self.tag_table_body)
        self.stack_push(element)

        self.block_table_row(table)

        for line in iter_content:
            match = self.table_re.match(line)
            if not match:
                # Allow the mainloop to take care of the line after a list.
                iter_content.push(line)
                break

            self.block_table_row(match.group('table'))

        self.stack_clear()

    def block_table_row(self, content):
        element = ET.Element(self.tag_table_row)
        self.stack_push(element)

        for match in self.tablerow_re.finditer(content):
            self._apply(match, 'tablerow')

        self.stack_pop()

    block_text = r'(?P<text> .+ )'

    def block_text_repl(self, _iter_content, text):
        if self.stack_top_check('table', 'table-body', 'list'):
            self.stack_clear()

        if self.stack_top_check('body'):
            element = ET.Element(self.tag_p)
            self.stack_push(element)
        # If we are in a paragraph already, don't loose the whitespace
        else:
            self.stack_top_append('\n')
        self.parse_inline(text)

    inline_emph = r'(?P<emph> (?<!:)// )'
    # there must be no : in front of the // avoids italic rendering in urls
    # with unknown protocols

    def inline_emph_repl(self, emph):
        if not self.stack_top_check('emphasis'):
            self.stack_push(ET.Element(self.tag_emphasis))
        else:
            self.stack_pop_name('emphasis')
            self.stack_pop()

    inline_strong = r'(?P<strong> \*\* )'

    def inline_strong_repl(self, strong):
        if not self.stack_top_check('strong'):
            self.stack_push(ET.Element(self.tag_strong))
        else:
            self.stack_pop_name('strong')
            self.stack_pop()

    inline_linebreak = r'(?P<linebreak> \\\\ )'

    def inline_linebreak_repl(self, linebreak):
        element = ET.Element(self.tag_line_break)
        self.stack_top_append(element)

    inline_escape = r'(?P<escape> ~ (?P<escaped_char>\S) )'

    def inline_escape_repl(self, escape, escaped_char):
        self.stack_top_append(escaped_char)

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
            ([|] \s* (?P<link_text>.+?) \s*)?
            \]\]
        )
    """

    def inline_link_repl(self, link, link_url=None, link_page=None, link_text=None):
        """Handle all kinds of links."""

        if link_page is not None:
            target = unicode(iri.Iri(scheme='wiki.local', path=link_page))
            text = link_page
        else:
            target = link_url
            text = link_url
        element = ET.Element(self.tag_a, attrib = {self.tag_href: target})
        self.stack_push(element)
        self.parse_inline(link_text or text, self.link_desc_re)
        self.stack_pop()

    inline_macro = r"""
        (?P<macro>
            <<
            (?P<macro_name> \w+)
            (\( (?P<macro_args> .*?) \))? \s*
            ([|] \s* (?P<macro_text> .+?) \s* )?
            >>
        )
    """

    def inline_macro_repl(self, macro, macro_name, macro_args=u''):
        """Handles macros using the placeholder syntax."""

        elem = self.macro(macro_name, macro_args, macro, 'inline')
        self.stack_top_append(elem)

    inline_nowiki = r"""
        (?P<nowiki>
            {{{
            (?P<nowiki_text>.*?}*)
            }}}
        )
    """

    def inline_nowiki_repl(self, nowiki, nowiki_text):
        self.stack_top_append(ET.Element(self.tag_code, children=[nowiki_text]))

    inline_object = r"""
        (?P<object>
            {{
            (?P<object_target>.+?) \s*
            ([|] \s* (?P<object_text>.+?) \s*)?
            }}
        )
    """

    def inline_object_repl(self, object, object_target, object_text=None):
        """Handles objects included in the page."""

        attrib = {self.tag_href: object_target}
        if object_text is not None:
            attrib[self.tag_alt] = object_text

        element = ET.Element(self.tag_object, attrib)
        self.stack_top_append(element)

    inline_url = r"""
        (?P<url>
            (^ | (?<=\s | [.,:;!?()/=]))
            (?P<escaped_url>~)?
            (?P<url_target>
                # TODO: config.url_schemas
                (http|https|ftp|nntp|news|mailto|telnet|file|irc):
                \S+?
            )
            ($ | (?=\s | [,.:;!?()] (\s | $)))
        )
    """

    def inline_url_repl(self, url, url_target, escaped_url=None):
        """Handle raw urls in text."""

        if not escaped_url:
            # this url is NOT escaped
            attrib = {self.tag_href: url_target}
            element = ET.Element(self.tag_a, attrib=attrib, children=[url_target])
            self.stack_top_append(element)
        else:
            # this url is escaped, we render it as text
            self.stack_top_append(url_target)

    list_end = r"""
        (?P<end>
            ^
            (
                # End the list on blank line,
                $
                |
                # heading,
                =
                |
                # table,
                \|
                |
                # and nowiki block
                {{{
            )
        )
    """
    # Matches a line which will end a list

    def list_end_repl(self, _iter_content, end):
        self.stack_clear()

    list_item = r"""
        (?P<item>
            ^ \s*
            (?P<item_head> [\#*]+) \s*
            (?P<item_text> .*?)
            $
        )
    """
    # Matches single list items

    def list_item_repl(self, _iter_content, item, item_head, item_text):
        list_level = len(item_head)
        list_type = item_head[-1]

        # Try to locate the list element which matches the requested level and
        # type.
        while True:
            cur = self.stack_top()
            if cur.tag.name == 'body':
                break
            if cur.tag.name == 'list-item-body':
                if list_level > cur.list_level:
                    break
            if cur.tag.name == 'list':
                if list_level >= cur.list_level and list_type == cur.list_type:
                    break
            self.stack_pop()

        if cur.tag.name != 'list':
            generate = list_type == '#' and 'ordered' or 'unordered'
            attrib = {moin_page.item_label_generate: generate}
            element = ET.Element(self.tag_list, attrib=attrib)
            element.list_level, element.list_type = list_level, list_type
            self.stack_push(element)

        element = ET.Element(self.tag_list_item)
        element_body = ET.Element(self.tag_list_item_body)
        element_body.list_level, element_body.list_type = list_level, list_type

        self.stack_push(element)
        self.stack_push(element_body)

        self.parse_inline(item_text)

    list_text = block_text

    list_text_repl = block_text_repl

    table = block_table

    tablerow = r"""
        (?P<cell>
            \|
            \s*
            (?P<cell_head> [=] )?
            (?P<cell_text> [^|]+ )
            \s*
        )
    """

    def tablerow_cell_repl(self, cell, cell_text, cell_head=None):
        element = ET.Element(self.tag_table_cell)
        self.stack_push(element)

        # TODO: How to handle table headings
        self.parse_inline(cell_text)

        self.stack_pop_name('table-cell')
        self.stack_pop()

    # Block elements
    block = (
        block_line,
        block_head,
        block_separator,
        block_macro,
        block_nowiki,
        block_list,
        block_table,
        block_text,
    )
    block_re = re.compile('|'.join(block), re.X | re.U)

    # Inline elements
    inline = (
        inline_url,
        inline_escape,
        inline_link,
        inline_macro,
        inline_nowiki,
        inline_object,
        inline_strong,
        inline_emph,
        inline_linebreak,
    )
    inline_re = re.compile('|'.join(inline), re.X | re.U)

    # Link description
    link_desc = (
        inline_object,
        inline_linebreak,
    )
    link_desc_re = re.compile('|'.join(link_desc), re.X | re.U)

    # List items
    list = (
        list_end,
        list_item,
        list_text,
    )
    list_re = re.compile('|'.join(list), re.X | re.U)

    # Nowiki end
    nowiki_end_re = re.compile(nowiki_end, re.X)

    # Table
    table_re = re.compile(table, re.X | re.U)

    # Table row
    tablerow_re = re.compile(tablerow, re.X | re.U)

    def stack_clear(self):
        del self._stack[1:]

    def stack_pop_name(self, *names):
        """
        Look up the tree to the first occurence
        of one of the listed kinds of nodes or root.
        Start at the node node.
        """
        while len(self._stack) > 1 and not self.stack_top_check(*names):
            self._stack.pop()

    def stack_pop(self):
        self._stack.pop()

    def stack_push(self, elem):
        self.stack_top_append(elem)
        self._stack.append(elem)

    def stack_top(self):
        return self._stack[-1]

    def stack_top_append(self, elem):
        self._stack[-1].append(elem)

    def stack_top_append_ifnotempty(self, elem):
        if elem:
            self.stack_top_append(elem)

    def stack_top_check(self, *names):
        """
        Checks if the name of the top of the stack matches the parameters.
        """
        tag = self._stack[-1].tag
        return tag.uri == moin_page.namespace and tag.name in names

    def _apply(self, match, prefix, *args):
        """
        Call the _repl method for the last matched group with the given prefix.
        """
        data = dict(((k, v) for k, v in match.groupdict().iteritems() if v is not None))
        getattr(self, '%s_%s_repl' % (prefix, match.lastgroup))(*args, **data)

    def macro_text(self, text):
        conv = self.__class__(self.request, None)
        conv._stack = [ET.Element(ET.QName(None))]
        conv.parse_inline(text)
        return conv._stack[0][:]

    def parse_inline(self, text, inline_re=inline_re):
        """Recognize inline elements within the given text"""

        pos = 0
        for match in inline_re.finditer(text):
            # Handle leading text
            self.stack_top_append_ifnotempty(text[pos:match.start()])
            pos = match.end()

            self._apply(match, 'inline')

        # Handle trailing text
        self.stack_top_append_ifnotempty(text[pos:])

from MoinMoin.converter2._registry import default_registry
default_registry.register(Converter.factory)
