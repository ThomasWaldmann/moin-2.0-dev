"""
MoinMoin - Compatibility input converter

Uses old-style parser if there is one for the requested type and the
compatibility formatter to create a converter.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import re
from emeraldtree import ElementTree as ET

from MoinMoin import config, wikiutil
from MoinMoin.Page import Page
from MoinMoin.util import namespaces, uri

class Converter(object):
    tag_page = ET.QName('page', namespaces.moin_page)
    tag_page_href = ET.QName('page-href', namespaces.moin_page)

    def __init__(self, request, page_url, args, parser, formatter):
        self.request, self.page_url, self.args = request, page_url, args
        self.parser, self.formatter = parser, formatter

    def __call__(self, content):
        attrib = {}
        if self.page_url is not None:
            attrib[self.tag_page_href] = self.page_url

        self.root = ET.Element(self.tag_page, attrib=attrib)

        text = '\n'.join(content)
        # TODO: Remove Page object
        # TODO: unicode URI
        page = Page(self.request, uri.Uri(self.page_url).path.decode('utf-8')[1:])

        parser = self.parser(text, self.request, format_args=self.args)
        formatter = self.formatter(self.request, page)

        parser.format(formatter)

        self.root.extend(formatter.root)

        return self.root

def _factory(request, input, output):
    if output == 'application/x-moin-document':
        try:
            Parser = wikiutil.searchAndImportPlugin(request.cfg, "parser", input)
            Formatter = wikiutil.searchAndImportPlugin(request.cfg, "formatter", 'compatibility')
        except wikiutil.PluginMissingError:
            return

        cls = type('Converter.%s' % str(input), (Converter, ), {})
        def init(self, request, page_url=None, args=None):
            super(cls, self).__init__(request, page_url, args, Parser, Formatter)
        cls.__init__ = init

        return cls

from _registry import default_registry
# Need to register ourself after all normal parsers but before the wildcard
default_registry.register(_factory, default_registry.PRIORITY_MIDDLE + 1)
