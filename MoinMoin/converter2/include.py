"""
MoinMoin - Include handling

Expands include elements in a internal Moin document.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET
import re

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.util.tree import html, moin_page, xinclude, xlink

class XPointer(list):
    """
    Simple XPointer parser
    """

    tokenizer_rules = r"""
        # Match escaped syntax elements
        \^[()^]
        |
        (?P<braket_open> \( )
        |
        (?P<braket_close> \) )
        |
        (?P<whitespace> \s+ )
        |
        # Anything else
        [^()^]+
    """
    tokenizer_re = re.compile(tokenizer_rules, re.X)

    class Entry(object):
        __slots__ = 'name', 'data'

        def __init__(self, name, data):
            self.name, self.data = name, data

        @property
        def data_unescape(self):
            data = self.data.replace('^(', '(').replace('^)', ')')
            return data.replace('^^', '^')

    def __init__(self, input):
        name = []
        stack = []

        for match in self.tokenizer_re.finditer(input):
            if match.group('braket_open'):
                stack.append([])
            elif match.group('braket_close'):
                top = stack.pop()
                if stack:
                    stack[-1].append('(')
                    stack[-1].extend(top)
                    stack[-1].append(')')
                else:
                    self.append(self.Entry(''.join(name), ''.join(top)))
                    name = []
            else:
                if stack:
                    stack[-1].append(match.group())
                elif not match.group('whitespace'):
                    name.append(match.group())

        while len(stack) > 1:
            top = stack.pop()
            stack[-1].extend(top)

        if name:
            if stack:
                data = ''.join(stack.pop())
            else:
                data = None
            self.append(self.Entry(''.join(name), None))

class Converter(object):
    tag_a = moin_page.a
    tag_div = moin_page.div
    tag_h = moin_page.h
    tag_href = xlink.href
    tag_page_href = moin_page.page_href
    tag_outline_level = moin_page.outline_level
    tag_xi_href = xinclude.href
    tag_xi_include = xinclude.include
    tag_xi_xpointer = xinclude.xpointer

    @classmethod
    def _factory(cls, request, input, output):
        if input == 'application/x-moin-document' and \
                output == 'application/x-moin-document;includes=expandall':
            return cls

    def recurse(self, elem, page_href):
        # Check if you reached a new page
        page_href_new = elem.get(self.tag_page_href)
        if page_href_new and page_href_new != page_href:
            page_href = page_href_new
            self.stack.append(page_href)
        else:
            self.stack.append(None)

        try:
            if elem.tag == self.tag_xi_include:
                href = elem.get(self.tag_xi_href)
                xpointer = elem.get(self.tag_xi_xpointer)

                xp_include_pages = None
                xp_include_sort = None
                xp_include_items = None
                xp_include_skipitems = None
                xp_include_heading = None
                xp_include_level = None

                if xpointer:
                    xp = XPointer(xpointer)
                    xp_include = None
                    xp_namespaces = {}
                    for entry in xp:
                        uri = None
                        name = entry.name.split(':', 1)
                        if len(name) > 1:
                            prefix, name = name
                            uri = xp_namespaces.get(prefix, False)
                        else:
                            name = name[0]

                        if uri is None and name == 'xmlns':
                            d_prefix, d_uri = entry.data.split('=', 1)
                            xp_namespaces[d_prefix] = d_uri
                        elif uri == moin_page.namespace and name == 'include':
                            xp_include = XPointer(entry.data)

                    if xp_include:
                        for entry in xp_include:
                            name, data = entry.name, entry.data
                            if name == 'pages':
                                xp_include_pages = data
                            elif name == 'sort':
                                xp_include_sort = data
                            elif name == 'items':
                                xp_include_items = int(data)
                            elif name == 'skipitems':
                                xp_include_skipitems = int(data)
                            elif name == 'heading':
                                xp_include_heading = data
                            elif name == 'level':
                                xp_include_level = data

                if href:
                    # We have a single page to include
                    # TODO: handle URIs
                    if href.startswith('wiki:///'):
                        include = href[8:]
                    elif href.startswith('wiki.local:'):
                        include = wikiutil.AbsPageName(page_href[8:], href[11:])

                    page = Page(self.request, include)
                    pages = ((page, 'wiki:///' + include), )

                elif xp_include_pages:
                    # We have a regex of pages to include
                    inc_match = re.compile(xp_include_pages)
                    pagelist = self.request.rootpage.getPageList(filter=inc_match.match)
                    pagelist.sort()
                    if xp_include_sort == 'descending':
                        pagelist.reverse()
                    if xp_include_skipitems is not None:
                        pagelist = pagelist[xp_include_skipitems:]
                    if xp_include_items is not None:
                        pagelist = pagelist[xp_include_items + 1:]

                    # TODO: URI
                    pages = ((Page(self.request, p), 'wiki:///' + p) for p in pagelist)

                div = ET.Element(self.tag_div)

                for page, page_href in pages:
                    if page_href in self.stack:
                        w = ('<p xmlns="%s"><strong class="error">Recursive include of "%s" forbidden</strong></p>'
                                % (html.namespace, page.page_name))
                        div.append(ET.XML(w))
                        continue
                    # TODO: Is this correct?
                    if not self.request.user.may.read(page.page_name):
                        continue

                    if xp_include_heading is not None:
                        attrib = {self.tag_href: page_href}
                        children = (xp_include_heading or page.split_title(), )
                        elem_a = ET.Element(self.tag_a, attrib, children=children)
                        attrib = {self.tag_outline_level: xp_include_level or '1'}
                        elem_h = ET.Element(self.tag_h, attrib, children=(elem_a, ))
                        div.append(elem_h)

                    page_doc = page.convert_input_cache(self.request)
                    page_doc.tag = self.tag_div
                    self.recurse(page_doc, page_href)
                    div.append(page_doc)

                return div

            for i in xrange(len(elem)):
                child = elem[i]
                if isinstance(child, ET.Node):
                    ret = self.recurse(child, page_href)
                    if ret:
                        elem[i] = ret
        finally:
            self.stack.pop()

    def __init__(self, request):
        self.request = request

    def __call__(self, tree):
        self.stack = []

        self.recurse(tree, None)

        return tree

from _registry import default_registry
default_registry.register(Converter._factory)
