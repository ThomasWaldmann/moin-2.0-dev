"""
MoinMoin - Link converter

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin import wikiutil
from MoinMoin.util import namespaces

class ConverterExternOutput(object):
    tag_href = ET.QName('href', namespaces.xlink)
    tag_page_href = ET.QName('page-href', namespaces.moin_page)

    @classmethod
    def _factory(cls, input, output):
        if input == 'application/x-moin-document' and \
                output == 'application/x-moin-document;links=extern':
            return cls()

    def handle_wikilocal(self, link, page_name):
        if ':' in link:
            wiki_name, link = link.split(':', 1)

            # TODO
            if wiki_name in ('attachment', 'drawing'):
                return None

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

    def recurse(self, elem, page_href):
        page_href = elem.get(self.tag_page_href, page_href)

        href = elem.get(self.tag_href, None)
        if href is not None:
            yield elem, href, page_href

        for child in elem:
            if isinstance(child, ET.Node):
                for i in self.recurse(child, page_href):
                    yield i

    def __call__(self, tree, request):
        self.request = request

        for elem, href, page_href in self.recurse(tree, None):
            if href.startswith('wiki.local:'):
                if page_href.startswith('wiki:///'):
                    page_name = page_href[8:]
                else:
                    page_name = ''
                href = self.handle_wikilocal(href[11:], page_name)
                if href is not None:
                    elem.set(self.tag_href, href)
        return tree

from _registry import default_registry
default_registry.register(ConverterExternOutput._factory)
