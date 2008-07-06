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
from emeraldtree import ElementTree

from MoinMoin.util import namespaces

class Rules:
    """Hold all the rules for generating regular expressions."""

    # For the inline elements:
    url =  r'''(?P<url>
            (^ | (?<=\s | [.,:;!?()/=]))
            (?P<escaped_url>~)?
            (?P<url_target>
                (http|https|ftp|nntp|news|mailto|telnet|file|irc):
                \S+?
            )
            ($ | (?=\s | [,.:;!?()] (\s | $)))
        )'''
    link = r'''(?P<link>
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
            ]]
        )'''
    image = r'''(?P<image>
            {{
            (?P<image_target>.+?) \s*
            ([|] \s* (?P<image_text>.+?) \s*)?
            }}
        )'''
    macro = r'''(?P<macro>
            <<
            (?P<macro_name> \w+)
            (\( (?P<macro_args> .*?) \))? \s*
            ([|] \s* (?P<macro_text> .+?) \s* )?
            >>
        )'''
    nowiki_inline = r'(?P<nowikiinline> {{{ (?P<nowikiinline_text>.*?}*) }}} )'
    emph = r'(?P<emph> (?<!:)// )' # there must be no : in front of the //
                                   # avoids italic rendering in urls with
                                   # unknown protocols
    strong = r'(?P<strong> \*\* )'
    linebreak = r'(?P<linebreak> \\\\ )'
    escape = r'(?P<escape> ~ (?P<escaped_char>\S) )'

    # For the block elements:
    separator = r'(?P<separator> ^ \s* ---- \s* $ )' # horizontal line
    line = r'(?P<line> ^ \s* $ )' # empty line that separates paragraphs
    head = r'''(?P<head>
            ^ \s*
            (?P<head_head>=+) \s*
            (?P<head_text> .*? ) \s*
            =* \s*
            $
        )'''
    text_block = r'(?P<textblock> (?P<testblock_newline>(?<=\n))? .+ )'
    text_inline =  r'(?P<textinline> .+? )'
    list = r'''(?P<list>
            ^ [ \t]* ([*][^*\#]|[\#][^\#*]).* $
            ( \n[ \t]* [*\#]+.* $ )*
        )''' # Matches the whole list, separate items are parsed later. The
             # list *must* start with a single bullet.
    item = r'''(?P<item>
            ^ \s*
            (?P<item_head> [\#*]+) \s*
            (?P<item_text> .*?)
            $
        )''' # Matches single list items
    nowiki_block = r'''(?P<nowikiblock>
            ^{{{ \s* $
            (\n)?
            (?P<nowikiblock_text>
                ([\#]!(?P<nowikiblock_kind>\w*?)(\s+.*)?$)?
                (.|\n)+?
            )
            (\n)?
            ^}}} \s*$
        )'''
    pre_escape = r' ^(?P<indent>\s*) ~ (?P<rest> \}\}\} \s*) $'
    table = r'''(?P<table>
            ^ \s*?
            [|].*? \s*?
            [|]? \s*?
            $
        )'''

    # For splitting table cells:
    cell = r'''
            \| \s*
            (
                (?P<head> [=][^|]+ ) |
                (?P<cell> (  %s | [^|])+ )
            ) \s*
        ''' % '|'.join([link, macro, image, nowiki_inline])

class Converter(object):
    """
    Parse the raw text and create a document object
    that can be converted into output using Emitter.
    """

    # For pre escaping, in creole 1.0 done with ~:
    pre_escape_re = re.compile(Rules.pre_escape, re.M | re.X)
    # for link descriptions
    link_re = re.compile('|'.join([Rules.image, Rules.linebreak, Rules.text_inline]),
        re.X | re.U | re.DOTALL)
    item_re = re.compile(Rules.item, re.X | re.U | re.M) # for list items
    cell_re = re.compile(Rules.cell, re.X | re.U) # for table cells
    # For block elements:
    block_re = re.compile('|'.join([Rules.line, Rules.head, Rules.separator,
        Rules.nowiki_block, Rules.list, Rules.table, Rules.text_block]), re.X | re.U | re.M)
    # For inline elements:
    inline_re = re.compile('|'.join([Rules.link, Rules.url, Rules.macro,
        Rules.nowiki_inline, Rules.image, Rules.strong, Rules.emph, Rules.linebreak,
        Rules.escape, Rules.text_inline]), re.X | re.U | re.DOTALL)

    @classmethod
    def _factory(cls, input, output):
        if input == 'text/creole' and output == 'application/x-moin-document':
            return cls()

    def __call__(self, text):
        """Parse the text given as self.raw and return DOM tree."""

        self.root = ElementTree.Element(ElementTree.QName('page', namespaces.moin_page))
        # The most recent document node
        self._stack = [self.root]
        # The node to add inline characters to
        self.text = None
        self.parse_block(text)
        return self.root

    # The _*_repl methods called for matches in regexps. Sometimes the
    # same method needs several names, because of group names in regexps.

    def _url_repl(self, url, url_target, escaped_url=None):
        """Handle raw urls in text."""

        if not escaped_url:
            # this url is NOT escaped
            tag = ElementTree.QName('a', namespaces.moin_page)
            tag_href = ElementTree.QName('href', namespaces.xlink)
            element = ElementTree.Element(tag, attrib = {tag_href: url_target}, children = [url_target])
            self._stack_top_append(element)
        else:
            # this url is escaped, we render it as text
            self._stack_top_append(url_target)

    def _link_repl(self, link, link_url=None, link_page=None, link_text=None):
        """Handle all kinds of links."""

        if link_page is not None:
            target = 'wiki.local:' + link_page
            text = link_page
        else:
            target = link_url
            text = link_url
        tag = ElementTree.QName('a', namespaces.moin_page)
        tag_href = ElementTree.QName('href', namespaces.xlink)
        element = ElementTree.Element(tag, attrib = {tag_href: target})
        self._stack_push(element)
        self._apply(self.link_re, link_text or text)
        self._stack_pop()

    def _macro_repl(self, macro, macro_name, macro_args=None):
        """Handles macros using the placeholder syntax."""

        # TODO: other namespace?
        tag = ElementTree.QName('macro', namespaces.moin_page)
        tag_name = ElementTree.QName('macro-name', namespaces.moin_page)
        tag_args = ElementTree.QName('macro-args', namespaces.moin_page)
        attrib = {tag_name: macro_name}
        if macro_args is not None:
            attrib[tag_args] = macro_args
        self._stack_top_append(ElementTree.Element(tag, attrib))

    def _image_repl(self, image, image_target, image_text=None):
        """Handles images and attachemnts included in the page."""

        tag = ElementTree.QName('image', namespaces.moin_page)
        tag_alt = ElementTree.QName('alt', namespaces.moin_page)
        tag_href = ElementTree.QName('href', namespaces.xlink)

        attrib = {tag_href: image_target}
        if image_text is not None:
            attrib[tag_alt] = image_text

        element = ElementTree.Element(tag, attrib)
        self._stack_top_append(element)

    def _separator_repl(self, separator):
        self._stack_pop_name(('page', 'blockquote'))
        # TODO: questionable
        tag = ElementTree.QName('separator', namespaces.moin_page)
        self._stack_top_append(ElementTree.Element(tag))

    def _item_repl(self, item, item_head, item_text):
        # TODO: Mention type in the tree

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
            tag = ElementTree.QName('list', namespaces.moin_page)
            element = ElementTree.Element(tag)
            element.level, element.type = level, type
            self._stack_push(element)

        tag = ElementTree.QName('list-item', namespaces.moin_page)
        tag_body = ElementTree.QName('list-item-body', namespaces.moin_page)
        element = ElementTree.Element(tag)
        element_body = ElementTree.Element(tag_body)
        element_body.level, element_body.type = level, type

        self._stack_push(element)
        self._stack_push(element_body)

        self.parse_inline(item_text)

    def _list_repl(self, list):
        self._apply(self.item_re, list)

    def _head_repl(self, head, head_head, head_text):
        self._stack_pop_name(('page', 'blockquote'))
        level = len(head_head)

        tag = ElementTree.QName('h', namespaces.moin_page)
        tag_level = ElementTree.QName('outline-level', namespaces.moin_page)
        element = ElementTree.Element(tag, attrib = {tag_level: str(level)}, children = [head_text])
        self._stack_top_append(element)

    def _textblock_repl(self, textblock, testblock_newline=None):
        if self._stack[-1].tag.name in ('table', 'table-body', 'list'):
            self._stack_pop_name(('page', 'blockquote'))
        if self._stack[-1].tag.name in ('page', 'blockquote'):
            tag = ElementTree.QName('p', namespaces.moin_page)
            element = ElementTree.Element(tag)
            self._stack_push(element)
        # If we are in a paragraph already, don't loose the whitespace
        elif testblock_newline is not None:
            self._stack_top_append('\n')
        # TODO: This used to add a space after the text.
        self.parse_inline(textblock)

    def _table_repl(self, table):
        self._stack_pop_name(('table-body', 'page', 'blockquote'))

        if self._stack[-1].tag.name != 'table-body':
            tag = ElementTree.QName('table', namespaces.moin_page)
            element = ElementTree.Element(tag)
            self._stack_push(element)
            tag = ElementTree.QName('table-body', namespaces.moin_page)
            element = ElementTree.Element(tag)
            self._stack_push(element)

        tag = ElementTree.QName('table-row', namespaces.moin_page)
        element = ElementTree.Element(tag)
        self._stack_push(element)

        for m in self.cell_re.finditer(table):
            cell = m.group('cell')
            if cell:
                tag = ElementTree.QName('table-cell', namespaces.moin_page)
                element = ElementTree.Element(tag)
                self._stack_push(element)

                self.parse_inline(cell)

                self._stack_pop()
            else:
                cell = m.group('head')
                # TODO
                tag = ElementTree.QName('table-cell', namespaces.moin_page)
                element = ElementTree.Element(tag, children=[cell.strip('=')])
                self._stack_top_append(element)

        self._stack_pop()

    def _nowikiblock_repl(self, nowikiblock, nowikiblock_text, nowikiblock_kind=None):
        self._stack_pop_name(('page', 'blockquote'))
        def remove_tilde(m):
            return m.group('indent') + m.group('rest')
        text = self.pre_escape_re.sub(remove_tilde, nowikiblock_text)
        # TODO
        tag = ElementTree.QName('blockcode', namespaces.moin_page)
        self._stack_top_append(ElementTree.Element(tag, children=[text]))

    def _line_repl(self, line):
        self._stack_pop_name(('page', 'blockquote'))
        self.text = None

    def _nowikiinline_repl(self, nowikiinline, nowikiinline_text):
        # TODO
        tag = ElementTree.QName('code', namespaces.moin_page)
        self._stack_top_append(ElementTree.Element(tag, children=[nowikiinline_text]))

    def _emph_repl(self, emph):
        if not self._stack_top_check(('emphasis',)):
            tag = ElementTree.QName('emphasis', namespaces.moin_page)
            self._stack_push(ElementTree.Element(tag))
        else:
            self._stack_pop_name(('emphasis',))
            self._stack_pop()
        self.text = None

    def _strong_repl(self, strong):
        if not self._stack_top_check(('strong',)):
            tag = ElementTree.QName('strong', namespaces.moin_page)
            self._stack_push(ElementTree.Element(tag))
        else:
            self._stack_pop_name(('strong',))
            self._stack_pop()
        self.text = None

    def _linebreak_repl(self, linebreak):
        tag = ElementTree.QName('line-break', namespaces.moin_page)
        element = ElementTree.Element(tag)
        self._stack_top_append(element)

    def _escape_repl(self, escape, escaped_char):
        self._stack_top_append(escaped_char)

    def _textinline_repl(self, textinline):
        self._stack_top_append(textinline)

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

    def _apply(self, re, text):
        """Invoke appropriate _*_repl method for every match"""

        for match in re.finditer(text):
            data = dict(((k, v) for k, v in match.groupdict().iteritems() if v is not None))
            getattr(self, '_%s_repl' % match.lastgroup)(**data)

    def parse_inline(self, raw):
        """Recognize inline elements inside blocks."""

        self._apply(self.inline_re, raw)

    def parse_block(self, raw):
        """Recognize block elements."""

        self._apply(self.block_re, raw)

from _registry import default_registry
default_registry.register(Converter._factory)
