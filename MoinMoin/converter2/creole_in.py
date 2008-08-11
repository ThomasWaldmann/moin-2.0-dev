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
from MoinMoin.util import namespaces, uri
from MoinMoin.converter2._wiki_macro import ConverterMacro

class _Iter(object):
    """
    Iterator with push back support

    Collected items can be pushed back into the iterator and further calls will
    return them.
    """

    def __init__(self, input):
        self.__finished = False
        self.__input = iter(input)
        self.__prepend = []

    def __iter__(self):
        return self

    def next(self):
        if self.__finished:
            raise StopIteration

        if self.__prepend:
            return self.__prepend.pop(0)

        try:
            return self.__input.next()
        except StopIteration:
            self.__finished = True
            raise

    def push(self, item):
        self.__prepend.append(item)

class Converter(ConverterMacro):
    tag_blockcode = ET.QName('blockcode', namespaces.moin_page)
    tag_page = ET.QName('page', namespaces.moin_page)

    @classmethod
    def _factory(cls, request, input, output):
        if input == 'text/creole' and output == 'application/x-moin-document':
            return cls

    def __init__(self, request, page_url=None, args=None):
        super(Converter, self).__init__(request)
        self.page_url = page_url

    def __call__(self, content):
        tag = ET.QName('page', namespaces.moin_page)
        tag_page_href = ET.QName('page-href', namespaces.moin_page)

        attrib = {}
        if self.page_url:
            attrib[tag_page_href] = self.page_url

        self.root = ET.Element(tag, attrib=attrib)
        self._stack = [self.root]
        iter = _Iter(content)

        # Please note that the iterator can be modified by other functions
        for line in iter:
            match = self.block_re.match(line)
            self._apply(match, 'block', iter)

        return self.root

    block_head = r"""
        (?P<head>
            ^ \s*
            (?P<head_head>=+) \s*
            (?P<head_text> .*? ) \s*
            =* \s*
            $
        )
    """

    def block_head_repl(self, iter, head, head_head, head_text):
        self.stack_pop_name('page')
        level = len(head_head)

        tag = ET.QName('h', namespaces.moin_page)
        tag_level = ET.QName('outline-level', namespaces.moin_page)
        element = ET.Element(tag, attrib = {tag_level: str(level)}, children = [head_text])
        self.stack_top_append(element)

    block_line = r'(?P<line> ^ \s* $ )'
    # empty line that separates paragraphs

    def block_line_repl(self, iter, line):
        self.stack_pop_name('page')

    block_list = r"""
        (?P<list>
            ^ \s* [*\#][^*\#].* $
        )
    """
    # Matches the beginning of a list. All lines within a list are handled by
    # list_*.

    def block_list_repl(self, iter, list):
        iter.push(list)

        for line in iter:
            match = self.list_re.match(line)
            self._apply(match, 'list', iter)

            if match.group('end') is not None:
                # Allow the mainloop to take care of the line after a list.
                iter.push(line)
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

    def block_macro_repl(self, iter, macro, macro_name, macro_args=u''):
        """Handles macros using the placeholder syntax."""

        self.stack_pop_name('page')
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

    def block_nowiki_lines(self, iter):
        "Unescaping generator for the lines in a nowiki block"

        for line in iter:
            match = self.nowiki_end_re.match(line)
            if match:
                if not match.group('escape'):
                    return
                line = match.group('rest')
            yield line

    def block_nowiki_repl(self, iter, nowiki):
        "Handles a complete nowiki block"

        self.stack_pop_name('page')

        try:
            firstline = iter.next()
        except StopIteration:
            self.stack_push(ET.Element(self.tag_blockcode))
            return

        # Stop directly if we got an end marker in the first line
        match = self.nowiki_end_re.match(firstline)
        if match and not match.group('escape'):
            self.stack_push(ET.Element(self.tag_blockcode))
            return

        lines = _Iter(self.block_nowiki_lines(iter))

        if firstline.startswith('#!'):
            args = wikiutil.parse_quoted_separated(firstline[2:], separator=None)
            name = args[0].pop(0)

            # Parse it directly if the type is ourself
            if name in ('creole', ):
                attrib = {}

                for key, value in args[1].iteritems():
                    if key in ('background-color', 'color'):
                        attrib[ET.QName(key, namespaces.moin_page)] = value

                self.stack_push(ET.Element(self.tag_page, attrib))

                for line in lines:
                    match = self.block_re.match(line)
                    self._apply(match, 'block', lines)

                self.stack_pop_name('page')
                self.stack_pop()

            else:
                from MoinMoin.converter2 import default_registry as reg

                mimetype = wikiutil.MimeType(name).mime_type()
                Converter = reg.get(self.request, mimetype, 'application/x-moin-document')

                elem = ET.Element(ET.QName('div', namespaces.moin_page))
                self.stack_top_append(elem)

                doc = Converter(self.request, self.page_url, ' '.join(args[0]))(lines)
                elem.extend(doc)

        else:
            elem = ET.Element(self.tag_blockcode, children=[firstline])
            self.stack_top_append(elem)

            for line in self.block_nowiki_lines(iter):
                elem.append('\n')
                elem.append(line)

    block_separator = r'(?P<separator> ^ \s* ---- \s* $ )'

    def block_separator_repl(self, iter, separator):
        self.stack_pop_name('page')
        tag = ET.QName('separator', namespaces.moin_page)
        self.stack_top_append(ET.Element(tag))

    block_table = r"""
        (?P<table>
            ^ \s* \| .* $
        )
    """

    def block_table_repl(self, iter, table):
        self.stack_pop_name('page')

        tag = ET.QName('table', namespaces.moin_page)
        element = ET.Element(tag)
        self.stack_push(element)
        tag = ET.QName('table-body', namespaces.moin_page)
        element = ET.Element(tag)
        self.stack_push(element)

        self.block_table_row(table)

        for line in iter:
            match = self.table_re.match(line)
            if not match:
                # Allow the mainloop to take care of the line after a list.
                iter.push(line)
                break

            self.block_table_row(match.group('table'))

        self.stack_pop_name('page')

    def block_table_row(self, content):
        tag = ET.QName('table-row', namespaces.moin_page)
        element = ET.Element(tag)
        self.stack_push(element)

        for match in self.tablerow_re.finditer(content):
            self._apply(match, 'tablerow')

        self.stack_pop()

    block_text = r'(?P<text> .+ )'

    def block_text_repl(self, iter, text):
        if self.stack_top_check('table', 'table-body', 'list'):
            self.stack_pop_name('page')

        if self.stack_top_check('page'):
            tag = ET.QName('p', namespaces.moin_page)
            element = ET.Element(tag)
            self.stack_push(element)
        # If we are in a paragraph already, don't loose the whitespace
        else:
            self.stack_top_append('\n')
        self.parse_inline(text)

    inline_text = r'(?P<text> .+? )'

    def inline_text_repl(self, text):
        self.stack_top_append(text)

    inline_emph = r'(?P<emph> (?<!:)// )'
    # there must be no : in front of the // avoids italic rendering in urls
    # with unknown protocols

    def inline_emph_repl(self, emph):
        if not self.stack_top_check('emphasis'):
            tag = ET.QName('emphasis', namespaces.moin_page)
            self.stack_push(ET.Element(tag))
        else:
            self.stack_pop_name('emphasis')
            self.stack_pop()

    inline_strong = r'(?P<strong> \*\* )'

    def inline_strong_repl(self, strong):
        if not self.stack_top_check('strong'):
            tag = ET.QName('strong', namespaces.moin_page)
            self.stack_push(ET.Element(tag))
        else:
            self.stack_pop_name('strong')
            self.stack_pop()

    inline_linebreak = r'(?P<linebreak> \\\\ )'

    def inline_linebreak_repl(self, linebreak):
        tag = ET.QName('line-break', namespaces.moin_page)
        element = ET.Element(tag)
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
                    [^|\]]+?
                )
                |
                (?P<link_page> [^|\]]+? )
            )
            \s*
            ([|] \s* (?P<link_text>.+?) \s*)?
            \]\]
        )
    """

    def inline_link_repl(self, link, link_url=None, link_page=None, link_text=None):
        """Handle all kinds of links."""

        if link_page is not None:
            # TODO: unicode URI
            target = str(uri.Uri(scheme='wiki.local', path=link_page.encode('utf-8')))
            text = link_page
        else:
            target = link_url
            text = link_url
        tag = ET.QName('a', namespaces.moin_page)
        tag_href = ET.QName('href', namespaces.xlink)
        element = ET.Element(tag, attrib = {tag_href: target})
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
        tag = ET.QName('code', namespaces.moin_page)
        self.stack_top_append(ET.Element(tag, children=[nowiki_text]))

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

        tag = ET.QName('object', namespaces.moin_page)
        tag_alt = ET.QName('alt', namespaces.moin_page)
        tag_href = ET.QName('href', namespaces.xlink)

        attrib = {tag_href: object_target}
        if object_text is not None:
            attrib[tag_alt] = object_text

        element = ET.Element(tag, attrib)
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
            tag = ET.QName('a', namespaces.moin_page)
            tag_href = ET.QName('href', namespaces.xlink)
            element = ET.Element(tag, attrib = {tag_href: url_target}, children = [url_target])
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

    def list_end_repl(self, iter, end):
        self.stack_pop_name('page')

    list_item = r"""
        (?P<item>
            ^ \s*
            (?P<item_head> [\#*]+) \s*
            (?P<item_text> .*?)
            $
        )
    """
    # Matches single list items

    def list_item_repl(self, iter, item, item_head, item_text):
        level = len(item_head)
        type = item_head[-1]

        # Try to locate the list element which matches the requested level and
        # type.
        while True:
            cur = self.stack_top()
            if cur.tag.name == 'page':
                break
            if cur.tag.name == 'list-item-body':
                if level > cur.level:
                    break
            if cur.tag.name == 'list':
                if level >= cur.level and type == cur.type:
                    break
            self.stack_pop()

        if cur.tag.name != 'list':
            tag = ET.QName('list', namespaces.moin_page)
            tag_generate = ET.QName('item-label-generate', namespaces.moin_page)
            generate = type == '#' and 'ordered' or 'unordered'
            attrib = {tag_generate: generate}
            element = ET.Element(tag, attrib=attrib)
            element.level, element.type = level, type
            self.stack_push(element)

        tag = ET.QName('list-item', namespaces.moin_page)
        tag_body = ET.QName('list-item-body', namespaces.moin_page)
        element = ET.Element(tag)
        element_body = ET.Element(tag_body)
        element_body.level, element_body.type = level, type

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
        tag = ET.QName('table-cell', namespaces.moin_page)
        element = ET.Element(tag)
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
        inline_link,
        inline_url,
        inline_macro,
        inline_nowiki,
        inline_object,
        inline_strong,
        inline_emph,
        inline_linebreak,
        inline_escape,
        inline_text,
    )
    inline_re = re.compile('|'.join(inline), re.X | re.U)

    # Link description
    link_desc = (
        inline_object,
        inline_linebreak,
        inline_text,
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

    def stack_top_check(self, *names):
        tag = self._stack[-1].tag
        return tag.uri == namespaces.moin_page and tag.name in names

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

    def parse_inline(self, text, re=inline_re):
        """Recognize inline elements within the given text"""

        for match in re.finditer(text):
            self._apply(match, 'inline')

from _registry import default_registry
default_registry.register(Converter._factory)
