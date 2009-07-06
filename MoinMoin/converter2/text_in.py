# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Simple text input converter.

    It just puts all text into a code block. It acts as a wildcard for
    text/* input.

    @copyright: 2008 MoinMoin:ThomasWaldmann
                2008 MoinMoin:BastianBlank
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.util.tree import moin_page

class Converter(object):
    """
    Parse the raw text and create a document object
    that can be converted into output using Emitter.
    """

    @classmethod
    def factory(cls, _request, type_input, type_output):
        if (type_input.startswith('text/') and
                type_output == 'application/x-moin-document'):
            return cls

    def __init__(self, _request):
        pass

    def __call__(self, content, page_url=None, arguments=None):
        """Parse the text and return DOM tree."""

        attrib = {}
        if page_url:
            attrib[moin_page.page_href] = unicode(page_url)

        blockcode = moin_page.blockcode()

        for line in content:
            if len(blockcode):
                blockcode.append('\n')
            blockcode.append(line.expandtabs())

        body = moin_page.body(children=(blockcode, ))
        return moin_page.page(attrib=attrib, children=(body, ))

from MoinMoin.converter2._registry import default_registry
# Register wildcards behind anything else
default_registry.register(Converter.factory, default_registry.PRIORITY_LAST)
