"""
MoinMoin - Tests for MoinMoin.converter2.creole_in

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.converter2.creole_in import *

namespaces_string = 'xmlns="%s"' % namespaces.moin_page

def serialize(elem, **options):
    from cStringIO import StringIO
    file = StringIO()
    tree = ElementTree.ElementTree(elem)
    tree.write(file, default_namespace = namespaces.moin_page, **options)
    return file.getvalue()

class TestConverter(object):
    def setup_class(self):
        self.conv = Converter()

    def test_base(self):
        pairs = [
            ('Text',
                '<page %s><p>Text</p></page>' % namespaces_string),
            ('= Heading 1',
                '<page %s><h outline-level="1">Heading 1</h></page>' % namespaces_string),
            ('== Heading 2',
                '<page %s><h outline-level="2">Heading 2</h></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do,) + i

    def _do(self, input, output):
        out = self.conv(input)
        assert serialize(out) == output

