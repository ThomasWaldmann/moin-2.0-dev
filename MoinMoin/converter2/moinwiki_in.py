"""
MoinMoin - Moin Wiki input converter

@copyright: 2000-2002 Juergen Hermann <jh@web.de>
            2006-2008 MoinMoin:ThomasWaldmann
            2007 MoinMoin:ReimarBauer
            2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import re
from emeraldtree import ElementTree as ET

from MoinMoin import config, wikiutil
from MoinMoin.util import namespaces
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
    @classmethod
    def _factory(cls, input, output):
        if input == 'text/moin-wiki' and output == 'application/x-moin-document':
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
        iter = _Iter(text.split('\n'))

        for line in iter:
            match = self.block_re.match(line)
            self._apply(match, 'block', iter)

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

    def block_list_repl(self, iter, list, list_indent, list_numbers=None,
            list_alpha=None, list_roman=None, list_bullet=None,
            list_none=None, list_text=None):

        level = len(list_indent)
        if list_numbers or list_alpha or list_alpha:
            type = 'ordered'
        else:
            type = 'unordered'

        while True:
            cur = self.stack_top()
            if cur.tag.name in ('page', 'blockquote'):
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
            attrib = {tag_generate: type}
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

        self.parse_inline(list_text)

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

    def block_macro_repl(self, iter, macro, macro_name, macro_args=''):
        """Handles macros using the placeholder syntax."""

        self.stack_pop_name('page')
        elem = self.macro(macro_name, macro_args, macro, 'block')
        if elem:
            self.stack_top_append(elem)

    block_nowiki = r"""
        (?P<nowiki>
            ^
            \s*
            (?P<nowiki_marker> \{{3,} )
            \s*
            (?P<nowiki_data> \#!.+ )?
            \s*
            $
        )
    """
    # Matches the beginning of a nowiki block

    nowiki_end = r"""
        ^ (?P<marker> }{3,} ) \s* $
    """
    # Matches the possibly escaped end of a nowiki block

    def block_nowiki_lines(self, iter, marker_len):
        "Unescaping generator for the lines in a nowiki block"

        for line in iter:
            match = self.nowiki_end_re.match(line)
            if match:
                marker = match.group('marker')
                if len(marker) >= marker_len:
                    return
            yield line

    def block_nowiki_repl(self, iter, nowiki, nowiki_marker, nowiki_data=None):
        self.stack_pop_name('page')

        tag = ET.QName('blockcode', namespaces.moin_page)

        nowiki_marker_len = len(nowiki_marker)

        if nowiki_data:
            firstline = nowiki_data
        else:
            try:
                firstline = iter.next()
            except StopIteration:
                return

            # Stop directly if we got an end marker in the first line
            match = self.nowiki_end_re.match(firstline)
            if match and len(match.group('marker')) >= nowiki_marker_len:
                self.stack_top_append(ET.Element(tag))
                return

        lines = _Iter(self.block_nowiki_lines(iter, nowiki_marker_len))

        if firstline.startswith('#!'):
            args = wikiutil.parse_quoted_separated(firstline[2:], separator=None)
            name = args[0].pop(0)

            # Parse it directly if the type is ourself
            if name in ('wiki', ):
                attrib = {}
                tag = ET.QName('page', namespaces.moin_page)

                if args[0]:
                    classes = ' '.join([i.replace('/', ' ') for i in args[0]])
                    attrib[ET.QName('class', namespaces.html)] = classes

                for key, value in args[1].iteritems():
                    if key in ('background-color', 'color'):
                        attrib[ET.QName(key, namespaces.moin_page)] = value

                self.stack_push(ET.Element(tag, attrib))

                for line in lines:
                    match = self.block_re.match(line)
                    self._apply(match, 'block', lines)

                self.stack_pop_name('page')
                self.stack_pop()

            else:
                # TODO
                attrib = {ET.QName('class', namespaces.html): 'error'}
                elem = ET.Element(tag, attrib, children=[firstline])
                self.stack_top_append(elem)

                for line in lines:
                    elem.append('\n')
                    elem.append(line)

        else:
            elem = ET.Element(tag, children=[firstline])
            self.stack_top_append(elem)

            for line in lines:
                elem.append('\n')
                elem.append(line)

    block_separator = r'(?P<separator> ^ \s* -{4,} \s* $ )'

    def block_separator_repl(self, iter, separator):
        self.stack_pop_name('page')
        tag = ET.QName('separator', namespaces.moin_page)
        self.stack_top_append(ET.Element(tag))

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

    inline_emphstrong = r"""
        (?P<emphstrong>
            '{2,6}
            (?=[^']+ (?P<emphstrong_follow> '{2,3} (?!') ) )?
        )
    """

    def inline_emphstrong_repl(self, emphstrong, emphstrong_follow=''):
        tag_emphasis = ET.QName('emphasis', namespaces.moin_page)
        tag_strong = ET.QName('strong', namespaces.moin_page)

        if len(emphstrong) == 5:
            if self.stack_top_check('emphasis'):
                self.stack_pop()
                if self.stack_top_check('strong'):
                    self.stack_pop()
                else:
                    self.stack_push(ET.Element(tag_strong))
            elif self.stack_top_check('strong'):
                if self.stack_top_check('strong'):
                    self.stack_pop()
                else:
                    self.stack_push(ET.Element(tag_strong))
            else:
                if len(emphstrong_follow) == 3:
                    self.stack_push(ET.Element(tag_emphasis))
                    self.stack_push(ET.Element(tag_strong))
                else:
                    self.stack_push(ET.Element(tag_strong))
                    self.stack_push(ET.Element(tag_emphasis))
        elif len(emphstrong) == 3:
            if self.stack_top_check('strong'):
                self.stack_pop()
            else:
                self.stack_push(ET.Element(tag_strong))
        elif len(emphstrong) == 2:
            if self.stack_top_check('emphasis'):
                self.stack_pop()
            else:
                self.stack_push(ET.Element(tag_emphasis))

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
        self.stack_push(element)
        if link_text:
            self.parse_inline(link_text, self.inlinedesc_re)
        else:
            self.stack_top_append(text)
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

    def inline_macro_repl(self, macro, macro_name, macro_args=''):
        """Handles macros using the placeholder syntax."""

        elem = self.macro(macro_name, macro_args, macro, 'inline')
        self.stack_top_append(elem)

    inline_nowiki = r"""
        (?P<nowiki>
            {{{
            (?P<nowiki_text>.*?}*)
            }}}
            |
            `
            (?P<nowiki_text_backtick>.*?)
            `
        )
    """

    def inline_nowiki_repl(self, nowiki, nowiki_text=None,
            nowiki_text_backtick=None):
        tag = ET.QName('code', namespaces.moin_page)

        text = None
        if nowiki_text is not None:
            text = nowiki_text
        # Remove empty backtick nowiki samples
        elif nowiki_text_backtick:
            text = nowiki_text_backtick
        else:
            return

        self.stack_top_append(ET.Element(tag, children=[text]))

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

    inline_freelink = r"""
        (?P<freelink>
         (?:
          (?<![%(u)s%(l)s/])  # require anything not upper/lower/slash before
          |
          ^  # ... or beginning of line
         )
         (?P<freelink_bang>\!)?  # configurable: avoid getting CamelCase rendered as link
         (
          (?P<freelink_interwiki>
           [A-Z][a-zA-Z]+\:
           (?P<freelink_interwiki_page>
            (?=[^ ]*[%(u)s%(l)s0..9][^ ]* )  # make sure there is something non-blank with at least one alphanum letter following
            [^"\'}\]|:,.\)?!]+  # we take all until we hit some blank or punctuation char ...
           )
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
         )
         (?:
          (?![%(u)s%(l)s/])  # require anything not upper/lower/slash following
          |
          $  # ... or end of line
         )
        )
    """ % {
        'u': config.chars_upper,
        'l': config.chars_lower,
        'child': re.escape(wikiutil.CHILD_PREFIX),
        'parent': re.escape(wikiutil.PARENT_PREFIX),
    }

    def inline_freelink_repl(self, freelink, freelink_bang=None,
            freelink_interwiki=None, freelink_interwiki_page=None,
            freelink_page=None):
        link = freelink_page or freelink_interwiki
        text = freelink_page or freelink_interwiki_page

        if freelink_bang:
            self.stack_top_append(text)
            return

        tag = ET.QName('a', namespaces.moin_page)
        tag_href = ET.QName('href', namespaces.xlink)

        attrib = {tag_href: 'wiki.local:' + link}
        element = ET.Element(tag, attrib, children=[text])
        self.stack_top_append(element)

    inline_url = r"""
        (?P<url>
            (^ | (?<=\s | [.,:;!?()/=]))
            (?P<url_target>
                # TODO: config.url_schemas
                (http|https|ftp|nntp|news|mailto|telnet|file|irc):
                \S+?
            )
            ($ | (?=\s | [,.:;!?()] (\s | $)))
        )
    """

    def inline_url_repl(self, url, url_target):
        tag = ET.QName('a', namespaces.moin_page)
        tag_href = ET.QName('href', namespaces.xlink)
        element = ET.Element(tag, attrib = {tag_href: url_target}, children = [url_target])
        self.stack_top_append(element)

    # Block elements
    block = (
        block_line,
        block_head,
        block_separator,
        block_macro,
        block_nowiki,
        block_list,
        #block_table,
        block_text,
    )
    block_re = re.compile('|'.join(block), re.X | re.U | re.M)

    inline = (
        inline_link,
        inline_macro,
        inline_nowiki,
        inline_object,
        inline_emphstrong,
        inline_freelink,
        inline_url,
        inline_text,
    )
    inline_re = re.compile('|'.join(inline), re.X | re.U)

    inlinedesc = (
        inline_macro,
        inline_nowiki,
        inline_emphstrong,
        inline_text,
    )
    inlinedesc_re = re.compile('|'.join(inlinedesc), re.X | re.U)

    # Nowiki end
    nowiki_end_re = re.compile(nowiki_end, re.X)

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
        data = dict(((str(k), v) for k, v in match.groupdict().iteritems() if v is not None))
        getattr(self, '%s_%s_repl' % (prefix, match.lastgroup))(*args, **data)

    def parse_inline(self, text, re=inline_re):
        """Recognize inline elements within the given text"""

        for match in re.finditer(text):
            self._apply(match, 'inline')

from _registry import default_registry
default_registry.register(Converter._factory)
