"""
MoinMoin - Tests for MoinMoin.converter2.creole_in

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.converter2.creole_in import *

namespaces_string = 'xmlns="%s"' % namespaces.moin_page
namespaces_string_xlink = 'xmlns:xlink="%s"' % namespaces.xlink

namespaces_list = {
    namespaces.moin_page: '',
    namespaces.xlink: 'xlink',
}

def serialize(elem, **options):
    from cStringIO import StringIO
    file = StringIO()
    tree = ElementTree.ElementTree(elem)
    tree.write(file, namespaces = namespaces_list, **options)
    return file.getvalue()

class TestConverter(object):
    def setup_class(self):
        self.conv = Converter()

    def test_base(self):
        pairs = [
            ('Text',
                '<page %s><p>Text</p></page>' % namespaces_string),
            ('Text\nTest',
                '<page %s><p>Text\nTest</p></page>' % namespaces_string),
            ('Text\n\nTest',
                '<page %s><p>Text</p><p>Test</p></page>' % namespaces_string),
            (r'Line\\Break',
                '<page %s><p>Line<line-break />Break</p></page>' % namespaces_string),
            ('http://moinmo.in/',
                '<page %s %s><p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p></page>' % (namespaces_string, namespaces_string_xlink)),
            ('~http://moinmo.in/',
                '<page %s><p>http://moinmo.in/</p></page>' % namespaces_string),
            ('[[http://moinmo.in/]]',
                '<page %s %s><p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p></page>' % (namespaces_string, namespaces_string_xlink)),
            ('[[http://moinmo.in/|MoinMoin]]',
                '<page %s %s><p><a xlink:href="http://moinmo.in/">MoinMoin</a></p></page>' % (namespaces_string, namespaces_string_xlink)),
            ('[[MoinMoin]]',
                '<page %s %s><p><a xlink:href="wiki:/MoinMoin">MoinMoin</a></p></page>' % (namespaces_string, namespaces_string_xlink)),
        ]
        for i in pairs:
            yield (self._do,) + i

    def test_emphasis(self):
        pairs = [
            ('//Emphasis//',
                '<page %s><p><emphasis>Emphasis</emphasis></p></page>' % namespaces_string),
            ('**Strong**',
                '<page %s><p><strong>Strong</strong></p></page>' % namespaces_string),
            ('//**Both**//',
                '<page %s><p><emphasis><strong>Both</strong></emphasis></p></page>' % namespaces_string),
            ('**//Both//**',
                '<page %s><p><strong><emphasis>Both</emphasis></strong></p></page>' % namespaces_string),
            ('Text //Emphasis\n\nText',
                '<page %s><p>Text <emphasis>Emphasis</emphasis></p><p>Text</p></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do,) + i

    def test_heading(self):
        pairs = [
            ('= Heading 1',
                '<page %s><h outline-level="1">Heading 1</h></page>' % namespaces_string),
            ('== Heading 2',
                '<page %s><h outline-level="2">Heading 2</h></page>' % namespaces_string),
            ('=== Heading 3',
                '<page %s><h outline-level="3">Heading 3</h></page>' % namespaces_string),
            ('==== Heading 4',
                '<page %s><h outline-level="4">Heading 4</h></page>' % namespaces_string),
            ('===== Heading 5',
                '<page %s><h outline-level="5">Heading 5</h></page>' % namespaces_string),
            ('====== Heading 6',
                '<page %s><h outline-level="6">Heading 6</h></page>' % namespaces_string),
            ('= Heading 1 =',
                '<page %s><h outline-level="1">Heading 1</h></page>' % namespaces_string),
            ('== Heading 2 ==',
                '<page %s><h outline-level="2">Heading 2</h></page>' % namespaces_string),
            ('=== Heading 3 ===',
                '<page %s><h outline-level="3">Heading 3</h></page>' % namespaces_string),
            ('==== Heading 4 ====',
                '<page %s><h outline-level="4">Heading 4</h></page>' % namespaces_string),
            ('===== Heading 5 =====',
                '<page %s><h outline-level="5">Heading 5</h></page>' % namespaces_string),
            ('====== Heading 6 ======',
                '<page %s><h outline-level="6">Heading 6</h></page>' % namespaces_string),
            ('=== Heading 3',
                '<page %s><h outline-level="3">Heading 3</h></page>' % namespaces_string),
            ('=== Heading 3 =',
                '<page %s><h outline-level="3">Heading 3</h></page>' % namespaces_string),
            ('=== Heading 3 ==',
                '<page %s><h outline-level="3">Heading 3</h></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do,) + i

    def _do(self, input, output):
        out = self.conv(input)
        assert serialize(out) == output

