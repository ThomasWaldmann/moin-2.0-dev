"""
MoinMoin - Tests for MoinMoin.converter2.link

@copyright: 2007 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.converter2.link import *

class TestConverterExternOutput(object):
    def setup_class(self):
        self.conv = ConverterExternOutput(self.request)

    def test_wiki(self):
        pairs = [
            ('wiki:///Test',
                './Test'),
            ('wiki:///Test?mode=raw',
                './Test?mode=raw'),
            ('wiki:///Test#anchor',
                './Test#anchor'),
            ('wiki:///Test?mode=raw#anchor',
                './Test?mode=raw#anchor'),
        ]
        for i in pairs:
            yield (self._do_wiki, ) + i

    def test_wikilocal(self):
        pairs = [
            ('wiki.local:',
                'wiki:///Root',
                './Root'),
            ('wiki.local:Test',
                'wiki:///Root',
                './Test'),
            ('wiki.local:Test',
                'wiki:///Root/Sub',
                './Test'),
            ('wiki.local:/Test',
                'wiki:///Root',
                './Root/Test'),
            ('wiki.local:/Test',
                'wiki:///Root/Sub',
                './Root/Sub/Test'),
            ('wiki.local:../Test',
                'wiki:///Root',
                './Test'),
            ('wiki.local:../Test',
                'wiki:///Root/Sub',
                './Root/Test'),
        ]
        for i in pairs:
            yield (self._do_wikilocal, ) + i

    def _do_wiki(self, input, output, skip=None):
        if skip:
            py.test.skip(skip)
        elem = ET.Element(None)
        self.conv.handle_wiki(elem, iri.Iri(input))
        assert elem.get(xlink.href) == output

    def _do_wikilocal(self, input, page, output, skip=None):
        if skip:
            py.test.skip(skip)
        elem = ET.Element(None)
        self.conv.handle_wikilocal(elem, iri.Iri(input), iri.Iri(page))
        assert elem.get(xlink.href) == output
