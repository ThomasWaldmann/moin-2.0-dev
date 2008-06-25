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
    proto = r'http|https|ftp|nntp|news|mailto|telnet|file|irc'
    url =  r'''(?P<url>
            (^ | (?<=\s | [.,:;!?()/=]))
            (?P<escaped_url>~)?
            (?P<url_target> (?P<url_proto> %s ):\S+? )
            ($ | (?=\s | [,.:;!?()] (\s | $)))
        )''' % proto
    link = r'''(?P<link>
            \[\[
            (?P<link_target>.+?) \s*
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
    code = r'(?P<code> {{{ (?P<code_text>.*?) }}} )'
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
    pre = r'''(?P<pre>
            ^{{{ \s* $
            (\n)?
            (?P<pre_text>
                ([\#]!(?P<pre_kind>\w*?)(\s+.*)?$)?
                (.|\n)+?
            )
            (\n)?
            ^}}} \s*$
        )'''
    pre_escape = r' ^(?P<indent>\s*) ~ (?P<rest> \}\}\} \s*) $'
    table = r'''(?P<table>
            ^ \s*
            [|].*? \s*
            [|]? \s*
            $
        )'''

    # For splitting table cells:
    cell = r'''
            \| \s*
            (
                (?P<head> [=][^|]+ ) |
                (?P<cell> (  %s | [^|])+ )
            ) \s*
        ''' % '|'.join([link, macro, image, code])

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
        Rules.pre, Rules.list, Rules.table, Rules.text_block]), re.X | re.U | re.M)
    # For inline elements:
    inline_re = re.compile('|'.join([Rules.link, Rules.url, Rules.macro,
        Rules.code, Rules.image, Rules.strong, Rules.emph, Rules.linebreak,
        Rules.escape, Rules.text_inline]), re.X | re.U | re.DOTALL)

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

    def _url_repl(self, url, url_proto, url_target, escaped_url=None):
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

    def _link_repl(self, link, link_target, link_text=''):
        """Handle all kinds of links."""

        # TODO: Convert into URI
        text = link_text.strip()
        tag = ElementTree.QName('a', namespaces.moin_page)
        tag_href = ElementTree.QName('href', namespaces.xlink)
        element = ElementTree.Element(tag, attrib = {tag_href: link_target})
        self._stack_push(element)
        self._apply(self.link_re, text)
        self._stack_pop()

    def _macro_repl(self, groups):
        """Handles macros using the placeholder syntax."""

        name = groups.get('macro_name', '')
        text = (groups.get('macro_text', '') or '').strip()
        node = DocNode('macro', self.cur, name)
        node.args = groups.get('macro_args', '') or ''
        DocNode('text', node, text or name)
        self.text = None

    def _image_repl(self, groups):
        """Handles images and attachemnts included in the page."""

        target = groups.get('image_target', '').strip()
        text = (groups.get('image_text', '') or '').strip()
        node = DocNode("image", self.cur, target)
        DocNode('text', node, text or node.content)
        self.text = None

    def _separator_repl(self, groups):
        self._stack_pop_name(('page', 'blockquote'))
        DocNode('separator', self.cur)

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
        if self._stack[-1].tag.name in ('table', 'table_row', 'bullet_list',
            'number_list'):
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

    def _table_repl(self, groups):
        row = groups.get('table', '|').strip()
        self._stack_pop_name(('table', 'page', 'blockquote'))
        if self.cur.kind != 'table':
            self.cur = DocNode('table', self.cur)
        tb = self.cur
        tr = DocNode('table_row', tb)

        for m in self.cell_re.finditer(row):
            cell = m.group('cell')
            if cell:
                self.cur = DocNode('table_cell', tr)
                self.text = None
                self.parse_inline(cell)
            else:
                cell = m.group('head')
                self.cur = DocNode('table_head', tr)
                self.text = DocNode('text', self.cur, u'')
                self.text.content = cell.strip('=')
        self.cur = tb
        self.text = None

    def _pre_repl(self, groups):
        self._stack_pop_name(('page', 'blockquote'))
        kind = groups.get('pre_kind', None)
        text = groups.get('pre_text', u'')
        def remove_tilde(m):
            return m.group('indent') + m.group('rest')
        text = self.pre_escape_re.sub(remove_tilde, text)
        node = DocNode('preformatted', self.cur, text)
        node.sect = kind or ''
        self.text = None

    def _line_repl(self, line):
        self._stack_pop_name(('page', 'blockquote'))
        self.text = None

    def _code_repl(self, groups):
        DocNode('code', self.cur, groups.get('code_text', u'').strip())
        self.text = None

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

    def _escape_repl(self, groups):
        if self.text is None:
            self.text = DocNode('text', self.cur, u'')
        self.text.content += groups.get('escaped_char', u'')

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

