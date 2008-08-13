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
from MoinMoin.util import namespaces, tree, uri
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
    tag_a = ET.QName('a', namespaces.moin_page)
    tag_alt = ET.QName('alt', namespaces.moin_page)
    tag_blockcode = ET.QName('blockcode', namespaces.moin_page)
    tag_code = ET.QName('code', namespaces.moin_page)
    tag_div = ET.QName('div', namespaces.moin_page)
    tag_emphasis = ET.QName('emphasis', namespaces.moin_page)
    tag_h = ET.QName('h', namespaces.moin_page)
    tag_href = ET.QName('href', namespaces.xlink)
    tag_item_label_generate = ET.QName('item-label-generate', namespaces.moin_page)
    tag_list = ET.QName('list', namespaces.moin_page)
    tag_list_item = ET.QName('list-item', namespaces.moin_page)
    tag_list_item_body = ET.QName('list-item-body', namespaces.moin_page)
    tag_object = ET.QName('object', namespaces.moin_page)
    tag_outline_level = ET.QName('outline-level', namespaces.moin_page)
    tag_page = ET.QName('page', namespaces.moin_page)
    tag_page_href = ET.QName('page-href', namespaces.moin_page)
    tag_p = ET.QName('p', namespaces.moin_page)
    tag_separator = ET.QName('separator', namespaces.moin_page)
    tag_strong = ET.QName('strong', namespaces.moin_page)
    tag_table = ET.QName('table', namespaces.moin_page)
    tag_table_body = ET.QName('table-body', namespaces.moin_page)
    tag_table_cell = ET.QName('table-cell', namespaces.moin_page)
    tag_table_row = ET.QName('table-row', namespaces.moin_page)

    @classmethod
    def _factory(cls, request, input, output):
        if input == 'text/moin-wiki' and output == 'application/x-moin-document':
            return cls

    def __init__(self, request, page_url=None, args=None):
        super(Converter, self).__init__(request)
        self.page_url = page_url

    def __call__(self, content):
        attrib = {}
        if self.page_url:
            attrib[self.tag_page_href] = self.page_url

        self.root = ET.Element(self.tag_page, attrib=attrib)
        self._stack = [self.root]
        iter = _Iter(content)

        for line in iter:
            match = self.block_re.match(line)
            self._apply(match, 'block', iter)

        return self.root

    block_comment = r"""
        (?P<comment>
            ^ \#\#
        )
    """

    def block_comment_repl(self, iter, comment):
        # A comment also ends anything
        self.stack_pop_name('page')

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

        attrib = {self.tag_outline_level: str(level)}
        element = ET.Element(self.tag_h, attrib=attrib, children=[head_text])
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
            cur = self.stack_top()
            if cur.tag.name in ('page', 'blockquote'):
                break
            if cur.tag.name == 'list-item-body':
                if level > cur.level:
                    break
            if cur.tag.name == 'list':
                if (level >= cur.level and type == cur.type and
                        style_type == cur.style_type):
                    break
            self.stack_pop()

        if cur.tag.name != 'list':
            attrib = {tree.moin_page.item_label_generate: type}
            if style_type:
                attrib[tree.moin_page.list_style_type] = style_type
            element = ET.Element(self.tag_list, attrib=attrib)
            element.level, element.type = level, type
            element.style_type = style_type
            self.stack_push(element)

        element = ET.Element(self.tag_list_item)
        element_body = ET.Element(self.tag_list_item_body)
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

    def block_macro_repl(self, iter, macro, macro_name, macro_args=u''):
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

    def block_nowiki_repl(self, iter, nowiki, nowiki_marker, nowiki_data=u''):
        self.stack_pop_name('page')

        nowiki_marker_len = len(nowiki_marker)

        lines = _Iter(self.block_nowiki_lines(iter, nowiki_marker_len))

        if nowiki_data.startswith('#!'):
            args = wikiutil.parse_quoted_separated(nowiki_data[2:].strip(), separator=None)
            name = args[0].pop(0)

            # Parse it directly if the type is ourself
            if name in ('wiki', ):
                attrib = {}

                if args[0]:
                    classes = ' '.join([i.replace('/', ' ') for i in args[0]])
                    attrib[ET.QName('class', namespaces.html)] = classes

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

                elem = ET.Element(self.tag_div)
                self.stack_top_append(elem)

                doc = Converter(self.request, self.page_url, ' '.join(args[0]))(lines)
                elem.extend(doc)

        else:
            elem = ET.Element(self.tag_blockcode)
            self.stack_top_append(elem)

            for line in lines:
                if len(elem):
                    elem.append('\n')
                elem.append(line)

    block_separator = r'(?P<separator> ^ \s* -{4,} \s* $ )'

    def block_separator_repl(self, iter, separator):
        self.stack_pop_name('page')
        self.stack_top_append(ET.Element(self.tag_separator))

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

    def block_table_repl(self, iter, table):
        self.stack_pop_name('page')

        element = ET.Element(self.tag_table)
        self.stack_push(element)
        element = ET.Element(self.tag_table_body)
        self.stack_push(element)

        self.block_table_row(table)

        for line in iter:
            match = self.table_re.match(line)
            if not match:
                # Allow the mainloop to take care of the line after a list.
                iter.push(line)
                break

            self.block_table_row(match.group('table'))

    def block_table_row(self, content):
        element = ET.Element(self.tag_table_row)
        self.stack_push(element)

        for match in self.tablerow_re.finditer(content):
            self._apply(match, 'tablerow')

        self.stack_pop()

    block_text = r'(?P<text> .+ )'

    def block_text_repl(self, iter, text):
        if self.stack_top_check('table', 'table-body', 'list'):
            self.stack_pop_name('page')

        if self.stack_top_check('page'):
            element = ET.Element(self.tag_p)
            self.stack_push(element)
        # If we are in a paragraph already, don't loose the whitespace
        else:
            self.stack_top_append('\n')
        self.parse_inline(text)

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

    def inline_comment_repl(self, comment, comment_begin=None, comment_end=None):
        # TODO
        pass

    inline_emphstrong = r"""
        (?P<emphstrong>
            '{2,6}
            (?=[^']+ (?P<emphstrong_follow> '{2,3} (?!') ) )?
        )
    """

    def inline_emphstrong_repl(self, emphstrong, emphstrong_follow=''):
        if len(emphstrong) == 5:
            if self.stack_top_check('emphasis'):
                self.stack_pop()
                if self.stack_top_check('strong'):
                    self.stack_pop()
                else:
                    self.stack_push(ET.Element(self.tag_strong))
            elif self.stack_top_check('strong'):
                if self.stack_top_check('strong'):
                    self.stack_pop()
                else:
                    self.stack_push(ET.Element(self.tag_strong))
            else:
                if len(emphstrong_follow) == 3:
                    self.stack_push(ET.Element(self.tag_emphasis))
                    self.stack_push(ET.Element(self.tag_strong))
                else:
                    self.stack_push(ET.Element(self.tag_strong))
                    self.stack_push(ET.Element(self.tag_emphasis))
        elif len(emphstrong) == 3:
            if self.stack_top_check('strong'):
                self.stack_pop()
            else:
                self.stack_push(ET.Element(self.tag_strong))
        elif len(emphstrong) == 2:
            if self.stack_top_check('emphasis'):
                self.stack_pop()
            else:
                self.stack_push(ET.Element(self.tag_emphasis))

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

    def inline_size_repl(self, size, size_begin=None, size_end=None):
        if size_begin:
            size = size[1] == '+' and '120%' or '85%'
            attrib = {tree.moin_page.font_size: size}
            elem = tree.moin_page.span(attrib=attrib)
            self.stack_push(elem)
        else:
            self.stack_pop()

    inline_strike = r"""
        (?P<strike>
           (?P<strike_begin>)
           --\(
           |
           \)--
        )
    """

    def inline_strike_repl(self, strike, strike_begin=None):
        if strike_begin is not None:
            attrib = {tree.moin_page.text_decoration: 'line-through'}
            self.stack_push(tree.moin_page.span(attrib=attrib))
        else:
            self.stack_pop()

    inline_subscript = r"""
        (?P<subscript>
            ,,
            (?P<subscript_text> .*? )
            ,,
        )
    """

    def inline_subscript_repl(self, subscript, subscript_text):
        attrib = {tree.moin_page.baseline_shift: 'sub'}
        elem = tree.moin_page.span(attrib=attrib, children=[subscript_text])
        self.stack_top_append(elem)

    inline_superscript = r"""
        (?P<superscript>
            \^
            (?P<superscript_text> .*? )
            \^
        )
    """

    def inline_superscript_repl(self, superscript, superscript_text):
        attrib = {tree.moin_page.baseline_shift: 'super'}
        elem = tree.moin_page.span(attrib=attrib, children=[superscript_text])
        self.stack_top_append(elem)

    inline_underline = r"""
        (?P<underline>
            __
        )
    """

    def inline_underline_repl(self, underline):
        if not self.stack_top_check('span'):
            attrib = {tree.moin_page.text_decoration: 'underline'}
            self.stack_push(tree.moin_page.span(attrib=attrib))
        else:
            self.stack_pop()

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
            ([|] \s* (?P<link_text>[^|]*?) \s*)?
            ([|] \s* (?P<link_args>.*?) \s*)?
            \]\]
        )
    """

    def inline_link_repl(self, link, link_url=None, link_page=None,
            link_text=None, link_args=None):
        """Handle all kinds of links."""

        # TODO: Query string / fragment
        if link_page is not None:
            if '#' in link_page:
                path, fragment = link_page.rsplit('#', 1)
            else:
                path, fragment = link_page, None
            # TODO: unicode URI
            target = str(uri.Uri(scheme='wiki.local', path=path.encode('utf-8'), fragment=fragment))
            text = link_page
        else:
            # TODO: unicode URI
            target = str(uri.Uri(link_url.encode('utf-8')))
            text = link_url
        element = ET.Element(self.tag_a, attrib={self.tag_href: target})
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

    def inline_macro_repl(self, macro, macro_name, macro_args=u''):
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
        text = None
        if nowiki_text is not None:
            text = nowiki_text
        # Remove empty backtick nowiki samples
        elif nowiki_text_backtick:
            text = nowiki_text_backtick
        else:
            return

        self.stack_top_append(ET.Element(self.tag_code, children=[text]))

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

        # TODO: unicode URI
        target = str(uri.Uri(object_target.encode('utf-8')))

        attrib = {self.tag_href: target}
        if object_text is not None:
            attrib[self.tag_alt] = object_text

        element = ET.Element(self.tag_object, attrib)
        self.stack_top_append(element)

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

    def inline_freelink_repl(self, freelink, freelink_bang=None,
            freelink_interwiki_page=None, freelink_interwiki_ref=None,
            freelink_page=None, freelink_email=None):
        if freelink_bang:
            self.stack_top_append(freelink)
            return

        attrib = {}

        if freelink_page:
            page = freelink_page.encode('utf-8')
            if '#' in page:
                path, fragment = page.rsplit('#', 1)
            else:
                path, fragment = page, None
            # TODO: unicode URI
            link = uri.Uri(scheme='wiki.local', path=path, fragment=fragment)
            text = freelink_page

        elif freelink_email:
            link = 'mailto:' + freelink_email
            text = freelink_email

        else:
            wikitag_bad = wikiutil.resolve_interwiki(self.request,
                    freelink_interwiki_ref, freelink_interwiki_page)[3]
            if wikitag_bad:
                self.stack_top_append(freelink)
                return

            # TODO: unicode URI
            link = uri.Uri(scheme='wiki',
                    authority=freelink_interwiki_ref.encode('utf-8'),
                    path='/' + freelink_interwiki_page.encode('utf-8'))
            text = freelink_interwiki_page

        attrib[self.tag_href] = str(link)

        element = ET.Element(self.tag_a, attrib, children=[text])
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
        # TODO: unicode URI
        url = str(uri.Uri(url_target.encode('utf-8')))
        attrib = {self.tag_href: url}
        element = ET.Element(self.tag_a, attrib=attrib, children=[url_target])
        self.stack_top_append(element)

    table = block_table

    tablerow = r"""
        (?P<cell>
            (?P<cell_marker> (\|\|)+ )
            ( < (?P<cell_args> .*? ) > )?
            \s*
            (?P<cell_text> .*? )
            \s*
            (?= ( \|\| | $ ) )
        )
    """

    def tablerow_cell_repl(self, cell, cell_marker, cell_text, cell_args=None):
        element = ET.Element(self.tag_table_cell)
        self.stack_push(element)

        self.parse_inline(cell_text)

        self.stack_pop_name('table-cell')
        self.stack_pop()

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

    def stack_top_append_iftrue(self, elem):
        if elem:
            self.stack_top_append(elem)

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

        pos = 0
        for match in re.finditer(text):
            # Handle leading text
            self.stack_top_append_iftrue(text[pos:match.start()])
            pos = match.end()

            self._apply(match, 'inline')

        # Handle trailing text
        self.stack_top_append_iftrue(text[pos:])

from _registry import default_registry
default_registry.register(Converter._factory)
