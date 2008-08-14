"""
MoinMoin - Tests for MoinMoin.converter2.creole_in

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.converter2.creole_in import *

namespaces_string = 'xmlns="%s"' % moin_page.namespace
namespaces_string_xlink = 'xmlns:xlink="%s"' % xlink.namespace

namespaces_list = {
    moin_page.namespace: '',
    xlink.namespace: 'xlink',
}

def serialize(elem, **options):
    from cStringIO import StringIO
    file = StringIO()
    tree = ET.ElementTree(elem)
    tree.write(file, namespaces = namespaces_list, **options)
    return file.getvalue()

class TestConverter(object):
    def setup_class(self):
        self.conv = Converter(self.request)

    def test_base(self):
        pairs = [
            ('Text',
                '<page %s><p>Text</p></page>' % namespaces_string),
            ('Text\nTest',
                '<page %s><p>Text\nTest</p></page>' % namespaces_string),
            ('Text\n\nTest',
                '<page %s><p>Text</p><p>Test</p></page>' % namespaces_string),
            ('Line\\\\Break',
                '<page %s><p>Line<line-break />Break</p></page>' % namespaces_string),
            ('Line\\\\\nBreak',
                '<page %s><p>Line<line-break />\nBreak</p></page>' % namespaces_string),
            ('http://moinmo.in/',
                '<page %s %s><p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p></page>' % (namespaces_string, namespaces_string_xlink)),
            ('[[http://moinmo.in/]]',
                '<page %s %s><p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p></page>' % (namespaces_string, namespaces_string_xlink)),
            ('[[http://moinmo.in/|MoinMoin]]',
                '<page %s %s><p><a xlink:href="http://moinmo.in/">MoinMoin</a></p></page>' % (namespaces_string, namespaces_string_xlink)),
            ('[[MoinMoin]]',
                '<page %s %s><p><a xlink:href="wiki.local:MoinMoin">MoinMoin</a></p></page>' % (namespaces_string, namespaces_string_xlink)),
            ('{{http://moinmo.in/}}',
                '<page %s %s><p><object xlink:href="http://moinmo.in/" /></p></page>' % (namespaces_string, namespaces_string_xlink)),
            ('{{http://moinmo.in/|MoinMoin}}',
                '<page %s %s><p><object alt="MoinMoin" xlink:href="http://moinmo.in/" /></p></page>' % (namespaces_string, namespaces_string_xlink)),
            ('----',
                '<page %s><separator /></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

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
            ('Text //Emphasis\n//Text',
                '<page %s><p>Text <emphasis>Emphasis\n</emphasis>Text</p></page>' % namespaces_string),
            ('Text //Emphasis\n\nText',
                '<page %s><p>Text <emphasis>Emphasis</emphasis></p><p>Text</p></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_escape(self):
        pairs = [
            ('~http://moinmo.in/',
                '<page %s><p>http://moinmo.in/</p></page>' % namespaces_string),
            ('~[[escape]]',
                '<page %s><p>[[escape]]</p></page>' % namespaces_string),
            ('~<<escape>>',
                '<page %s><p>&lt;&lt;escape&gt;&gt;</p></page>' % namespaces_string),
            ('~{~{{escape}}}',
                '<page %s><p>{{{escape}}}</p></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

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
            yield (self._do, ) + i

    def test_list(self):
        pairs = [
            ('* Item',
                '<page %s><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></page>' % namespaces_string),
            (' *Item',
                '<page %s><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></page>' % namespaces_string),
            ('*Item',
                '<page %s><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></page>' % namespaces_string),
            ('* Item\nItem',
                '<page %s><list item-label-generate="unordered"><list-item><list-item-body>Item\nItem</list-item-body></list-item></list></page>' % namespaces_string),
            ('* Item 1\n*Item 2',
                '<page %s><list item-label-generate="unordered"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></page>' % namespaces_string),
            ('* Item 1\n** Item 1.2\n* Item 2',
                '<page %s><list item-label-generate="unordered"><list-item><list-item-body>Item 1<list item-label-generate="unordered"><list-item><list-item-body>Item 1.2</list-item-body></list-item></list></list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></page>' % namespaces_string),
            ('* List 1\n\n* List 2',
                '<page %s><list item-label-generate="unordered"><list-item><list-item-body>List 1</list-item-body></list-item></list><list item-label-generate="unordered"><list-item><list-item-body>List 2</list-item-body></list-item></list></page>' % namespaces_string),
            ('# Item',
                '<page %s><list item-label-generate="ordered"><list-item><list-item-body>Item</list-item-body></list-item></list></page>' % namespaces_string),
            ('* List 1\n# List 2',
                '<page %s><list item-label-generate="unordered"><list-item><list-item-body>List 1</list-item-body></list-item></list><list item-label-generate="ordered"><list-item><list-item-body>List 2</list-item-body></list-item></list></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_macro(self):
        pairs = [
            ('<<BR>>',
                '<page %s />' % namespaces_string),
            ('Text<<BR>>Text',
                '<page %s><p>Text<line-break />Text</p></page>' % namespaces_string),
            ('<<Macro>>',
                '<page %s><macro alt="&lt;&lt;Macro&gt;&gt;" macro-args="" macro-context="block" macro-name="Macro" /></page>' % namespaces_string),
            (' <<Macro>> ',
                '<page %s><macro alt="&lt;&lt;Macro&gt;&gt;" macro-args="" macro-context="block" macro-name="Macro" /></page>' % namespaces_string),
            ('Text <<Macro>>',
                '<page %s><p>Text <macro alt="&lt;&lt;Macro&gt;&gt;" macro-args="" macro-context="inline" macro-name="Macro" /></p></page>' % namespaces_string),
            ('Text\n<<Macro>>',
                '<page %s><p>Text</p><macro alt="&lt;&lt;Macro&gt;&gt;" macro-args="" macro-context="block" macro-name="Macro" /></page>' % namespaces_string),
            ('Text\nText <<Macro>>',
                '<page %s><p>Text\nText <macro alt="&lt;&lt;Macro&gt;&gt;" macro-args="" macro-context="inline" macro-name="Macro" /></p></page>' % namespaces_string),
            ('Text\n\n<<Macro>>',
                '<page %s><p>Text</p><macro alt="&lt;&lt;Macro&gt;&gt;" macro-args="" macro-context="block" macro-name="Macro" /></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_table(self):
        pairs = [
            ('|Cell',
                '<page %s><table><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></page>' % namespaces_string),
            ('|Cell|',
                '<page %s><table><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></page>' % namespaces_string),
            ('|Cell 1|Cell 2',
                '<page %s><table><table-body><table-row><table-cell>Cell 1</table-cell><table-cell>Cell 2</table-cell></table-row></table-body></table></page>' % namespaces_string),
            ('|Cell 1|Cell 2|',
                '<page %s><table><table-body><table-row><table-cell>Cell 1</table-cell><table-cell>Cell 2</table-cell></table-row></table-body></table></page>' % namespaces_string),
            ('|Row 1\n|Row 2\n',
                '<page %s><table><table-body><table-row><table-cell>Row 1</table-cell></table-row><table-row><table-cell>Row 2</table-cell></table-row></table-body></table></page>' % namespaces_string),
            ('|Row 1|\n|Row 2|\n',
                '<page %s><table><table-body><table-row><table-cell>Row 1</table-cell></table-row><table-row><table-cell>Row 2</table-cell></table-row></table-body></table></page>' % namespaces_string),
            ('|Cell 1.1|Cell 1.2|\n|Cell 2.1|Cell 2.2|\n',
                '<page %s><table><table-body><table-row><table-cell>Cell 1.1</table-cell><table-cell>Cell 1.2</table-cell></table-row><table-row><table-cell>Cell 2.1</table-cell><table-cell>Cell 2.2</table-cell></table-row></table-body></table></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_nowiki(self):
        pairs = [
            ('{{{nowiki}}}',
                '<page %s><p><code>nowiki</code></p></page>' % namespaces_string),
            ('{{{{nowiki}}}}',
                '<page %s><p><code>{nowiki}</code></p></page>' % namespaces_string),
            ('text: {{{nowiki}}}, text',
                '<page %s><p>text: <code>nowiki</code>, text</p></page>' % namespaces_string),
            ('{{{\nnowiki\n}}}',
                '<page %s><blockcode>nowiki</blockcode></page>' % namespaces_string),
            ('{{{\nnowiki\nno\nwiki\n}}}',
                '<page %s><blockcode>nowiki\nno\nwiki</blockcode></page>' % namespaces_string),
            ('{{{nowiki}}} {{{nowiki}}}',
                '<page %s><p><code>nowiki</code> <code>nowiki</code></p></page>' % namespaces_string),
            # XXX: Is <page> correct?
            ('{{{\n#!creole background-color=red\nnowiki\n}}}',
               '<page %s><page background-color="red"><p>nowiki</p></page></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_composite(self):
        pairs = [
            ('Text\n* Item\n\nText',
                '<page %s><p>Text</p><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list><p>Text</p></page>' % namespaces_string),
            ('Text\n* Item\n= Heading',
                '<page %s><p>Text</p><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list><h outline-level="1">Heading</h></page>' % namespaces_string),
            ('Text\n* Item\n{{{\nnowiki\n}}}',
                '<page %s><p>Text</p><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list><blockcode>nowiki</blockcode></page>' % namespaces_string),
            ('Text\n* Item\n|Item',
                '<page %s><p>Text</p><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list><table><table-body><table-row><table-cell>Item</table-cell></table-row></table-body></table></page>' % namespaces_string),
            ('Text\n|Item\nText',
                '<page %s><p>Text</p><table><table-body><table-row><table-cell>Item</table-cell></table-row></table-body></table><p>Text</p></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def _do(self, input, output):
        out = self.conv(unicode(input).split('\n'))
        assert serialize(out) == output

