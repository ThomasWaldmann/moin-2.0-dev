"""
MoinMoin - Link converter

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree

from MoinMoin import wikiutil
from MoinMoin.util import namespaces

class ConverterExternOutput(object):
    @classmethod
    def _factory(cls, input, output):
        if input == 'application/x-moin-document' and \
                output == 'application/x-moin-document;links=extern':
            return cls()

    def handle_wikilocal(self, link):
        if ':' in link:
            wiki_name, link = link.split(':', 1)

            # TODO
            if wiki_name in ('attachment', 'drawing', 'image'):
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

        current_page = self.page.page_name
        if not link:
            link = current_page

        # handle relative links
        link = wikiutil.AbsPageName(current_page, link)

        if anchor:
            link = link + '#' + wikiutil.url_quote_plus(anchor)

        # TODO query string
        return self.request.getScriptname() + '/' + link

    def __call__(self, tree, request, page):
        self.request, self.page = request, page

        tag = ElementTree.QName('href', namespaces.xlink)
        for elem in tree.iter():
            href = elem.get(tag, None)
            if href is not None:
                if href.startswith('wiki.local:'):
                    href = self.handle_wikilocal(href[11:])
                    if href is not None:
                        elem.set(tag, href)
        return tree

from _registry import default_registry
default_registry.register(ConverterExternOutput._factory)
