# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Simple text input converter.

    It just puts all text into a code block.

    @copyright: 2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin.util import namespaces

class Converter(object):
    """
    Parse the raw text and create a document object
    that can be converted into output using Emitter.
    """

    @classmethod
    def _factory(cls, request, input, output):
        if input.startswith('text/') and output == 'application/x-moin-document':
            return cls

    def __init__(self, request, page_url=None, args=None):
        self.page_url = page_url

    def __call__(self, content):
        """Parse the text and return DOM tree."""

        tag = ET.QName('page', namespaces.moin_page)
        tag_page_href = ET.QName('page-href', namespaces.moin_page)

        attrib = {}
        if self.page_url:
            attrib[tag_page_href] = self.page_url

        root = ET.Element(tag, attrib=attrib)

        blockcode = ET.Element(ET.QName('blockcode', namespaces.moin_page))

        for line in content:
            if len(blockcode):
                blockcode.append('\n')
            blockcode.append(line.expandtabs())

        root.append(blockcode)
        return root

from _registry import default_registry
default_registry.register(Converter._factory, default_registry.PRIORITY_LAST)
