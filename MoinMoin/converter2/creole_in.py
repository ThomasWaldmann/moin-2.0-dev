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
                2008 MoinMoin:BastianBlank (converter interface)
    @license: GNU GPL, see COPYING for details.
"""

import re
from emeraldtree import ElementTree as ET

from MoinMoin.util import namespaces
from MoinMoin.converter2._wiki_macro import ConverterMacro

class Converter(ConverterMacro):
    """
    Parse the raw text and create a document object
    that can be converted into output using Emitter.
    """

    @classmethod
    def _factory(cls, input, output):
        if input == 'text/creole' and output == 'application/x-moin-document':
            return cls

    def __init__(self, request, page_name=None, args=None):
        super(Converter, self).__init__(request)
        self.page_name = page_name

    def __call__(self, text):
        tag = ET.QName('page', namespaces.moin_page)
        tag_page_href = ET.QName('page-href', namespaces.moin_page)

        attrib = {}
        if self.page_name is not None:
            attrib[tag_page_href] = 'wiki:///' + self.page_name

        self.root = ET.Element(tag, attrib=attrib)
        self._stack = [self.root]
        self.parse_block(text)
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

    def block_head_repl(self, head, head_head, head_text):
        self._stack_pop_name(('page', 'blockquote'))
        level = len(head_head)

        tag = ET.QName('h', namespaces.moin_page)
        tag_level = ET.QName('outline-level', namespaces.moin_page)
        element = ET.Element(tag, attrib = {tag_level: str(level)}, children = [head_text])
        self._stack_top_append(element)

    block_line = r'(?P<line> ^ \s* $ )'
    # empty line that separates paragraphs

    def block_line_repl(self, line):
        self._stack_pop_name(('page', 'blockquote'))

    block_list = r"""
        (?P<list>
            ^ [ \t]* ([*][^*\#]|[\#][^\#*]).* $
            ( \n[ \t]* [*\#]+.* $ )*
        )
    """
    # Matches the whole list, separate items are parsed later. The list *must*
    # start with a single bullet.

    def block_list_repl(self, list):
        self._apply(self.list_item_re, 'list', list)

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

    def block_macro_repl(self, macro, macro_name, macro_args=''):
        """Handles macros using the placeholder syntax."""

        self._stack_pop_name(('page', 'blockquote'))
        elem = self.macro(macro_name, macro_args, macro, 'block')
        if elem:
            self._stack_top_append(elem)

    block_nowiki = r"""
        (?P<nowiki>
            ^{{{ \s* $
            (\n)?
            ([\#]!\ *(?P<nowiki_kind>\w*)(\ +[^\n]*)?\n)?
            (?P<nowiki_text>
                (.|\n)+?
            )
            (\n)?
            ^}}} \s*$
        )
    """

    def block_nowiki_repl(self, nowiki, nowiki_text, nowiki_kind=None):
        self._stack_pop_name(('page', 'blockquote'))

        def remove_tilde(m):
            return m.group('indent') + m.group('rest')

        if nowiki_kind:
            # TODO: move somewhere else
            from MoinMoin import wikiutil
            from MoinMoin.converter2 import default_registry as reg

            mimetype = wikiutil.MimeType(nowikiblock_kind).mime_type()
            Converter = reg.get(mimetype, 'application/x-moin-document', None)

            if Converter:
                self._stack_push(ET.Element(ET.QName('div', namespaces.moin_page)))

                doc = Converter(self.request, self.page_name)(nowiki_text)
                self._stack_top_append(doc)

            else:
                # TODO: warning
                pass

        else:
            text = self.nowiki_escape_re.sub(remove_tilde, nowiki_text)
            tag = ET.QName('blockcode', namespaces.moin_page)
            self._stack_top_append(ET.Element(tag, children=[text]))

    block_separator = r'(?P<separator> ^ \s* ---- \s* $ )'

    def block_separator_repl(self, separator):
        self._stack_pop_name(('page', 'blockquote'))
        tag = ET.QName('separator', namespaces.moin_page)
        self._stack_top_append(ET.Element(tag))

    block_table = r"""
        (?P<table>
            ^ \s*?
            [|].*? \s*?
            [|]? \s*?
            $
        )
    """

    def block_table_repl(self, table):
        self._stack_pop_name(('table-body', 'page', 'blockquote'))

        if self._stack[-1].tag.name != 'table-body':
            tag = ET.QName('table', namespaces.moin_page)
            element = ET.Element(tag)
            self._stack_push(element)
            tag = ET.QName('table-body', namespaces.moin_page)
            element = ET.Element(tag)
            self._stack_push(element)

        tag = ET.QName('table-row', namespaces.moin_page)
        element = ET.Element(tag)
        self._stack_push(element)

        for m in self.table_cell_re.finditer(table):
            cell = m.group('cell')
            if cell:
                tag = ET.QName('table-cell', namespaces.moin_page)
                element = ET.Element(tag)
                self._stack_push(element)

                self.parse_inline(cell)

                self._stack_pop()
            else:
                cell = m.group('head')
                # TODO: How to handle table headings
                tag = ET.QName('table-cell', namespaces.moin_page)
                element = ET.Element(tag, children=[cell.strip('=')])
                self._stack_top_append(element)

        self._stack_pop()

    block_text = r'(?P<text> (?P<text_newline>(?<=\n))? .+ )'

    def block_text_repl(self, text, text_newline=None):
        if self._stack[-1].tag.name in ('table', 'table-body', 'list'):
            self._stack_pop_name(('page', 'blockquote'))
        if self._stack[-1].tag.name in ('page', 'blockquote'):
            tag = ET.QName('p', namespaces.moin_page)
            element = ET.Element(tag)
            self._stack_push(element)
        # If we are in a paragraph already, don't loose the whitespace
        elif text_newline is not None:
            self._stack_top_append('\n')
        self.parse_inline(text)

    inline_text = r'(?P<text> .+? )'

    def inline_text_repl(self, text):
        self._stack_top_append(text)

    inline_emph = r'(?P<emph> (?<!:)// )'
    # there must be no : in front of the // avoids italic rendering in urls
    # with unknown protocols

    def inline_emph_repl(self, emph):
        if not self._stack_top_check(('emphasis', )):
            tag = ET.QName('emphasis', namespaces.moin_page)
            self._stack_push(ET.Element(tag))
        else:
            self._stack_pop_name(('emphasis', ))
            self._stack_pop()

    inline_strong = r'(?P<strong> \*\* )'

    def inline_strong_repl(self, strong):
        if not self._stack_top_check(('strong', )):
            tag = ET.QName('strong', namespaces.moin_page)
            self._stack_push(ET.Element(tag))
        else:
            self._stack_pop_name(('strong', ))
            self._stack_pop()

    inline_linebreak = r'(?P<linebreak> \\\\ )'

    def inline_linebreak_repl(self, linebreak):
        tag = ET.QName('line-break', namespaces.moin_page)
        element = ET.Element(tag)
        self._stack_top_append(element)

    inline_escape = r'(?P<escape> ~ (?P<escaped_char>\S) )'

    def inline_escape_repl(self, escape, escaped_char):
        self._stack_top_append(escaped_char)

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
            target = 'wiki.local:' + link_page
            text = link_page
        else:
            target = link_url
            text = link_url
        tag = ET.QName('a', namespaces.moin_page)
        tag_href = ET.QName('href', namespaces.xlink)
        element = ET.Element(tag, attrib = {tag_href: target})
        self._stack_push(element)
        self._apply(self.link_desc_re, 'inline', link_text or text)
        self._stack_pop()

    inline_macro = r"""
        (?P<macro>
            <<
            (?P<macro_name> \w+)
            (\( (?P<macro_args> .*?) \))? \s*
            ([|] \s* (?P<macro_text> .+?) \s* )?
            >>
        )
    """

    def inline_macro_repl(self, macro, macro_name, macro_args=''):
        """Handles macros using the placeholder syntax."""

        elem = self.macro(macro_name, macro_args, macro, 'inline')
        self._stack_top_append(elem)

    inline_nowiki = r"""
        (?P<nowiki>
            {{{
            (?P<nowiki_text>.*?}*)
            }}}
        )
    """

    def inline_nowiki_repl(self, nowiki, nowiki_text):
        tag = ET.QName('code', namespaces.moin_page)
        self._stack_top_append(ET.Element(tag, children=[nowiki_text]))

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
        self._stack_top_append(element)

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
            self._stack_top_append(element)
        else:
            # this url is escaped, we render it as text
            self._stack_top_append(url_target)

    list_item = r"""
        (?P<item>
            ^ \s*
            (?P<item_head> [\#*]+) \s*
            (?P<item_text> .*?)
            $
        )
    """
    # Matches single list items

    def list_item_repl(self, item, item_head, item_text):
        level = len(item_head)
        type = item_head[-1]

        while True:
            cur = self._stack[-1]
            if cur.tag.name in ('page', 'blockquote'):
                break
            if cur.tag.name == 'list-item-body':
                if level > cur.level:
                    break
            if cur.tag.name == 'list':
                if level >= cur.level and type == cur.type:
                    break
            self._stack.pop()

        if cur.tag.name != 'list':
            tag = ET.QName('list', namespaces.moin_page)
            tag_generate = ET.QName('item-label-generate', namespaces.moin_page)
            generate = type == '#' and 'ordered' or 'unordered'
            attrib = {tag_generate: generate}
            element = ET.Element(tag, attrib=attrib)
            element.level, element.type = level, type
            self._stack_push(element)

        tag = ET.QName('list-item', namespaces.moin_page)
        tag_body = ET.QName('list-item-body', namespaces.moin_page)
        element = ET.Element(tag)
        element_body = ET.Element(tag_body)
        element_body.level, element_body.type = level, type

        self._stack_push(element)
        self._stack_push(element_body)

        self.parse_inline(item_text)

    nowiki_escape = r' ^(?P<indent>\s*) ~ (?P<rest> \}\}\} \s*) $'

    table_cell = r"""
        \| \s*
        (
            (?P<head> [=][^|]+ ) |
            (?P<cell> (  %s | [^|])+ )
        ) \s*
    """ % '|'.join([inline_link, inline_macro, inline_object, inline_nowiki])

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
    block_re = re.compile('|'.join(block), re.X | re.U | re.M)

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
    inline_re = re.compile('|'.join(inline), re.X | re.U | re.DOTALL)

    # Link description
    link_desc = (
        inline_object,
        inline_linebreak,
        inline_text,
    )
    link_desc_re = re.compile('|'.join(link_desc), re.X | re.U | re.DOTALL)

    # Nowiki escape
    nowiki_escape_re = re.compile(nowiki_escape, re.M | re.X)

    # List items
    list_item_re = re.compile(list_item, re.X | re.U | re.M)

    # Table cells
    table_cell_re = re.compile(table_cell, re.X | re.U)

    def _stack_pop_name(self, tags):
        """
        Look up the tree to the first occurence
        of one of the listed kinds of nodes or root.
        Start at the node node.
        """
        while len(self._stack) > 1 and self._stack[-1].tag.name not in tags:
            self._stack.pop()

    def _stack_pop(self):
        self._stack.pop()

    def _stack_push(self, elem):
        self._stack_top_append(elem)
        self._stack.append(elem)

    def _stack_top_append(self, elem):
        self._stack[-1].append(elem)

    def _stack_top_check(self, names):
        tag = self._stack[-1].tag
        return tag.uri == namespaces.moin_page and tag.name in names

    def _apply(self, re, prefix, text):
        """Invoke appropriate _*_repl method for every match"""

        for match in re.finditer(text):
            data = dict(((k, v) for k, v in match.groupdict().iteritems() if v is not None))
            getattr(self, '%s_%s_repl' % (prefix, match.lastgroup))(**data)

    def macro_text(self, text):
        conv = self.__class__(self.request, None)
        conv._stack = [ET.Element(ET.QName(None))]
        conv.parse_inline(text)
        return conv._stack[0][:]

    def parse_inline(self, raw):
        """Recognize inline elements inside blocks."""

        self._apply(self.inline_re, 'inline', raw)

    def parse_block(self, raw):
        """Recognize block elements."""

        self._apply(self.block_re, 'block', raw)

from _registry import default_registry
default_registry.register(Converter._factory)
