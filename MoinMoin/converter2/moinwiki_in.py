"""
MoinMoin - Moin Wiki input converter

@copyright: 2008 MoinMoin:BastianBlank (converter interface)
@license: GNU GPL, see COPYING for details.
"""

import re
from emeraldtree import ElementTree as ET

from MoinMoin.util import namespaces
from MoinMoin.converter2._wiki_macro import ConverterMacro

class Converter(ConverterMacro):
    @classmethod
    def _factory(cls, input, output):
        if input == 'text/moin-wiki;disabled' and output == 'application/x-moin-document':
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
            (?P=head_head) \s*
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

    inline_emphstrong = r"""
        (?P<emphstrong>
            '{2,5}
            (?=[^']+ (?P<emphstrong_follow> '{2,3} (?!') ) )?
        )
    """

    def inline_emphstrong_repl(self, emphstrong, emphstrong_follow=''):
        tag_emphasis = ET.QName('emphasis', namespaces.moin_page)
        tag_strong = ET.QName('strong', namespaces.moin_page)

        if len(emphstrong) == 5:
            if self._stack_top_check(('emphasis', )):
                self._stack_pop()
                if self._stack_top_check(('strong', )):
                    self._stack_pop()
                else:
                    self._stack_push(ET.Element(tag_strong))
            elif self._stack_top_check(('strong', )):
                if self._stack_top_check(('strong', )):
                    self._stack_pop()
                else:
                    self._stack_push(ET.Element(tag_strong))
            else:
                if len(emphstrong_follow) == 3:
                    self._stack_push(ET.Element(tag_emphasis))
                    self._stack_push(ET.Element(tag_strong))
                else:
                    self._stack_push(ET.Element(tag_strong))
                    self._stack_push(ET.Element(tag_emphasis))
        elif len(emphstrong) == 3:
            if self._stack_top_check(('strong', )):
                self._stack_pop()
            else:
                self._stack_push(ET.Element(tag_strong))
        elif len(emphstrong) == 2:
            if self._stack_top_check(('emphasis', )):
                self._stack_pop()
            else:
                self._stack_push(ET.Element(tag_emphasis))

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
        if link_text:
            self.parse_inline(link_text)
        else:
            self._stack_top_append(text)
        self._stack_pop()

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

    # Block elements
    block = (
        block_line,
        block_head,
        #block_separator,
        #block_macro,
        #block_nowiki,
        #block_list,
        #block_table,
        block_text,
    )
    block_re = re.compile('|'.join(block), re.X | re.U | re.M)

    inline = (
        inline_link,
        #inline_url,
        #inline_macro,
        #inline_nowiki,
        inline_object,
        inline_emphstrong,
        #inline_linebreak,
        inline_text
    )
    inline_re = re.compile('|'.join(inline), re.X | re.U)

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

    def parse_inline(self, raw):
        """Recognize inline elements inside blocks."""

        self._apply(self.inline_re, 'inline', raw)

    def parse_block(self, raw):
        """Recognize block elements."""

        self._apply(self.block_re, 'block', raw)

from _registry import default_registry
default_registry.register(Converter._factory)
