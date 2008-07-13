"""
MoinMoin - Compatibility formatter

Implements the oldstyle formatter interface and produces a internal tree
representation.

@copyright: 2000-2004 by Juergen Hermann <jh@web.de>
@copyright: 2008 MoinMoin:BastianBlank
@copyright: 1999-2007 by Fredrik Lundh (html parser)
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET
import htmlentitydefs
from HTMLParser import HTMLParser as _HTMLParserBase

from MoinMoin import wikiutil
from MoinMoin.util import namespaces

class _HTMLParser(_HTMLParserBase):
    AUTOCLOSE = "p", "li", "tr", "th", "td", "head", "body"
    IGNOREEND = "img", "hr", "meta", "link", "br"

    def __init__(self, encoding=None):
        self.__stack = []
        self.__builder = ET.TreeBuilder()
        self.encoding = encoding or "iso-8859-1"
        _HTMLParserBase.__init__(self)

    ##
    # Flushes parser buffers, and return the root element.
    #
    # @return An Element instance.

    def close(self):
        _HTMLParserBase.close(self)
        return self.__builder.close()

    ##
    # (Internal) Handles start tags.

    def handle_starttag(self, tag, attrs):
        tag = ET.QName(tag.lower(), namespaces.html)
        if tag.name == "meta":
            return
        if tag.name in self.AUTOCLOSE:
            if self.__stack and self.__stack[-1] == tag:
                self.handle_endtag(tag)
        self.__stack.append(tag)
        attrib = {}
        if attrs:
            for key, value in attrs:
                key = ET.QName(key.lower(), namespaces.html)
                attrib[key] = value
        self.__builder.start(tag, attrib)
        if tag.name in self.IGNOREEND:
            self.__stack.pop()
            self.__builder.end(tag)

    ##
    # (Internal) Handles end tags.

    def handle_endtag(self, tag):
        if not isinstance(tag, ET.QName):
            tag = ET.QName(tag.lower(), namespaces.html)
        if tag.name in self.IGNOREEND:
            return
        lasttag = self.__stack.pop()
        if tag != lasttag and lasttag in self.AUTOCLOSE:
            self.handle_endtag(lasttag)
        self.__builder.end(tag)

    ##
    # (Internal) Handles character references.

    def handle_charref(self, char):
        if char[:1] == "x":
            char = int(char[1:], 16)
        else:
            char = int(char)
        if 0 <= char < 128:
            self.__builder.data(chr(char))
        else:
            self.__builder.data(unichr(char))

    ##
    # (Internal) Handles entity references.

    def handle_entityref(self, name):
        entity = htmlentitydefs.entitydefs.get(name)
        if entity:
            if len(entity) == 1:
                entity = ord(entity)
            else:
                entity = int(entity[2:-1])
            if 0 <= entity < 128:
                self.__builder.data(chr(entity))
            else:
                self.__builder.data(unichr(entity))
        else:
            self.unknown_entityref(name)

    ##
    # (Internal) Handles character data.

    def handle_data(self, data):
        # convert to unicode
        data = data.decode(self.encoding, "ignore")
        self.__builder.data(data)

    ##
    # (Hook) Handles unknown entity references.  The default action
    # is to ignore unknown entities.

    def unknown_entityref(self, name):
        pass # ignore by default; override if necessary


class Formatter(object):
    hardspace = ' '

    tag_a = ET.QName('a', namespaces.moin_page)
    tag_emphasis = ET.QName('emphasis', namespaces.moin_page)
    tag_h = ET.QName('h', namespaces.moin_page)
    tag_href = ET.QName('href', namespaces.xlink)
    tag_id = ET.QName('id', namespaces.moin_page)
    tag_list = ET.QName('list', namespaces.moin_page)
    tag_list_item = ET.QName('list-item', namespaces.moin_page)
    tag_list_item_body = ET.QName('list-item-body', namespaces.moin_page)
    tag_macro = ET.QName('macro', namespaces.moin_page)
    tag_macro_args = ET.QName('macro-args', namespaces.moin_page)
    tag_macro_name = ET.QName('macro-name', namespaces.moin_page)
    tag_macro_type = ET.QName('macro-type', namespaces.moin_page)
    tag_outline_level = ET.QName('outline-level', namespaces.moin_page)
    tag_p = ET.QName('p', namespaces.moin_page)
    tag_span = ET.QName('span', namespaces.moin_page)
    tag_strong = ET.QName('strong', namespaces.moin_page)
    tag_table = ET.QName('table', namespaces.moin_page)
    tag_table_body = ET.QName('table-body', namespaces.moin_page)
    tag_table_cell = ET.QName('table-cell', namespaces.moin_page)
    tag_table_row = ET.QName('table-row', namespaces.moin_page)

    def __init__(self, request, page, **kw):
        self.request, self.page = request, page
        self._ = request.getText

        self._store_pagelinks = kw.get('store_pagelinks', 0)
        self._terse = kw.get('terse', 0)
        self.in_p = 0
        self.in_pre = 0
        self._base_depth = 0

        self.root = ET.Element(None)
        self._stack = [self.root]

    def handle_on(self, on, tag, attrib={}, nonempty=False):
        if on:
            self._stack_push(ET.Element(tag, attrib))
        else:
            elem = self._stack_pop()
            if nonempty and not len(elem):
                self._stack[-1].remove(elem)
        return ''

    def lang(self, on, lang_name):
        return ""

    # Document Level #####################################################

    def startDocument(self, pagename):
        raise NotImplementedError

    def endDocument(self):
        raise NotImplementedError

    def startContent(self, **kw):
        raise NotImplementedError

    def endContent(self):
        raise NotImplementedError

    # Links ##############################################################

    def pagelink(self, on, pagename='', page=None, **kw):
        if on:
            if not pagename and page:
                pagename = page.page_name
            tag = ET.QName('a', namespaces.moin_page)
            tag_href = ET.QName('href', namespaces.xlink)
            attrib = {tag_href: "wiki.local:" + pagename}
            self._stack_push(ET.Element(tag, attrib))
        else:
            self._stack_pop()
        return ''

    def interwikilink(self, on, interwiki='', pagename='', **kw):
        if on:
            tag = ET.QName('a', namespaces.moin_page)
            tag_href = ET.QName('href', namespaces.xlink)
            attrib = {tag_href: "wiki://" + interwiki + '/' + pagename}
            self._stack_push(ET.Element(tag, attrib))
        else:
            self._stack_pop()
        return ''

    def url(self, on, url=None, css=None, **kw):
        attrib = {}
        if url:
            attrib[self.tag_href] = url
        return self.handle_on(on, self.tag_a, attrib)

    # Attachments ######################################################

    def attachment_link(self, on, url=None, **kw):
        raise NotImplementedError
    def attachment_image(self, url, **kw):
        raise NotImplementedError
    def attachment_drawing(self, url, text, **kw):
        raise NotImplementedError

    def attachment_inlined(self, url, text, **kw):
        raise NotImplementedError

    def anchordef(self, name):
        raise NotImplementedError
        return ""

    def line_anchordef(self, lineno):
        id = 'line-%d' % lineno
        self._stack_top_append(ET.Element(self.tag_span, attrib={self.tag_id: id}))
        return ""

    def anchorlink(self, on, name='', **kw):
        raise NotImplementedError
        return ""

    def line_anchorlink(self, on, lineno=0):
        raise NotImplementedError
        return ""

    def image(self, src=None, **kw):
        """An inline image.

        Extra keyword arguments are according to the HTML <img> tag attributes.
        In particular an 'alt' or 'title' argument should give a description
        of the image.
        """
        raise NotImplementedError
        title = src
        for titleattr in ('title', 'html__title', 'alt', 'html__alt'):
            if titleattr in kw:
                title = kw[titleattr]
                break
        if title:
            return '[Image:%s]' % title
        return '[Image]'

    # generic transclude/include:
    def transclusion(self, on, **kw):
        raise NotImplementedError
    def transclusion_param(self, **kw):
        raise NotImplementedError

    def smiley(self, text):
        raise NotImplementedError
        return text

    def nowikiword(self, text):
        self._stack_top_append(text)
        return ''

    # Text and Text Attributes ###########################################

    def text(self, text, **kw):
        self._stack_top_append(unicode(text))
        return ''

    def _text(self, text):
        raise NotImplementedError

    def strong(self, on, **kw):
        return self.handle_on(on, self.tag_strong, nonempty=True)

    def emphasis(self, on, **kw):
        return self.handle_on(on, self.tag_emphasis, nonempty=True)

    def underline(self, on, **kw):
        raise NotImplementedError

    def highlight(self, on, **kw):
        raise NotImplementedError

    def sup(self, on, **kw):
        raise NotImplementedError

    def sub(self, on, **kw):
        raise NotImplementedError

    def strike(self, on, **kw):
        raise NotImplementedError

    def code(self, on, **kw):
        if on:
            self._stack_push(ET.Element(ET.QName('code', namespaces.moin_page)))
        else:
            self._stack_pop()
        return ''

    def preformatted(self, on, **kw):
        raise NotImplementedError
        self.in_pre = on != 0

    def small(self, on, **kw):
        raise NotImplementedError

    def big(self, on, **kw):
        raise NotImplementedError

    # special markup for syntax highlighting #############################

    def code_area(self, on, code_id, **kw):
        raise NotImplementedError

    def code_line(self, on):
        raise NotImplementedError

    def code_token(self, tok_text, tok_type):
        raise NotImplementedError

    # Paragraphs, Lines, Rules ###########################################

    def linebreak(self, preformatted=1):
        raise NotImplementedError

    def paragraph(self, on, **kw):
        self.in_p = on != 0
        return self.handle_on(on, self.tag_p)

    def rule(self, size=0, **kw):
        raise NotImplementedError

    def icon(self, type):
        raise NotImplementedError
        return type

    # Lists ##############################################################

    def number_list(self, on, type=None, start=None, **kw):
        # TODO list type
        attrib = {}
        return self.handle_on(on, self.tag_list, attrib)

    def bullet_list(self, on, **kw):
        # TODO list type
        attrib = {}
        return self.handle_on(on, self.tag_list, attrib)

    def listitem(self, on, **kw):
        if on:
            self._stack_push(ET.Element(self.tag_list_item))
            self._stack_push(ET.Element(self.tag_list_item_body))
        else:
            self._stack_pop()
            self._stack_pop()
        return ''

    def definition_list(self, on, **kw):
        raise NotImplementedError

    def definition_term(self, on, compact=0, **kw):
        raise NotImplementedError

    def definition_desc(self, on, **kw):
        raise NotImplementedError

    def heading(self, on, depth, **kw):
        attrib = {self.tag_outline_level: str(depth)}
        return self.handle_on(on, self.tag_h, attrib)

    # Tables #############################################################

    def table(self, on, attrs={}, **kw):
        if on:
            self._stack_push(ET.Element(self.tag_table))
            self._stack_push(ET.Element(self.tag_table_body))
        else:
            self._stack_pop()
            self._stack_pop()
        return ''

    def table_row(self, on, attrs={}, **kw):
        return self.handle_on(on, self.tag_table_row)

    def table_cell(self, on, attrs={}, **kw):
        return self.handle_on(on, self.tag_table_cell)

    # Dynamic stuff / Plugins ############################################

    def macro(self, macro_obj, name, args, markup=None):
        attrib = {self.tag_macro_name: name, self.tag_macro_args: args}
        if self.in_p:
            attrib[self.tag_macro_type] = 'inline'
        else:
            attrib[self.tag_macro_type] = 'block'
        elem = ET.Element(self.tag_macro, attrib)
        self._stack_top_append(elem)
        return ''

    def _get_bang_args(self, line):
        if line.startswith('#!'):
            try:
                name, args = line[2:].split(None, 1)
            except ValueError:
                return ''
            else:
                return args
        return None

    def parser(self, parser_name, lines):
        """ parser_name MUST be valid!
            writes out the result instead of returning it!
        """
        raise NotImplementedError
        # attention: this is copied into text_python!
        parser = wikiutil.searchAndImportPlugin(self.request.cfg, "parser", parser_name)
        args = None
        if lines:
            args = self._get_bang_args(lines[0])
            logging.debug("formatter.parser: parser args %r" % args)
            if args is not None:
                lines = lines[1:]
        if lines and not lines[0]:
            lines = lines[1:]
        if lines and not lines[-1].strip():
            lines = lines[:-1]
        p = parser('\n'.join(lines), self.request, format_args=args)
        p.format(self)
        del p
        return ''

    # Other ##############################################################

    def div(self, on, **kw):
        """ open/close a blocklevel division """
        raise NotImplementedError
        return ""

    def span(self, on, **kw):
        """ open/close a inline span """
        raise NotImplementedError
        return ""

    def rawHTML(self, markup):
        """ This allows emitting pre-formatted HTML markup, and should be
            used wisely (i.e. very seldom).

            Using this event while generating content results in unwanted
            effects, like loss of markup or insertion of CDATA sections
            when output goes to XML formats.
        """
        if not markup:
            return ''

        parser = _HTMLParser()
        parser.feed(markup)
        doc = parser.close()
        self._stack_top_append(doc)

        return ''

    def escapedText(self, on, **kw):
        """ This allows emitting text as-is, anything special will
            be escaped (at least in HTML, some text output format
            would possibly do nothing here)
        """
        self._stack_top_append(text)
        return ''

    def comment(self, text, **kw):
        return ""

    def _stack_pop(self):
        return self._stack.pop()

    def _stack_push(self, elem):
        self._stack_top_append(elem)
        self._stack.append(elem)

    def _stack_top_append(self, elem):
        self._stack[-1].append(elem)

