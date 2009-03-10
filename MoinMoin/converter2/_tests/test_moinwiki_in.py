"""
MoinMoin - Tests for MoinMoin.converter2.moinwiki_in

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.converter2.moinwiki_in import *

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
                '<page %s><body><p>Text</p></body></page>' % namespaces_string),
            ('Text\nTest',
                '<page %s><body><p>Text\nTest</p></body></page>' % namespaces_string),
            ('Text\n\nTest',
                '<page %s><body><p>Text</p><p>Test</p></body></page>' % namespaces_string),
            ('MoinMoin',
                '<page %s %s><body><p><a xlink:href="wiki.local:MoinMoin">MoinMoin</a></p></body></page>' % (namespaces_string, namespaces_string_xlink)),
            ('!MoinMoin',
                '<page %s><body><p>MoinMoin</p></body></page>' % namespaces_string),
            ('Self:FrontPage',
                '<page %s %s><body><p><a xlink:href="wiki://Self/FrontPage">FrontPage</a></p></body></page>' % (namespaces_string, namespaces_string_xlink)),
            ('http://moinmo.in/',
                '<page %s %s><body><p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p></body></page>' % (namespaces_string, namespaces_string_xlink)),
            ('[[http://moinmo.in/]]',
                '<page %s %s><body><p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p></body></page>' % (namespaces_string, namespaces_string_xlink)),
            ('[[http://moinmo.in/|MoinMoin]]',
                '<page %s %s><body><p><a xlink:href="http://moinmo.in/">MoinMoin</a></p></body></page>' % (namespaces_string, namespaces_string_xlink)),
            ('[[MoinMoin]]',
                '<page %s %s><body><p><a xlink:href="wiki.local:MoinMoin">MoinMoin</a></p></body></page>' % (namespaces_string, namespaces_string_xlink)),
            ('{{http://moinmo.in/}}',
                '<page %s %s><body><p><object xlink:href="http://moinmo.in/" /></p></body></page>' % (namespaces_string, namespaces_string_xlink)),
            ('{{http://moinmo.in/|MoinMoin}}',
                '<page %s %s><body><p><object alt="MoinMoin" xlink:href="http://moinmo.in/" /></p></body></page>' % (namespaces_string, namespaces_string_xlink)),
            ('----',
                '<page %s><body><separator /></body></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_emphasis(self):
        pairs = [
            ("''Emphasis''",
                '<page %s><body><p><emphasis>Emphasis</emphasis></p></body></page>' % namespaces_string),
            ("'''Strong'''",
                '<page %s><body><p><strong>Strong</strong></p></body></page>' % namespaces_string),
            ("'''''Both'''''",
                '<page %s><body><p><strong><emphasis>Both</emphasis></strong></p></body></page>' % namespaces_string),
            ("'''''Mixed'''Emphasis''",
                '<page %s><body><p><emphasis><strong>Mixed</strong>Emphasis</emphasis></p></body></page>' % namespaces_string),
            ("'''''Mixed''Strong'''",
                '<page %s><body><p><strong><emphasis>Mixed</emphasis>Strong</strong></p></body></page>' % namespaces_string),
            ("Text ''Emphasis\n''Text",
                '<page %s><body><p>Text <emphasis>Emphasis\n</emphasis>Text</p></body></page>' % namespaces_string),
            ("Text ''Emphasis\n\nText",
                '<page %s><body><p>Text <emphasis>Emphasis</emphasis></p><p>Text</p></body></page>' % namespaces_string),
            ("Text''''''Text''''",
                '<page %s><body><p>TextText</p></body></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_heading(self):
        pairs = [
            ('= Heading 1 =',
                '<page %s><body><h outline-level="1">Heading 1</h></body></page>' % namespaces_string),
            ('== Heading 2 ==',
                '<page %s><body><h outline-level="2">Heading 2</h></body></page>' % namespaces_string),
            ('=== Heading 3 ===',
                '<page %s><body><h outline-level="3">Heading 3</h></body></page>' % namespaces_string),
            ('==== Heading 4 ====',
                '<page %s><body><h outline-level="4">Heading 4</h></body></page>' % namespaces_string),
            ('===== Heading 5 =====',
                '<page %s><body><h outline-level="5">Heading 5</h></body></page>' % namespaces_string),
            ('====== Heading 6 ======',
                '<page %s><body><h outline-level="6">Heading 6</h></body></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_inline(self):
        pairs = [
            ("__underline__",
                '<page %s><body><p><span text-decoration="underline">underline</span></p></body></page>' % namespaces_string),
            (",,sub,,script",
                '<page %s><body><p><span baseline-shift="sub">sub</span>script</p></body></page>' % namespaces_string),
            ("^super^script",
                '<page %s><body><p><span baseline-shift="super">super</span>script</p></body></page>' % namespaces_string),
            ("~-smaller-~",
                '<page %s><body><p><span font-size="85%%">smaller</span></p></body></page>' % namespaces_string),
            ("~+larger+~",
                '<page %s><body><p><span font-size="120%%">larger</span></p></body></page>' % namespaces_string),
            ("--(strike through)--",
                '<page %s><body><p><span text-decoration="line-through">strike through</span></p></body></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_list(self):
        pairs = [
            (' * Item',
                '<page %s><body><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>' % namespaces_string),
            (' * Item\nItem',
                '<page %s><body><list item-label-generate="unordered"><list-item><list-item-body>Item\nItem</list-item-body></list-item></list></body></page>' % namespaces_string),
            (' * Item 1\n *Item 2',
                '<page %s><body><list item-label-generate="unordered"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>' % namespaces_string),
            (' * Item 1\n  * Item 1.2\n * Item 2',
                '<page %s><body><list item-label-generate="unordered"><list-item><list-item-body>Item 1<list item-label-generate="unordered"><list-item><list-item-body>Item 1.2</list-item-body></list-item></list></list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>' % namespaces_string),
            (' * List 1\n\n * List 2',
                '<page %s><body><list item-label-generate="unordered"><list-item><list-item-body>List 1</list-item-body></list-item></list><list item-label-generate="unordered"><list-item><list-item-body>List 2</list-item-body></list-item></list></body></page>' % namespaces_string),
            (' 1. Item',
                '<page %s><body><list item-label-generate="ordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>' % namespaces_string),
            (' * List 1\n 1. List 2',
                '<page %s><body><list item-label-generate="unordered"><list-item><list-item-body>List 1</list-item-body></list-item></list><list item-label-generate="ordered"><list-item><list-item-body>List 2</list-item-body></list-item></list></body></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_macro(self):
        pairs = [
            ('<<BR>>',
                '<page %s><body /></page>' % namespaces_string),
            ('Text<<BR>>Text',
                '<page %s><body><p>Text<line-break />Text</p></body></page>' % namespaces_string),
            ('<<Macro>>',
                '<page %s><body><macro alt="&lt;&lt;Macro&gt;&gt;" macro-args="" macro-context="block" macro-name="Macro" /></body></page>' % namespaces_string),
            (' <<Macro>> ',
                '<page %s><body><macro alt="&lt;&lt;Macro&gt;&gt;" macro-args="" macro-context="block" macro-name="Macro" /></body></page>' % namespaces_string),
            ('Text <<Macro>>',
                '<page %s><body><p>Text <macro alt="&lt;&lt;Macro&gt;&gt;" macro-args="" macro-context="inline" macro-name="Macro" /></p></body></page>' % namespaces_string),
            ('Text\n<<Macro>>',
                '<page %s><body><p>Text</p><macro alt="&lt;&lt;Macro&gt;&gt;" macro-args="" macro-context="block" macro-name="Macro" /></body></page>' % namespaces_string),
            ('Text\nText <<Macro>>',
                '<page %s><body><p>Text\nText <macro alt="&lt;&lt;Macro&gt;&gt;" macro-args="" macro-context="inline" macro-name="Macro" /></p></body></page>' % namespaces_string),
            ('Text\n\n<<Macro>>',
                '<page %s><body><p>Text</p><macro alt="&lt;&lt;Macro&gt;&gt;" macro-args="" macro-context="block" macro-name="Macro" /></body></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_table(self):
        pairs = [
            ('||Cell||',
                '<page %s><body><table><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>' % namespaces_string),
            ('||Cell 1||Cell 2||',
                '<page %s><body><table><table-body><table-row><table-cell>Cell 1</table-cell><table-cell>Cell 2</table-cell></table-row></table-body></table></body></page>' % namespaces_string),
            ('||Row 1||\n||Row 2||\n',
                '<page %s><body><table><table-body><table-row><table-cell>Row 1</table-cell></table-row><table-row><table-cell>Row 2</table-cell></table-row></table-body></table></body></page>' % namespaces_string),
            ('||Cell 1.1||Cell 1.2||\n||Cell 2.1||Cell 2.2||\n',
                '<page %s><body><table><table-body><table-row><table-cell>Cell 1.1</table-cell><table-cell>Cell 1.2</table-cell></table-row><table-row><table-cell>Cell 2.1</table-cell><table-cell>Cell 2.2</table-cell></table-row></table-body></table></body></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_nowiki(self):
        pairs = [
            ('{{{nowiki}}}',
                '<page %s><body><p><code>nowiki</code></p></body></page>' % namespaces_string),
            ('`nowiki`',
                '<page %s><body><p><code>nowiki</code></p></body></page>' % namespaces_string),
            ('{{{{nowiki}}}}',
                '<page %s><body><p><code>{nowiki}</code></p></body></page>' % namespaces_string),
            ('text: {{{nowiki}}}, text',
                '<page %s><body><p>text: <code>nowiki</code>, text</p></body></page>' % namespaces_string),
            ('{{{\nnowiki\n}}}',
                '<page %s><body><blockcode>nowiki</blockcode></body></page>' % namespaces_string),
            ('{{{\nnowiki\nno\nwiki\n}}}',
                '<page %s><body><blockcode>nowiki\nno\nwiki</blockcode></body></page>' % namespaces_string),
            ('{{{nowiki}}} {{{nowiki}}}',
                '<page %s><body><p><code>nowiki</code> <code>nowiki</code></p></body></page>' % namespaces_string),
            ('{{{}}}',
                '<page %s><body><p><code></code></p></body></page>' % namespaces_string),
            ('``',
                '<page %s><body><p /></body></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_composite(self):
        pairs = [
            ('Text\n * Item\n\nText',
                '<page %s><body><p>Text</p><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list><p>Text</p></body></page>' % namespaces_string),
            ('Text\n||Item||\nText',
                '<page %s><body><p>Text</p><table><table-body><table-row><table-cell>Item</table-cell></table-row></table-body></table><p>Text</p></body></page>' % namespaces_string),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def _do(self, input, output, skip=None):
        if skip:
            py.test.skip(skip)
        out = self.conv(input.split('\n'))
        assert serialize(out) == output

