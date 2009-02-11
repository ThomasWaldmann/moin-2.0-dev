"""
MoinMoin - Link converter

Expands all links in a internal Moin document. This includes interwiki and
special wiki links.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET
import urllib

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.util import iri
from MoinMoin.util.tree import html, moin_page, xlink

class ConverterBase(object):
    tag_class = html.class_
    tag_href = xlink.href
    tag_page_href = moin_page.page_href

    def handle_wiki(self, elem, link):
        pass

    def handle_wikilocal(self, elem, link, page_name):
        pass

    def recurse(self, elem, page):
        new_page_href = elem.get(self.tag_page_href)
        if new_page_href:
            page = iri.Iri(new_page_href)

        href = elem.get(self.tag_href)
        if href:
            yield elem, iri.Iri(href), page

        for child in elem:
            if isinstance(child, ET.Node):
                for i in self.recurse(child, page):
                    yield i

    def __init__(self, request):
        self.request = request

    def __call__(self, tree):
        for elem, href, page in self.recurse(tree, None):
            if href.scheme == 'wiki.local':
                self.handle_wikilocal(elem, href, page)
            elif href.scheme == 'wiki':
                self.handle_wiki(elem, href)
        return tree

class ConverterExternOutput(ConverterBase):
    @classmethod
    def _factory(cls, request, input, output):
        if input == 'application/x-moin-document' and \
                output == 'application/x-moin-document;links=extern':
            return cls

    # TODO: Deduplicate code
    def handle_wiki(self, elem, input):
        link = iri.Iri(query=input.query, fragment=input.fragment)

        if input.authority:
            wikitag, wikiurl, wikitail, err = wikiutil.resolve_interwiki(self.request, input.authority, input.path[1:])

            if not err:
                output = iri.Iri(wikiutil.join_wiki(wikiurl, wikitail)) + link

                elem.set(self.tag_class, 'interwiki')
            else:
                # TODO
                pass

        else:
            link.path = input.path
            output = iri.Iri(self.request.url_root) + link

        elem.set(self.tag_href, unicode(output))

    def handle_wikilocal(self, elem, input, page):
        link = iri.Iri(query=input.query, fragment=input.fragment)

        if input.path:
            path = input.path

            if path[0] == '':
                # TODO: Don't missuse __add__
                link.path = iri.IriPath(segments=page.path[1:] + path[1:])
            elif path[0] == '..':
                link.path = iri.IriPath(page.path[1:]) + path[1:]
            else:
                link.path = path

            page = Page(self.request, unicode(link.path), None)
            if not page.exists():
                elem.set(self.tag_class, 'nonexistent')
        else:
            link.path = page.path

        output = iri.Iri(self.request.url_root) + link

        elem.set(self.tag_href, unicode(output))

class ConverterPagelinks(ConverterBase):
    @classmethod
    def _factory(cls, request, input, output):
        if input == 'application/x-moin-document' and \
                output == 'application/x-moin-document;links=pagelinks':
            return cls

    def handle_wikilocal(self, elem, input, page):
        if not input.path or ':' in input.path:
            return

        path = input.path

        if path[0] == '':
            # TODO: Don't missuse __add__
            path = iri.IriPath(segments=page.path[1:] + path[1:])
        elif path[0] == '..':
            path = iri.IriPath(page.path[1:]) + path[1:]

        self.links.add(unicode(path))

    def __call__(self, tree):
        self.links = set()

        super(ConverterPagelinks, self).__call__(tree)

        return self.links

from _registry import default_registry
default_registry.register(ConverterExternOutput._factory)
default_registry.register(ConverterPagelinks._factory)
