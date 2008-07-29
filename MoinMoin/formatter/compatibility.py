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
from MoinMoin.converter2._wiki_macro import ConverterMacro
from MoinMoin.util import namespaces

class _HTMLParser(_HTMLParserBase):
    AUTOCLOSE = "p", "li", "tr", "th", "td", "head", "body"
    IGNOREEND = "img", "hr", "meta", "link", "br", "input", 'col'

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
                key = key.lower()
                # Handle short attributes
                if value is None:
                    value = key
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
        if isinstance(data, str):
            data = data.decode(self.encoding, "ignore")
        self.__builder.data(data)

    ##
    # (Hook) Handles unknown entity references.  The default action
    # is to ignore unknown entities.

    def unknown_entityref(self, name):
        pass # ignore by default; override if necessary


class Formatter(ConverterMacro):
    hardspace = ' '

    tag_a = ET.QName('a', namespaces.moin_page)
    tag_blockcode = ET.QName('blockcode', namespaces.moin_page)
    tag_data = ET.QName('data', namespaces.moin_page)
    tag_div = ET.QName('div', namespaces.moin_page)
    tag_emphasis = ET.QName('emphasis', namespaces.moin_page)
    tag_font_size = ET.QName('font-size', namespaces.moin_page)
    tag_h = ET.QName('h', namespaces.moin_page)
    tag_href = ET.QName('href', namespaces.xlink)
    tag_id = ET.QName('id', namespaces.moin_page)
    tag_item_label_generate = ET.QName('item-label-generate', namespaces.moin_page)
    tag_list = ET.QName('list', namespaces.moin_page)
    tag_list_item = ET.QName('list-item', namespaces.moin_page)
    tag_list_item_body = ET.QName('list-item-body', namespaces.moin_page)
    tag_list_item_label = ET.QName('list-item-label', namespaces.moin_page)
    tag_macro = ET.QName('macro', namespaces.moin_page)
    tag_macro_args = ET.QName('macro-args', namespaces.moin_page)
    tag_macro_name = ET.QName('macro-name', namespaces.moin_page)
    tag_macro_type = ET.QName('macro-type', namespaces.moin_page)
    tag_object = ET.QName('object', namespaces.moin_page)
    tag_outline_level = ET.QName('outline-level', namespaces.moin_page)
    tag_p = ET.QName('p', namespaces.moin_page)
    tag_src = ET.QName('src', namespaces.moin_page)
    tag_separator = ET.QName('separator', namespaces.moin_page)
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

    def handle_on(self, on, tag, attrib={}):
        if on:
            self._stack_push(ET.Element(tag, attrib))
        else:
            self._stack_pop()
        return ''

    def lang(self, on, lang_name):
        return ""

    def sysmsg(self, on, **kw):
        if on:
            self.paragraph(on)
            # TODO: class="error"?
            self.strong(on)
        else:
            self._stack_pop()
            self._stack_pop()
        return ''

    # Document Level #####################################################

    def startDocument(self, pagename):
        raise NotImplementedError('startDocument')

    def endDocument(self):
        raise NotImplementedError('endDocument')

    def startContent(self, **kw):
        raise NotImplementedError('startContent')

    def endContent(self):
        raise NotImplementedError('endContent')

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
        # TODO
        return ''

    def attachment_image(self, url, **kw):
        # TODO
        return ''

    def attachment_drawing(self, url, text, **kw):
        # TODO
        return ''

    def attachment_inlined(self, url, text, **kw):
        # TODO
        return ''

    def anchordef(self, name):
        raise NotImplementedError('anchordef')

    def line_anchordef(self, lineno):
        # TODO
        #id = 'line-%d' % lineno
        #self._stack_top_append(ET.Element(self.tag_span, attrib={self.tag_id: id}))
        return ""

    def anchorlink(self, on, name='', **kw):
        raise NotImplementedError('anchorlink')

    def line_anchorlink(self, on, lineno=0):
        raise NotImplementedError('line_anchorlink')

    def image(self, src=None, **kw):
        """An inline image.

        Extra keyword arguments are according to the HTML <img> tag attributes.
        In particular an 'alt' or 'title' argument should give a description
        of the image.
        """
        # TODO
        return ''
        title = src
        for titleattr in ('title', 'html__title', 'alt', 'html__alt'):
            if titleattr in kw:
                title = kw[titleattr]
                break
        if title:
            return '[Image:%s]' % title
        return '[Image]'

    # generic transclude/include:
    def transclusion(self, on, data=None, **kw):
        attrib = {}
        if data:
            attrib[self.tag_data] = data
        return self.handle_on(on, self.tag_object, attrib)
    def transclusion_param(self, **kw):
        raise NotImplementedError('transclusion_param')

    def smiley(self, text):
        # TODO
        return ''

    def nowikiword(self, text):
        self._stack_top_append(text)
        return ''

    # Text and Text Attributes ###########################################

    def text(self, text, **kw):
        self._stack_top_append(unicode(text))
        return ''

    def _text(self, text):
        raise NotImplementedError('_text')

    def strong(self, on, **kw):
        return self.handle_on(on, self.tag_strong)

    def emphasis(self, on, **kw):
        return self.handle_on(on, self.tag_emphasis)

    def underline(self, on, **kw):
        # TODO
        return ''

    def highlight(self, on, **kw):
        raise NotImplementedError('highlight')

    def sup(self, on, **kw):
        # TODO
        return ''

    def sub(self, on, **kw):
        # TODO
        return ''

    def strike(self, on, **kw):
        # TODO
        return ''

    def code(self, on, **kw):
        if on:
            self._stack_push(ET.Element(ET.QName('code', namespaces.moin_page)))
        else:
            self._stack_pop()
        return ''

    def preformatted(self, on, **kw):
        self.in_pre = on != 0
        return self.handle_on(on, self.tag_blockcode)

    def small(self, on, **kw):
        attrib = {self.tag_font_size: '85%'}
        return self.handle_on(on, self.tag_span, attrib)

    def big(self, on, **kw):
        attrib = {self.tag_font_size: '120%'}
        return self.handle_on(on, self.tag_span, attrib)

    # special markup for syntax highlighting #############################

    def code_area(self, on, code_id, code_type='code', show=0, start=-1, step=-1):
        # TODO
        return ''

    def code_line(self, on):
        # TODO
        return ''

    def code_token(self, tok_text, tok_type):
        # TODO
        return ''

    # Paragraphs, Lines, Rules ###########################################

    def linebreak(self, preformatted=1):
        raise NotImplementedError('linebreak')

    def paragraph(self, on, **kw):
        self.in_p = on != 0
        return self.handle_on(on, self.tag_p)

    def rule(self, size=0, **kw):
        self._stack_top_append(ET.Element(self.tag_separator))
        return ''

    def icon(self, type):
        raise NotImplementedError('icon')
        return type

    # Lists ##############################################################

    def number_list(self, on, type=None, start=None, **kw):
        attrib = {self.tag_item_label_generate: 'ordered'}
        return self.handle_on(on, self.tag_list, attrib)

    def bullet_list(self, on, **kw):
        attrib = {self.tag_item_label_generate: 'unordered'}
        return self.handle_on(on, self.tag_list, attrib)

    def listitem(self, on, **kw):
        if on:
            elem_item_body = ET.Element(self.tag_list_item_body)
            elem_item = ET.Element(self.tag_list_item,
                    children=[elem_item_body])
            # The old moin wiki parser seems to forget the list sometimes
            if self._stack[-1].tag.name != 'list':
                elem = ET.Element(self.tag_list, children=[elem_item])
            else:
                elem = elem_item
            self._stack_top_append(elem)
            self._stack.append(elem_item_body)
        else:
            self._stack_pop()
        return ''

    def definition_list(self, on, **kw):
        if on:
            self._stack_push(ET.Element(None))
        else:
            elem = self._stack_pop()
            if elem.tag is not None:
                raise ValueError

            self._stack[-1].remove(elem)

            new_list = ET.Element(self.tag_list)
            new_item = None

            for child in elem:
                if not isinstance(child, ET.Element):
                    continue

                if child.tag not in (self.tag_list_item_label,
                        self.tag_list_item_body):
                    continue

                # If we already have an item and we want to add a label
                if (new_item is not None and
                        child.tag == self.tag_list_item_label):
                    # clear it
                    new_item = None

                if not new_item:
                    new_item = ET.Element(self.tag_list_item)
                    new_list.append(new_item)

                new_item.append(child)

                # If this was a body
                if child.tag == self.tag_list_item_body:
                    # clear it
                    new_item = None

            self._stack[-1].append(new_list)

        return ''

    def definition_term(self, on, compact=0, **kw):
        return self.handle_on(on, self.tag_list_item_label)

    def definition_desc(self, on, **kw):
        return self.handle_on(on, self.tag_list_item_body)

    def heading(self, on, depth, **kw):
        attrib = {self.tag_outline_level: str(depth)}
        return self.handle_on(on, self.tag_h, attrib)

    # Tables #############################################################

    _allowed_table_attrs = {
        '': ['colspan', 'rowspan', 'abbr'],
    }

    def _checkTableAttr(self, attrs, prefix):
        """ Check table attributes

        Convert from wikitable attributes to Moine page attributes.

        @param attrs: attribute dict
        @param prefix: used in wiki table attributes
        @rtype: dict
        @return: valid table attributes
        """
        if not attrs:
            return {}

        ret = {}
        for key, val in attrs.items():
            # Ignore keys that don't start with prefix
            if prefix and key[:len(prefix)] != prefix:
                continue
            key = key[len(prefix):]
            val = val.strip('"')
            real_key = None
            if key == 'bgcolor':
                key = ET.QName('background-color', None)
            elif key == 'align':
                key = ET.QName('text-align', None)
            elif key == 'valign':
                key = ET.QName('vertical-align', None)
            elif key == 'class':
                key = ET.QName('class', namespaces.html)
            elif key == 'style':
                key = ET.QName('style', namespaces.html)
            elif prefix == '' and key in ('colspan', 'rowspan', 'abbr'):
                key = ET.QName(key, namespaces.html)
            else:
                continue
            ret[key] = val
        return ret

    def table(self, on, attrib={}, **kw):
        if on:
            elem_body = ET.Element(self.tag_table_body)
            attrib = self._checkTableAttr(attrib, 'table')
            elem = ET.Element(self.tag_table, attrib, children=[elem_body])
            self._stack_top_append(elem)
            self._stack.append(elem_body)
        else:
            self._stack_pop()
        return ''

    def table_row(self, on, attrib={}, **kw):
        attrib = self._checkTableAttr(attrib, 'row')
        return self.handle_on(on, self.tag_table_row, attrib)

    def table_cell(self, on, attrib={}, **kw):
        attrib = self._checkTableAttr(attrib, '')
        return self.handle_on(on, self.tag_table_cell, attrib)

    # Dynamic stuff / Plugins ############################################

    def macro(self, macro_obj, name, args, markup=None):
        if self.in_p:
            macro_type = 'inline'
        else:
            macro_type = 'block'
        elem = super(Formatter, self).macro(name, args, markup, macro_type)
        if elem:
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
        if not lines:
            return ''

        args = ''
        if lines[0].startswith('#!'):
            data = lines[0][2:].split(None, 1)
            if len(data) > 1:
                args = data[1]
            lines.pop(0)

        if lines and not lines[0]:
            lines.pop(0)
        if lines and not lines[-1]:
            lines.pop(-1)
        if not lines:
            return ''

        text = '\n'.join(lines)

        from MoinMoin.converter2 import default_registry as reg

        mimetype = wikiutil.MimeType(parser_name).mime_type()
        Converter = reg.get(mimetype, 'application/x-moin-document', None)

        self._stack_push(ET.Element(ET.QName('div', namespaces.moin_page)))

        if Converter:
            doc = Converter(self.request, self.page.page_name)(text)
            self._stack_top_append(doc)

        else:
            Parser = wikiutil.searchAndImportPlugin(self.request.cfg, "parser", parser_name)
            parser = Parser(text, self.request, format_args=args)

            parser.format(self)

        self._stack_pop()
        return ''

    # Other ##############################################################

    def div(self, on, **kw):
        """ open/close a blocklevel division """
        return self.handle_on(on, self.tag_div)

    def span(self, on, **kw):
        """ open/close a inline span """
        return self.handle_on(on, self.tag_span)

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
        parser.feed('<div>')
        parser.feed(markup)
        parser.feed('</div>')
        doc = parser.close()
        self._stack_top_extend(doc[:])

        return ''

    def escapedText(self, text, **kw):
        self._stack_top_append(text)
        return ''

    def comment(self, text, **kw):
        return ""

    # ID handling #################################################

    def sanitize_to_id(self, text):
        '''
        Take 'text' and return something that is a valid ID
        for this formatter.
        The default returns the first non-space character of the string.

        Because of the way this is used, it must be idempotent,
        i.e. calling it on an already sanitized id must yield the
        original id.
        '''
        return text.strip()[:1]

    def make_id_unique(self, id):
        '''
        Take an ID and make it unique in the current namespace.
        '''
        ns = self.request.include_id
        if not ns is None:
            ns = self.sanitize_to_id(ns)
        id = self.sanitize_to_id(id)
        id = self.request.make_unique_id(id, ns)
        return id

    def qualify_id(self, id):
        '''
        Take an ID and return a string that is qualified by
        the current namespace; this default implementation
        is suitable if the dot ('.') is valid in IDs for your
        formatter.
        '''
        ns = self.request.include_id
        if not ns is None:
            ns = self.sanitize_to_id(ns)
            return '%s.%s' % (ns, id)
        return id

    # Internal

    def _stack_pop(self):
        # Don't remve the last object
        if len(self._stack) == 1:
            return self._stack[0]
        elem = self._stack.pop()
        if not len(elem):
            try:
                self._stack[-1].remove(elem)
            except ValueError:
                # This is an optiomization, ignore errors
                pass
        return elem

    def _stack_push(self, elem):
        self._stack_top_append(elem)
        self._stack.append(elem)

    def _stack_top_append(self, elem):
        self._stack[-1].append(elem)

    def _stack_top_extend(self, elems):
        self._stack[-1].extend(elems)

