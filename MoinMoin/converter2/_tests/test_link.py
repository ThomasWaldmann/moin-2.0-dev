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
                'Root',
                './Root'),
            ('wiki.local:Test',
                'Root',
                './Test'),
            ('wiki.local:Test',
                'Root/Sub',
                './Test'),
            ('wiki.local:/Test',
                'Root',
                './Root/Test'),
            ('wiki.local:/Test',
                'Root/Sub',
                './Root/Sub/Test'),
            ('wiki.local:../Test',
                'Root',
                './Test'),
            ('wiki.local:../Test',
                'Root/Sub',
                './Root/Test'),
        ]
        for i in pairs:
            yield (self._do_wikilocal, ) + i

    def _do_wiki(self, input, output, skip=None):
        if skip:
            py.test.skip(skip)
        out = self.conv.handle_wiki(ET.Element(None), iri.Iri(input))
        assert out == output

    def _do_wikilocal(self, input, page_name, output, skip=None):
        if skip:
            py.test.skip(skip)
        out = self.conv.handle_wikilocal(ET.Element(None), iri.Iri(input), page_name)
        assert out == output
