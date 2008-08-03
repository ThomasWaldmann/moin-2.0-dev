"""
MoinMoin - Compatibility input converter

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import re
from emeraldtree import ElementTree as ET

from MoinMoin import config, wikiutil
from MoinMoin.Page import Page
from MoinMoin.util import namespaces

class Converter(object):
    def __init__(self, request, page_name, args, parser, formatter):
        self.request, self.page_name, self.args = request, page_name, args
        self.parser, self.formatter = parser, formatter

    def __call__(self, text):
        tag = ET.QName('page', namespaces.moin_page)
        tag_page_href = ET.QName('page-href', namespaces.moin_page)

        attrib = {}
        if self.page_name is not None:
            attrib[tag_page_href] = 'wiki:///' + self.page_name

        self.root = ET.Element(tag, attrib=attrib)

        # TODO: Remove Page object
        page = Page(self.request, self.page_name)

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
        def init(self, request, page_name=None, args=None):
            super(cls, self).__init__(request, page_name, args, Parser, Formatter)
        cls.__init__ = init

        return cls

from _registry import default_registry
default_registry.register(_factory, default_registry.PRIORITY_MIDDLE + 1)
