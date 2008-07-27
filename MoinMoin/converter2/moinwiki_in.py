"""
MoinMoin - Moin Wiki input converter

@copyright: 2008 MoinMoin:BastianBlank (converter interface)
@license: GNU GPL, see COPYING for details.
"""

import re
from emeraldtree import ElementTree as ET

from MoinMoin.util import namespaces
from MoinMoin.converter2._wiki_macro import ConverterMacro

class Rules:
    pass

class Converter(ConverterMacro):
    @classmethod
    def _factory(cls, input, output):
        if input == 'text/moin-wiki;disabled' and output == 'application/x-moin-document':
            return cls

    def __init__(self, request, page_name=None, args=None):
        super(Converter, self).__init__(request)
        self.page_name = page_name

    def __call__(self, text):
        tag = ET.QName('page', namespaces.moin_page)
        tag_page_href = ET.QName('page-href', namespaces.moin_page)

        attrib = {}
        if self.page_name is not None:
            attrib[tag_page_href] = 'wiki:///' + self.page_name

        self.root = ET.Element(tag, attrib=attrib)
        self._stack = [self.root]
        return self.root

from _registry import default_registry
default_registry.register(Converter._factory)
