"""
MoinMoin - Tests for MoinMoin.converter2._wiki_macro

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree.ElementTree import ElementTree
import py.test

from MoinMoin.converter2._wiki_macro import *

namespaces_string = 'xmlns="%s"' % namespaces.moin_page

namespaces_list = {
    namespaces.moin_page: '',
}

def serialize(elem, **options):
    from cStringIO import StringIO
    file = StringIO()
    tree = ElementTree(elem)
    tree.write(file, namespaces=namespaces_list, **options)
    return file.getvalue()

class TestConverter(object):
    def setup_class(self):
        self.conv = ConverterMacro()

    def test(self):
        pairs = [
            ('BR', None, 'text',
                None,
                '<line-break %s />' % namespaces_string),
            ('FootNote', 'note', 'text',
                None,
                '<note note-class="footnote" %s><note-body>note</note-body></note>' % namespaces_string),
        ]
        for name, args, text, output_block, output_inline in pairs:
            yield (self._do, name, args, text, 'block', output_block)
            yield (self._do, name, args, text, 'inline', output_inline)

    def _do(self, name, args, text, type, output):
        out = self.conv.macro(name, args, text, type)
        if output is not None or out is not None:
            assert serialize(out) == output

