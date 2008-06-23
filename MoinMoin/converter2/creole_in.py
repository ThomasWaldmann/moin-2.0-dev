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
    @license: GNU GPL, see COPYING for details.
"""

import re
from emeraldtree import ElementTree

from MoinMoin.util import namespaces

# Whether the parser should convert \n into <br>.
bloglike_lines = False

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
    linebreak = r'(?P<break> \\\\ )'
    escape = r'(?P<escape> ~ (?P<escaped_char>\S) )'
    char =  r'(?P<char> . )'

    # For the block elements:
    separator = r'(?P<separator> ^ \s* ---- \s* $ )' # horizontal line
    line = r'(?P<line> ^ \s* $ )' # empty line that separates paragraphs
    head = r'''(?P<head>
            ^ \s*
            (?P<head_head>=+) \s*
            (?P<head_text> .*? ) \s*
            (?P<head_tail>=*) \s*
            $
        )'''
    if bloglike_lines:
        text = r'(?P<text> .+ ) (?P<break> (?<!\\)$\n(?!\s*$) )?'
    else:
        text = r'(?P<text> .+ )'
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
    link_re = re.compile('|'.join([Rules.image, Rules.linebreak, Rules.char]), re.X | re.U) # for link descriptions
    item_re = re.compile(Rules.item, re.X | re.U | re.M) # for list items
    cell_re = re.compile(Rules.cell, re.X | re.U) # for table cells
    # For block elements:
    block_re = re.compile('|'.join([Rules.line, Rules.head, Rules.separator,
        Rules.pre, Rules.list, Rules.table, Rules.text]), re.X | re.U | re.M)
    # For inline elements:
    inline_re = re.compile('|'.join([Rules.link, Rules.url, Rules.macro,
        Rules.code, Rules.image, Rules.strong, Rules.emph, Rules.linebreak,
        Rules.escape, Rules.char]), re.X | re.U)

    namespace = namespaces.moin_page

    def __call__(self, text):
        """Parse the text given as self.raw and return DOM tree."""

        self.root = ElementTree.Element(ElementTree.QName('page', self.namespace))
        # The most recent document node
        self._stack = [self.root]
        # The node to add inline characters to
        self.text = None
        self.parse_block(text)
        return self.root

    # The _*_repl methods called for matches in regexps. Sometimes the
    # same method needs several names, because of group names in regexps.

    def _url_repl(self, groups):
        """Handle raw urls in text."""

        if not groups.get('escaped_url'):
            # this url is NOT escaped
            target = groups.get('url_target', '')
            node = DocNode('link', self.cur)
            node.content = target
            DocNode('text', node, node.content)
            self.text = None
        else:
            # this url is escaped, we render it as text
            if self.text is None:
                self.text = DocNode('text', self.cur, u'')
            self.text.content += groups.get('url_target')
    _url_target_repl = _url_repl
    _url_proto_repl = _url_repl
    _escaped_url = _url_repl

    def _link_repl(self, groups):
        """Handle all kinds of links."""

        target = groups.get('link_target', '')
        text = (groups.get('link_text', '') or '').strip()
        parent = self.cur
        self.cur = DocNode('link', self.cur)
        self.cur.content = target
        self.text = None
        re.sub(self.link_re, self._replace, text)
        self.cur = parent
        self.text = None
    _link_target_repl = _link_repl
    _link_text_repl = _link_repl

    def _macro_repl(self, groups):
        """Handles macros using the placeholder syntax."""

        name = groups.get('macro_name', '')
        text = (groups.get('macro_text', '') or '').strip()
        node = DocNode('macro', self.cur, name)
        node.args = groups.get('macro_args', '') or ''
        DocNode('text', node, text or name)
        self.text = None
    _macro_name_repl = _macro_repl
    _macro_args_repl = _macro_repl
    _macro_text_repl = _macro_repl

    def _image_repl(self, groups):
        """Handles images and attachemnts included in the page."""

        target = groups.get('image_target', '').strip()
        text = (groups.get('image_text', '') or '').strip()
        node = DocNode("image", self.cur, target)
        DocNode('text', node, text or node.content)
        self.text = None
    _image_target_repl = _image_repl
    _image_text_repl = _image_repl

    def _separator_repl(self, groups):
        self._stack_pop_name(('page', 'blockquote'))
        DocNode('separator', self.cur)

    def _item_repl(self, groups):
        bullet = groups.get('item_head', u'')
        text = groups.get('item_text', u'')
        if bullet[-1] == '#':
            kind = 'number_list'
        else:
            kind = 'bullet_list'
        level = len(bullet)
        lst = self.cur
        # Find a list of the same kind and level up the tree
        while (lst and
                   not (lst.kind in ('number_list', 'bullet_list') and
                        lst.level == level) and
                    not lst.kind in ('page', 'blockquote')):
            lst = lst.parent
        if lst and lst.kind == kind:
            self.cur = lst
        else:
            # Create a new level of list
            self._stack_pop_name(('list_item', 'page', 'blockquote'))
            self.cur = DocNode(kind, self.cur)
            self.cur.level = level
        self.cur = DocNode('list_item', self.cur)
        self.parse_inline(text)
        self.text = None
    _item_text_repl = _item_repl
    _item_head_repl = _item_repl

    def _list_repl(self, groups):
        text = groups.get('list', u'')
        self.item_re.sub(self._replace, text)

    def _head_repl(self, groups):
        self._stack_pop_name(('page', 'blockquote'))
        level = len(groups.get('head_head', ' '))
        text = groups.get('head_text', '').strip()

        tag = ElementTree.QName('h', namespaces.moin_page)
        tag_level = ElementTree.QName('outline-level', namespaces.moin_page)
        element = ElementTree.Element(tag, attrib = {tag_level: str(level)}, children = [text])
        self._stack_top_append(element)
    _head_head_repl = _head_repl
    _head_text_repl = _head_repl

    def _text_repl(self, groups):
        if self._stack[-1].tag.name in ('table', 'table_row', 'bullet_list',
            'number_list'):
            self._stack_pop_name(('page', 'blockquote'))
        if self._stack[-1].tag.name in ('page', 'blockquote'):
            tag = ElementTree.QName('p', namespaces.moin_page)
            element = ElementTree.Element(tag)
            self._stack_push(element)
        # TODO: This used to add a space after the text.
        self.parse_inline(groups.get('text', ''))
        if groups.get('break') and self._stack[-1].tag.name in ('paragraph',
            'emphasis', 'strong', 'code'):
            tag = ElementTree.QName('line-break', namespaces.moin_page)
            element = ElementTree.Element(tag)
            self._stack_top_append(element)
        self.text = None
    _break_repl = _text_repl

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
    _pre_text_repl = _pre_repl
    _pre_head_repl = _pre_repl
    _pre_kind_repl = _pre_repl

    def _line_repl(self, groups):
        self._stack_pop_name(('page', 'blockquote'))
        self.text = None

    def _code_repl(self, groups):
        DocNode('code', self.cur, groups.get('code_text', u'').strip())
        self.text = None
    _code_text_repl = _code_repl
    _code_head_repl = _code_repl

    def _emph_repl(self, groups):
        if not self._stack_top_check(('emphasis',)):
            tag = ElementTree.QName('emphasis', namespaces.moin_page)
            self._stack_push(ElementTree.Element(tag))
        else:
            self._stack_pop_name(('emphasis',))
            self._stack_pop()
        self.text = None

    def _strong_repl(self, groups):
        if not self._stack_top_check(('strong',)):
            tag = ElementTree.QName('strong', namespaces.moin_page)
            self._stack_push(ElementTree.Element(tag))
        else:
            self._stack_pop_name(('strong',))
            self._stack_pop()
        self.text = None

    def _break_repl(self, groups):
        tag = ElementTree.QName('line-break', namespaces.moin_page)
        element = ElementTree.Element(tag)
        self._stack_top_append(element)

    def _escape_repl(self, groups):
        if self.text is None:
            self.text = DocNode('text', self.cur, u'')
        self.text.content += groups.get('escaped_char', u'')

    def _char_repl(self, groups):
        self._stack_top_append(groups.get('char', u''))

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
        return tag.uri == self.namespace and tag.name in names

    def _replace(self, match):
        """Invoke appropriate _*_repl method. Called for every matched group."""

        groups = match.groupdict()
        for name, text in groups.iteritems():
            if text is not None:
                replace = getattr(self, '_%s_repl' % name)
                replace(groups)
                return

    def parse_inline(self, raw):
        """Recognize inline elements inside blocks."""

        re.sub(self.inline_re, self._replace, raw)

    def parse_block(self, raw):
        """Recognize block elements."""

        re.sub(self.block_re, self._replace, raw)

#################### Helper classes

### The document model and emitter follow

class DocNode:
    """
    A node in the document.
    """

    def __init__(self, kind='', parent=None, content=None):
        self.children = []
        self.parent = parent
        self.kind = kind
        self.content = content
        if self.parent is not None:
            self.parent.children.append(self)
