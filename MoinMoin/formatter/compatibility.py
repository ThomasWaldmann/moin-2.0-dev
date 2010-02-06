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
from emeraldtree.html import HTMLParser

from MoinMoin import wikiutil
from MoinMoin.converter2._wiki_macro import ConverterMacro
from MoinMoin.util import iri
from MoinMoin.util.tree import html, moin_page, xlink


class CheckRequest(object):
    def __init__(self, request, name):
        self.__request, self.__name = request, name
        self.written = []

    def __getattr__(self, name):
        return getattr(self.__request, name)

    def write(self, *text):
        if not self.written:
            text_warn = ''.join((i.encode('ascii', 'replace') for i in text))
            if text_warn:
                text_warn.replace('\n', ' ')
                if len(text_warn) > 100:
                    text_warn = text_warn[:100] + '...'
                from warnings import warn
                message = self.__name + ' used request.write: ' + text_warn
                warn(message, DeprecationWarning, stacklevel=2)
        self.written.extend(text)


class Formatter(ConverterMacro):
    hardspace = ' '

    tag_a = moin_page.a
    tag_blockcode = moin_page.blockcode
    tag_data = moin_page.data
    tag_div = moin_page.div
    tag_emphasis = moin_page.emphasis
    tag_font_size = moin_page.font_size
    tag_h = moin_page.h
    tag_href = xlink.href
    tag_id = moin_page.id
    tag_item_label_generate = moin_page.item_label_generate
    tag_list = moin_page.list
    tag_list_item = moin_page.list_item
    tag_list_item_body = moin_page.list_item_body
    tag_list_item_label = moin_page.list_item_label
    tag_macro = moin_page.macro
    tag_macro_args = moin_page.macro_args
    tag_macro_name = moin_page.macro_name
    tag_macro_type = moin_page.macro_type
    tag_object = moin_page.object
    tag_outline_level = moin_page.outline_level
    tag_p = moin_page.p
    tag_src = moin_page.src
    tag_span = moin_page.span
    tag_strong = moin_page.strong
    tag_table = moin_page.table
    tag_table_body = moin_page.table_body
    tag_table_cell = moin_page.table_cell
    tag_table_row = moin_page.table_row

    tag_html_class = html.class_

    def __init__(self, request, name, **kw):
        self.request = CheckRequest(request, name)
        self._ = request.getText

        self._store_pagelinks = kw.get('store_pagelinks', 0)
        self._terse = kw.get('terse', 0)
        self.in_p = 0
        self.in_pre = 0
        self._base_depth = 0

        self._root = moin_page.body()
        self._stack = [self._root]

    @property
    def root(self):
        self._check()
        return self._root

    def handle_on(self, on, tag, attrib={}):
        if on:
            self._stack_push(tag(attrib))
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
        self._check()
        if on:
            if not pagename and page:
                pagename = page.page_name
            link = unicode(iri.Iri(scheme='wiki.local', path=pagename))
            attrib = {self.tag_href: link}
            self._stack_push(self.tag_a(attrib))
        else:
            self._stack_pop()
        return ''

    def interwikilink(self, on, interwiki='', pagename='', **kw):
        self._check()
        if on:
            link = unicode(iri.Iri(scheme='wiki',
                authority=interwiki,
                path = '/' + pagename))
            attrib = {self.tag_href: link}
            self._stack_push(self.tag_a(attrib))
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
        self._check()
        # TODO
        return ''

    def attachment_image(self, url, **kw):
        self._check()
        # TODO
        return ''

    def attachment_drawing(self, url, text, **kw):
        self._check()
        # TODO
        return ''

    def attachment_inlined(self, url, text, **kw):
        self._check()
        # TODO
        return ''

    def anchordef(self, name):
        raise NotImplementedError('anchordef')

    def line_anchordef(self, lineno):
        self._check()
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
        self._check()
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
        self._check()
        # TODO
        return ''

    def nowikiword(self, text):
        self._check()
        self._stack_top_append(text)
        return ''

    # Text and Text Attributes ###########################################

    def text(self, text, **kw):
        self._check()
        self._stack_top_append(unicode(text))
        return ''

    def _text(self, text):
        raise NotImplementedError('_text')

    def strong(self, on, **kw):
        self._check()
        return self.handle_on(on, self.tag_strong)

    def emphasis(self, on, **kw):
        self._check()
        return self.handle_on(on, self.tag_emphasis)

    def underline(self, on, **kw):
        self._check()
        # TODO
        return ''

    def highlight(self, on, **kw):
        raise NotImplementedError('highlight')

    def sup(self, on, **kw):
        self._check()
        # TODO
        return ''

    def sub(self, on, **kw):
        self._check()
        # TODO
        return ''

    def strike(self, on, **kw):
        self._check()
        # TODO
        return ''

    def code(self, on, **kw):
        self._check()
        if on:
            self._stack_push(moin_page.code())
        else:
            self._stack_pop()
        return ''

    def preformatted(self, on, **kw):
        self._check()
        self.in_pre = on != 0
        return self.handle_on(on, self.tag_blockcode)

    def small(self, on, **kw):
        self._check()
        attrib = {self.tag_font_size: '85%'}
        return self.handle_on(on, self.tag_span, attrib)

    def big(self, on, **kw):
        self._check()
        attrib = {self.tag_font_size: '120%'}
        return self.handle_on(on, self.tag_span, attrib)

    # special markup for syntax highlighting #############################

    def code_area(self, on, code_id, code_type='code', show=0, start=-1, step=-1):
        self._check()
        # TODO
        attrib = {self.tag_html_class: 'codearea'}
        return self.handle_on(on, self.tag_blockcode, attrib)

    def code_line(self, on):
        self._check()
        # TODO
        if on:
            self._stack_push(self.tag_span())
        else:
            self._stack_pop()
            self._stack_top_append('\n')
        return ''

    def code_token(self, on, tok_type):
        self._check()
        # TODO
        attrib = {self.tag_html_class: tok_type}
        return self.handle_on(on, self.tag_span, attrib)

    # Paragraphs, Lines, Rules ###########################################

    def linebreak(self, preformatted=1):
        self._check()
        self._stack_top_append(moin_page.line_break())
        return ''

    def paragraph(self, on, **kw):
        self._check()
        self.in_p = on != 0
        return self.handle_on(on, self.tag_p)

    def rule(self, size=0, **kw):
        self._check()
        self._stack_top_append(moin_page.separator())
        return ''

    def icon(self, type):
        raise NotImplementedError('icon')
        return type

    # Lists ##############################################################

    def number_list(self, on, type=None, start=None, **kw):
        self._check()
        attrib = {self.tag_item_label_generate: 'ordered'}
        return self.handle_on(on, self.tag_list, attrib)

    def bullet_list(self, on, **kw):
        self._check()
        attrib = {self.tag_item_label_generate: 'unordered'}
        return self.handle_on(on, self.tag_list, attrib)

    def listitem(self, on, **kw):
        self._check()
        if on:
            elem_item_body = self.tag_list_item_body()
            elem_item = self.tag_list_item(children=[elem_item_body])
            # The old moin wiki parser seems to forget the list sometimes
            if self._stack[-1].tag.name != 'list':
                elem = self.tag_list(children=[elem_item])
            else:
                elem = elem_item
            self._stack_top_append(elem)
            self._stack.append(elem_item_body)
        else:
            self._stack_pop()
        return ''

    def definition_list(self, on, **kw):
        self._check()
        if on:
            self._stack_push(ET.Element(None))
        else:
            elem = self._stack_pop()
            if elem.tag is not None:
                raise ValueError

            self._stack[-1].remove(elem)

            new_list = self.tag_list()
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
                    new_item = self.tag_list_item()
                    new_list.append(new_item)

                new_item.append(child)

                # If this was a body
                if child.tag == self.tag_list_item_body:
                    # clear it
                    new_item = None

            self._stack[-1].append(new_list)

        return ''

    def definition_term(self, on, compact=0, **kw):
        self._check()
        return self.handle_on(on, self.tag_list_item_label)

    def definition_desc(self, on, **kw):
        self._check()
        return self.handle_on(on, self.tag_list_item_body)

    def heading(self, on, depth, **kw):
        self._check()
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
                key = ET.QName('class', html)
            elif key == 'style':
                key = ET.QName('style', html)
            elif prefix == '' and key in ('colspan', 'rowspan', 'abbr'):
                key = ET.QName(key, html)
            else:
                continue
            ret[key] = val
        return ret

    def table(self, on, attrib={}, **kw):
        self._check()
        if on:
            elem_body = self.tag_table_body()
            attrib = self._checkTableAttr(attrib, 'table')
            elem = self.tag_table(attrib, children=[elem_body])
            self._stack_top_append(elem)
            self._stack.append(elem_body)
        else:
            self._stack_pop()
        return ''

    def table_row(self, on, attrib={}, **kw):
        self._check()
        attrib = self._checkTableAttr(attrib, 'row')
        return self.handle_on(on, self.tag_table_row, attrib)

    def table_cell(self, on, attrib={}, **kw):
        self._check()
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

        from MoinMoin.converter2 import default_registry as reg

        mimetype = wikiutil.MimeType(parser_name).mime_type()
        Converter = reg.get(self.request, mimetype, 'application/x.moin.document')

        elem = moin_page.div()
        self._stack_top_append(elem)

        doc = Converter(self.request, self.page, args)(lines)
        elem.extend(doc)

        return ''

    # Other ##############################################################

    def div(self, on, **kw):
        """ open/close a blocklevel division """
        self._check()
        return self.handle_on(on, self.tag_div)

    def span(self, on, **kw):
        """ open/close a inline span """
        self._check()
        return self.handle_on(on, self.tag_span)

    def rawHTML(self, markup):
        """ This allows emitting pre-formatted HTML markup, and should be
            used wisely (i.e. very seldom).

            Using this event while generating content results in unwanted
            effects, like loss of markup or insertion of CDATA sections
            when output goes to XML formats.
        """
        self._check()

        if not markup:
            return ''

        parser = HTMLParser()
        parser.feed('<div>')
        parser.feed(markup)
        parser.feed('</div>')
        doc = parser.close()
        self._stack_top_extend(doc[:])

        return ''

    def escapedText(self, text, **kw):
        self._check()
        self._stack_top_append(text)
        return ''

    def comment(self, text, **kw):
        self._check()
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

    def _check(self):
        if self.request.written:
            written = self.request.written
            self.request.written = []
            self.rawHTML(''.join(written))

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

