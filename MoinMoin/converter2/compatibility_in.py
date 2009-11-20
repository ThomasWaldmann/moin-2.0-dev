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
from MoinMoin.util.tree import moin_page

class Converter(object):
    def __init__(self, request, page, args, parser):
        self.request, self.page, self.args = request, page, args
        self.parser = parser

    def __call__(self, content):
        attrib = {}
        if self.page is not None:
            attrib[moin_page.page_href] = unicode(self.page)

        root = moin_page.page(attrib=attrib)

        text = '\n'.join(content)

        parser = self.parser(text, self.request, format_args=self.args or '')
        formatter = Formatter(self.request, self.page)

        parser.format(formatter)

        root.extend(formatter.root)

        return root

def _factory(request, input, output):
    """
    Creates a class dynamicaly which uses the matching old-style parser and
    compatiblity formatter.
    """
    if output == 'application/x.moin.document':
        try:
            parser = wikiutil.searchAndImportPlugin(
                    request.cfg, "parser", unicode(input))
        # If the plugin is not available, ignore it
        except wikiutil.PluginMissingError:
            return

        cls = type('Converter.%s' % str(input), (Converter, ), {})
        def init(self, request, page=None, args=None):
            super(cls, self).__init__(request, page, args, parser)
        cls.__init__ = init

        return cls

from . import default_registry
# Need to register ourself after all normal parsers but before the wildcard
default_registry.register(_factory, default_registry.PRIORITY_MIDDLE + 1)
