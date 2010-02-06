"""
MoinMoin - Compatibility input converter

Uses old-style parser if there is one for the requested type and the
compatibility formatter to create a converter.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

from MoinMoin import wikiutil
from MoinMoin.formatter.compatibility import Formatter
from MoinMoin.util.mime import Type, type_moin_document
from MoinMoin.util.tree import moin_page

class Converter(object):
    def __init__(self, request):
        self.request = request

    def __call__(self, content):
        text = '\n'.join(content)

        formatter = Formatter(self.request, 'Parser ' + self.name)
        parser = self.parser(text, formatter.request, format_args='')

        parser.format(formatter)

        body = moin_page.body()

        body.extend(formatter.root)

        return moin_page.page(children=(body, ))

def _factory(request, input, output, **kw):
    """
    Creates a class dynamically, which uses the matching old-style parser and
    compatibility formatter.
    """
    if (type_moin_document.issupertype(output) and
            Type('x-moin/format').issupertype(input)):
        try:
            name = input.parameters.get('name')
            parser = wikiutil.searchAndImportPlugin(
                    request.cfg, "parser", name)
        # If the plugin is not available, ignore it
        except wikiutil.PluginMissingError:
            return

        return type('Converter.%s' % str(name), (Converter, ), {'name': name, 'parser': parser})

from . import default_registry
# Need to register ourself after all normal parsers but before the wildcard
default_registry.register(_factory, default_registry.PRIORITY_MIDDLE + 1)

