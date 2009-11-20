"""
MoinMoin - Pygments driven syntax highlighting input converter

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

from MoinMoin.util.mime import Type, type_moin_document
from MoinMoin.util.tree import moin_page


class Converter(object):
    def __init__(self, request, type):
        self.request, self.type = request, type

    def __call__(self, content, arguments=None):
        # XXX
        blockcode = moin_page.blockcode(children=('Pygments highlighter: %s\n' % self.type))

        for line in content:
            if len(blockcode):
                blockcode.append('\n')
            blockcode.append(line.expandtabs())

        body = moin_page.body(children=(blockcode, ))
        return moin_page.page(children=(body, ))


def _factory(_request, type_input, type_output):
    if type_moin_document.issupertype(type_output):
        if Type('text/x-diff').issupertype(type_input):
            pygments_type = 'diff'
        elif Type('text/x-irclog').issupertype(type_input):
            pygments_type = 'irc'
        elif (Type('text/x-python').issupertype(type_input) or
            Type('x-moin/format;name=python').issupertype(type_input)):
            pygments_type = 'python'
        else:
            return

        def real_factory(request):
            return Converter(request, pygments_type)
        return real_factory

from . import default_registry
default_registry.register(_factory)
