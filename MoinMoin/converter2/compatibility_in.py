"""
MoinMoin - Compatibility input converter

Uses old-style parser if there is one for the requested type and the
compatibility formatter to create a converter.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.util import uri
from MoinMoin.util.tree import moin_page

class Converter(object):
    def __init__(self, request, page_url, args, parser, formatter):
        self.request, self.page_url, self.args = request, page_url, args
        self.parser, self.formatter = parser, formatter

    def __call__(self, content):
        attrib = {}
        if self.page_url is not None:
            attrib[moin_page.page_href] = unicode(self.page_url)

        root = moin_page.page(attrib=attrib)

        text = '\n'.join(content)
        # TODO: unicode URI
        # TODO: Remove Page object
        page = Page(self.request, self.page_url.path.decode('utf-8')[1:])

        parser = self.parser(text, self.request, format_args=self.args or '')
        formatter = self.formatter(self.request, page)

        parser.format(formatter)

        root.extend(formatter.root)

        return root

def _factory(request, input, output):
    """
    Creates a class dynamicaly which uses the matching old-style parser and
    compatiblity formatter.
    """
    if output == 'application/x-moin-document':
        try:
            parser = wikiutil.searchAndImportPlugin(
                    request.cfg, "parser", input)
            formatter = wikiutil.searchAndImportPlugin(
                    request.cfg, "formatter", 'compatibility')
        # One of the two plugins is not available, ignore it
        except wikiutil.PluginMissingError:
            return

        cls = type('Converter.%s' % str(input), (Converter, ), {})
        def init(self, request, page_url=None, args=None):
            super(cls, self).__init__(request, page_url, args, parser, formatter)
        cls.__init__ = init

        return cls

from MoinMoin.converter2._registry import default_registry
# Need to register ourself after all normal parsers but before the wildcard
default_registry.register(_factory, default_registry.PRIORITY_MIDDLE + 1)
