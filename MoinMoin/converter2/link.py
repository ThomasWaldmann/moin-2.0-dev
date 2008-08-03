"""
MoinMoin - Link converter

Expands all links in a internal Moin document. This includes interwiki and
special wiki links.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin import wikiutil
from MoinMoin.util import namespaces

class ConverterBase(object):
    tag_href = ET.QName('href', namespaces.xlink)
    tag_page_href = ET.QName('page-href', namespaces.moin_page)

    def handle_wiki(self, link):
        pass

    def handle_wikilocal(self, link, page_name):
        pass

    def recurse(self, elem, page_href):
        page_href = elem.get(self.tag_page_href, page_href)

        href = elem.get(self.tag_href, None)
        if href is not None:
            yield elem, href, page_href

        for child in elem:
            if isinstance(child, ET.Node):
                for i in self.recurse(child, page_href):
                    yield i

    def __init__(self, request):
        self.request = request

    def __call__(self, tree):
        for elem, href, page_href in self.recurse(tree, None):
            new_href = None
            if href.startswith('wiki.local:'):
                if page_href.startswith('wiki:///'):
                    page_name = page_href[8:]
                else:
                    page_name = ''
                new_href = self.handle_wikilocal(href[11:], page_name)
            elif href.startswith('wiki://'):
                new_href = self.handle_wiki(href[7:])
            if new_href is not None:
                elem.set(self.tag_href, new_href)
        return tree

class ConverterExternOutput(ConverterBase):
    @classmethod
    def _factory(cls, request, input, output):
        if input == 'application/x-moin-document' and \
                output == 'application/x-moin-document;links=extern':
            return cls

    # TODO: Deduplicate code
    def handle_wiki(self, link):
        wikitag, link = link.split('/', 1)

        if wikitag and wikitag != 'Self':
            wikitag, wikiurl, wikitail, err = wikiutil.resolve_interwiki(self.request, wikitag, link)

            if not err and wikitag != 'Self':
                # TODO query string
                return wikiutil.join_wiki(wikiurl, wikitail)

        try:
            link, anchor = link.rsplit("#", 1)
        except ValueError:
            anchor = None

        if anchor:
            link = link + '#' + wikiutil.url_quote_plus(anchor)

        # TODO query string
        return self.request.getScriptname() + '/' + link

    def handle_wikilocal(self, link, page_name):
        if ':' in link:
            wiki_name, link = link.split(':', 1)

            # TODO
            if wiki_name in ('attachment', 'drawing'):
                return None

            if wiki_name == 'mailto':
                return 'mailto:' + link

            wikitag, wikiurl, wikitail, err = wikiutil.resolve_interwiki(self.request, wiki_name, link)

            if not err and wikitag != 'Self':
                # TODO query string
                return wikiutil.join_wiki(wikiurl, wikitail)

        # handle anchors
        try:
            link, anchor = link.rsplit("#", 1)
        except ValueError:
            anchor = None

        if not link:
            link = page_name

        # handle relative links
        link = wikiutil.AbsPageName(page_name, link)

        if anchor:
            link = link + '#' + wikiutil.url_quote_plus(anchor)

        # TODO query string
        return self.request.getScriptname() + '/' + link

class ConverterPagelinks(ConverterBase):
    @classmethod
    def _factory(cls, request, input, output):
        if input == 'application/x-moin-document' and \
                output == 'application/x-moin-document;links=pagelinks':
            return cls

    def handle_wikilocal(self, link, page_name):
        if ':' in link:
            wiki_name, link = link.split(':', 1)

            if wiki_name in ('attachment', 'drawing', 'mailto'):
                return

            wikitag, wikiurl, wikitail, err = wikiutil.resolve_interwiki(self.request, wiki_name, link)

            if not err and wikitag != 'Self':
                return None

        # handle anchors
        try:
            link, anchor = link.rsplit("#", 1)
        except ValueError:
            pass

        if link:
            self.links.add(link)

    def __call__(self, tree):
        self.links = set()

        super(ConverterPagelinks, self).__call__(tree)

        return self.links

from _registry import default_registry
default_registry.register(ConverterExternOutput._factory)
default_registry.register(ConverterPagelinks._factory)
