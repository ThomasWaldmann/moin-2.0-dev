"""
MoinMoin - Link converter

Expands all links in a internal Moin document. This includes interwiki and
special wiki links.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

from MoinMoin import wikiutil
from MoinMoin.util.iri import Iri
from MoinMoin.util.mime import type_moin_document
from MoinMoin.util.tree import html, moin_page, xlink

class ConverterBase(object):
    _tag_xlink_href = xlink.href

    def handle_wiki(self, elem, link):
        pass

    def handle_wikilocal(self, elem, link, page_name):
        pass

    def __init__(self, request):
        self.request = request
        # TODO: request should hold this in a parsed way
        self.url_root = Iri(request.url_root)

    def __call__(self, elem, page=None,
            __tag_page_href=moin_page.page_href, __tag_href=_tag_xlink_href):
        new_page_href = elem.get(__tag_page_href)
        if new_page_href:
            page = Iri(new_page_href)

        href = elem.get(__tag_href)
        if href:
            href = Iri(href)
            if href.scheme == 'wiki.local':
                self.handle_wikilocal(elem, href, page)
            elif href.scheme == 'wiki':
                self.handle_wiki(elem, href)

        for child in elem.iter_elements():
            self(child, page)

        return elem

class ConverterExternOutput(ConverterBase):
    @classmethod
    def _factory(cls, input, output, request, links=None, **kw):
        if links == 'extern':
            return cls(request)

    # TODO: Deduplicate code
    def handle_wiki(self, elem, input):
        link = Iri(query=input.query, fragment=input.fragment)

        if input.authority:
            wikitag, wikiurl, wikitail, err = wikiutil.resolve_interwiki(self.request, input.authority, input.path[1:])

            if not err:
                output = Iri(wikiutil.join_wiki(wikiurl, wikitail)) + link

                elem.set(html.class_, 'interwiki')
            else:
                # TODO
                link.path = input.path[1:]
                output = self.url_root + link

        else:
            link.path = input.path[1:]
            output = self.url_root + link

        elem.set(self._tag_xlink_href, output)

    def handle_wikilocal(self, elem, input, page):
        link = Iri(query=input.query, fragment=input.fragment)

        if input.path:
            path = input.path

            if path[0] == '':
                tmp = page.path[1:]
                tmp.extend(path[1:])
                link.path = tmp
            elif path[0] == '..':
                link.path = page.path[1:] + path[1:]
            else:
                link.path = path

            if not self.request.storage.has_item(unicode(link.path)):
                elem.set(html.class_, 'nonexistent')
        else:
            link.path = page.path[1:]

        output = self.url_root + link

        elem.set(self._tag_xlink_href, output)

class ConverterItemLinks(ConverterBase):
    """
    determine all links to other wiki items in this document
    """
    @classmethod
    def _factory(cls, input, output, request, links=None, **kw):
        if links == 'itemlinks':
            return cls(request)

    def __init__(self, request):
        super(ConverterItemLinks, self).__init__(request)
        self.links = set()

    def handle_wikilocal(self, elem, input, page):
        if not input.path or ':' in input.path:
            return

        path = input.path

        if path[0] == '':
            p = page.path[1:] 
            p.extend(path[1:])
            path = p
        elif path[0] == '..':
            path = page.path[1:] + path[1:]

        self.links.add(path)

    def get_links(self):
        """
        return a list of unicode link target item names
        """
        return [unicode(link) for link in self.links]


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(ConverterExternOutput._factory, type_moin_document, type_moin_document)
default_registry.register(ConverterItemLinks._factory, type_moin_document, type_moin_document)
