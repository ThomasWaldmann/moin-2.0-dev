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
from MoinMoin.util import uri
from MoinMoin.util.tree import html, moin_page, xlink

class ConverterBase(object):
    tag_class = html.class_
    tag_href = xlink.href
    tag_page_href = moin_page.page_href

    def handle_wiki(self, elem, link):
        pass

    def handle_wikilocal(self, elem, link, page_name):
        pass

    def recurse(self, elem, page_name):
        new_page_href = elem.get(self.tag_page_href)
        if new_page_href:
            # TODO: unicode URI
            u = uri.Uri(new_page_href)
            if u.authority == '' and u.path.startswith('/'):
                page_name = u.path[1:].decode('utf-8')

        href = elem.get(self.tag_href, None)
        if href is not None:
            yield elem, uri.Uri(href), page_name

        for child in elem:
            if isinstance(child, ET.Node):
                for i in self.recurse(child, page_name):
                    yield i

    def __init__(self, request):
        self.request = request

    def __call__(self, tree):
        for elem, href, page_name in self.recurse(tree, None):
            if href.scheme == 'wiki.local':
                self.handle_wikilocal(elem, href, page_name)
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
        ret = uri.Uri(query=input.query, fragment=input.fragment)

        if input.authority:
            wikitag, wikiurl, wikitail, err = wikiutil.resolve_interwiki(self.request, input.authority, input.path[1:])

            if not err:
                tmp = uri.Uri(wikiutil.join_wiki(wikiurl, wikitail))
                ret.scheme, ret.authority, ret.path = tmp.scheme, tmp.authority, tmp.path
                if tmp.query:
                    if ret.query:
                        ret.query += ';' + tmp.query
                    else:
                        ret.query = tmp.query
                if tmp.fragment:
                    if ret.fragment:
                        ret.fragment += ';' + tmp.fragment
                    else:
                        ret.fragment = tmp.fragment

                elem.set(self.tag_class, 'interwiki')
            else:
                # TODO
                pass

        else:
            ret.path = self.request.getScriptname() + input.path

        elem.set(self.tag_href, str(ret))

    def handle_wikilocal(self, elem, input, page_name):
        ret = uri.Uri(query=input.query, fragment=input.fragment)
        link = None

        if input.path:
            if ':' in input.path:
                wiki_name, link = input.path.split(':', 1)

                # TODO
                if wiki_name in ('attachment', 'drawing'):
                    return

                if wiki_name == 'mailto':
                    elem.set(self.tag_href, 'mailto:' + link)
                    return

                # TODO: Remove users
                return

            else:
                # TODO: unicode URI
                link = input.path.decode('utf-8')

        else:
            link = page_name

        if link:
            abs_page_name = wikiutil.AbsPageName(page_name, link)
            page = Page(self.request, abs_page_name, None)
            if not page.exists():
                elem.set(self.tag_class, 'nonexistent')

            # TODO: unicode URI
            ret.path = self.request.getScriptname() + '/' + abs_page_name.encode('utf-8')

        elem.set(self.tag_href, str(ret))

class ConverterPagelinks(ConverterBase):
    @classmethod
    def _factory(cls, request, input, output):
        if input == 'application/x-moin-document' and \
                output == 'application/x-moin-document;links=pagelinks':
            return cls

    def handle_wikilocal(self, elem, input, page_name):
        if not input.path or ':' in input.path:
            return

        if input.path:
            # TODO: unicode URI
            link = wikiutil.AbsPageName(page_name, input.path.decode('utf-8'))
            self.links.add(link)

    def __call__(self, tree):
        self.links = set()

        super(ConverterPagelinks, self).__call__(tree)

        return self.links

from _registry import default_registry
default_registry.register(ConverterExternOutput._factory)
default_registry.register(ConverterPagelinks._factory)
