"""
MoinMoin - Link converter

Expands all links in a internal Moin document. This includes interwiki and
special wiki links.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

from flask import flaskg
from werkzeug import url_decode, url_encode

from MoinMoin import wikiutil
from MoinMoin.util.iri import Iri, IriPath
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

    def _get_do(self, query):
        """
        get 'do' value from query string and remove do=value from querystring

        Note: we can't use url_decode/url_encode from e.g. werkzeug because
              url_encode quotes the qs values (and Iri code will quote them again)
        """
        do = None
        separator = '&'
        result = []
        if query:
            for kv in query.split(separator):
                if not kv:
                    continue
                if '=' in kv:
                    k, v = kv.split('=', 1)
                else:
                    k, v = kv, ''
                if k == 'do':
                    do = v
                    continue # we remove do=xxx from qs
                result.append(u'%s=%s' % (k, v))
        if result:
            query = separator.join(result)
        else:
            query = None
        return do, query

    # TODO: Deduplicate code
    def handle_wiki(self, elem, input):
        do, query = self._get_do(input.query)
        link = Iri(query=query, fragment=input.fragment)

        if input.authority:
            # interwiki link
            wikitag, wikiurl, wikitail, err = wikiutil.resolve_interwiki(self.request, input.authority, input.path[1:])
            if not err:
                elem.set(html.class_, 'interwiki')
                if do is not None:
                    # this will only work for wikis with compatible URL design
                    # for other wikis, don't use do=... in your interwiki links
                    wikitail = '/+' + do + wikitail
                base = Iri(wikiutil.join_wiki(wikiurl, wikitail))
            else:
                # TODO (for now, we just link to Self:item_name in case of
                # errors, see code below)
                pass
        else:
            err = False

        if not input.authority or err:
            # local wiki link
            if do is not None:
                link.path = IriPath('+' + do + '/') + input.path[1:]
            else:
                link.path = input.path[1:]
            base = self.url_root

        elem.set(self._tag_xlink_href, base + link)

    def handle_wikilocal(self, elem, input, page):
        do, query = self._get_do(input.query)
        link = Iri(query=query, fragment=input.fragment)

        if input.path:
            path = input.path

            if path[0] == '':
                # /subitem
                tmp = page.path[1:]
                tmp.extend(path[1:])
                path = tmp
            elif path[0] == '..':
                # ../sisteritem
                path = page.path[1:] + path[1:]

            if not flaskg.storage.has_item(unicode(path)):
                elem.set(html.class_, 'nonexistent')
        else:
            path = page.path[1:]

        if do is not None:
            link.path = IriPath('+' + do + '/') + path
        else:
            link.path = path
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

        self.links.add(unicode(path))

    def get_links(self):
        """
        return a list of unicode link target item names
        """
        return list(self.links)


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(ConverterExternOutput._factory, type_moin_document, type_moin_document)
default_registry.register(ConverterItemLinks._factory, type_moin_document, type_moin_document)
