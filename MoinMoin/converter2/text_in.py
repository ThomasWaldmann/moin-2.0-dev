# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Simple text input converter.

    It just puts all text into a code block. It acts as a wildcard for
    text/* input.

    @copyright: 2008 MoinMoin:ThomasWaldmann
                2008 MoinMoin:BastianBlank
    @license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

from MoinMoin.util.tree import moin_page

class Converter(object):
    """
    Parse the raw text and create a document object
    that can be converted into output using Emitter.
    """

    @classmethod
    def factory(cls, _request, type_input, type_output, **kw):
        if (type_input.type == 'text' and
                type_output == 'application/x.moin.document'):
            return cls

    def __init__(self, _request):
        pass

    def __call__(self, content, arguments=None):
        """Parse the text and return DOM tree."""

        blockcode = moin_page.blockcode()

        for line in content:
            if len(blockcode):
                blockcode.append('\n')
            blockcode.append(line.expandtabs())

        body = moin_page.body(children=(blockcode, ))
        return moin_page.page(children=(body, ))

from . import default_registry
# Register wildcards behind anything else
default_registry.register(Converter.factory, default_registry.PRIORITY_LAST)
