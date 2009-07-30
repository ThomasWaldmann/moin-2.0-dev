"""
MoinMoin - Tests for MoinMoin.converter2.moinwiki_in

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test
import re

from MoinMoin.converter2.moinwiki_in import *


class TestConverter(object):
    namespaces = {
        moin_page.namespace: '',
        xlink.namespace: 'xlink',
    }

    output_re = re.compile(r'\s+xmlns(:\S+)?="[^"]+"')

    def setup_class(self):
        self.conv = Converter(self.request)

    def test_base(self):
        data = [
            (u'Text',
                '<page><body><p>Text</p></body></page>'),
            (u'Text\nTest',
                '<page><body><p>Text\nTest</p></body></page>'),
            (u'Text\n\nTest',
                '<page><body><p>Text</p><p>Test</p></body></page>'),
            (u'MoinMoin',
                '<page><body><p><a xlink:href="wiki.local:MoinMoin">MoinMoin</a></p></body></page>'),
            (u'!MoinMoin',
                '<page><body><p>MoinMoin</p></body></page>'),
            (u'Self:FrontPage',
                '<page><body><p><a xlink:href="wiki://Self/FrontPage">FrontPage</a></p></body></page>'),
            (u'http://moinmo.in/',
                '<page><body><p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p></body></page>'),
            (u'[[http://moinmo.in/]]',
                '<page><body><p><a xlink:href="http://moinmo.in/">http://moinmo.in/</a></p></body></page>'),
            (u'[[http://moinmo.in/|MoinMoin]]',
                '<page><body><p><a xlink:href="http://moinmo.in/">MoinMoin</a></p></body></page>'),
            (u'[[MoinMoin]]',
                '<page><body><p><a xlink:href="wiki.local:MoinMoin">MoinMoin</a></p></body></page>'),
            (u'{{http://moinmo.in/}}',
                '<page><body><p><object xlink:href="http://moinmo.in/" /></p></body></page>'),
            (u'{{http://moinmo.in/|MoinMoin}}',
                '<page><body><p><object alt="MoinMoin" xlink:href="http://moinmo.in/" /></p></body></page>'),
            (u'----',
                '<page><body><separator /></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_args(self):
        from MoinMoin.converter2._args import Arguments
        from MoinMoin.util.iri import Iri
        data = [
            (u'Text',
                '<page page-href="wiki:/Test"><body><p>Text</p></body></page>',
                {'page_url': Iri(scheme='wiki', path='/Test')}),
            (u'Text',
                '<page><body style="background-color: red"><p>Text</p></body></page>',
                {'arguments': Arguments(keyword={'style': 'background-color: red'})}),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_emphasis(self):
        data = [
            ("''Emphasis''",
                '<page><body><p><emphasis>Emphasis</emphasis></p></body></page>'),
            ("'''Strong'''",
                '<page><body><p><strong>Strong</strong></p></body></page>'),
            ("'''''Both'''''",
                '<page><body><p><strong><emphasis>Both</emphasis></strong></p></body></page>'),
            ("'''''Mixed'''Emphasis''",
                '<page><body><p><emphasis><strong>Mixed</strong>Emphasis</emphasis></p></body></page>'),
            ("'''''Mixed''Strong'''",
                '<page><body><p><strong><emphasis>Mixed</emphasis>Strong</strong></p></body></page>'),
            ("Text ''Emphasis\n''Text",
                '<page><body><p>Text <emphasis>Emphasis\n</emphasis>Text</p></body></page>'),
            ("Text ''Emphasis\n\nText",
                '<page><body><p>Text <emphasis>Emphasis</emphasis></p><p>Text</p></body></page>'),
            ("Text''''''Text''''",
                '<page><body><p>TextText</p></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_heading(self):
        data = [
            (u'= Heading 1 =',
                '<page><body><h outline-level="1">Heading 1</h></body></page>'),
            (u'== Heading 2 ==',
                '<page><body><h outline-level="2">Heading 2</h></body></page>'),
            (u'=== Heading 3 ===',
                '<page><body><h outline-level="3">Heading 3</h></body></page>'),
            (u'==== Heading 4 ====',
                '<page><body><h outline-level="4">Heading 4</h></body></page>'),
            (u'===== Heading 5 =====',
                '<page><body><h outline-level="5">Heading 5</h></body></page>'),
            (u'====== Heading 6 ======',
                '<page><body><h outline-level="6">Heading 6</h></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_inline(self):
        data = [
            ("__underline__",
                '<page><body><p><span text-decoration="underline">underline</span></p></body></page>'),
            (",,sub,,script",
                '<page><body><p><span baseline-shift="sub">sub</span>script</p></body></page>'),
            ("^super^script",
                '<page><body><p><span baseline-shift="super">super</span>script</p></body></page>'),
            ("~-smaller-~",
                '<page><body><p><span font-size="85%">smaller</span></p></body></page>'),
            ("~+larger+~",
                '<page><body><p><span font-size="120%">larger</span></p></body></page>'),
            ("--(strike through)--",
                '<page><body><p><span text-decoration="line-through">strike through</span></p></body></page>'),
            (u'&quot;',
                '<page><body><p>"</p></body></page>'),
            (u'&#34;',
                '<page><body><p>"</p></body></page>'),
            (u'&#x22;',
                '<page><body><p>"</p></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            (u' * Item',
                '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>'),
            (u' * Item\nItem',
                '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item\nItem</list-item-body></list-item></list></body></page>'),
            (u' * Item 1\n *Item 2',
                '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>'),
            (u' * Item 1\n  * Item 1.2\n * Item 2',
                '<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item 1<list item-label-generate="unordered"><list-item><list-item-body>Item 1.2</list-item-body></list-item></list></list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>'),
            (u' * List 1\n\n * List 2',
                '<page><body><list item-label-generate="unordered"><list-item><list-item-body>List 1</list-item-body></list-item></list><list item-label-generate="unordered"><list-item><list-item-body>List 2</list-item-body></list-item></list></body></page>'),
            (u' 1. Item',
                '<page><body><list item-label-generate="ordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>'),
            (u' * List 1\n 1. List 2',
                '<page><body><list item-label-generate="unordered"><list-item><list-item-body>List 1</list-item-body></list-item></list><list item-label-generate="ordered"><list-item><list-item-body>List 2</list-item-body></list-item></list></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_macro(self):
        data = [
            (u'<<BR>>',
                '<page><body /></page>'),
            (u'Text<<BR>>Text',
                '<page><body><p>Text<line-break />Text</p></body></page>'),
            (u'<<Macro>>',
                '<page><body><page alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></body></page>'),
            (u' <<Macro>> ',
                '<page><body><page alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></body></page>'),
            (u'Text <<Macro>>',
                '<page><body><p>Text <inline-part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></p></body></page>'),
            (u'Text\n<<Macro>>',
                '<page><body><p>Text</p><page alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></body></page>'),
            (u'Text\nText <<Macro>>',
                '<page><body><p>Text\nText <inline-part alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></p></body></page>'),
            (u'Text\n\n<<Macro>>',
                '<page><body><p>Text</p><page alt="&lt;&lt;Macro&gt;&gt;" content-type="x-moin/macro;name=Macro" /></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_table(self):
        data = [
            (u'||Cell||',
                '<page><body><table><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>'),
            (u'||Cell 1||Cell 2||',
                '<page><body><table><table-body><table-row><table-cell>Cell 1</table-cell><table-cell>Cell 2</table-cell></table-row></table-body></table></body></page>'),
            (u'||Row 1||\n||Row 2||\n',
                '<page><body><table><table-body><table-row><table-cell>Row 1</table-cell></table-row><table-row><table-cell>Row 2</table-cell></table-row></table-body></table></body></page>'),
            (u'||Cell 1.1||Cell 1.2||\n||Cell 2.1||Cell 2.2||\n',
                '<page><body><table><table-body><table-row><table-cell>Cell 1.1</table-cell><table-cell>Cell 1.2</table-cell></table-row><table-row><table-cell>Cell 2.1</table-cell><table-cell>Cell 2.2</table-cell></table-row></table-body></table></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_nowiki(self):
        data = [
            (u'{{{nowiki}}}',
                '<page><body><p><code>nowiki</code></p></body></page>'),
            (u'`nowiki`',
                '<page><body><p><code>nowiki</code></p></body></page>'),
            (u'{{{{nowiki}}}}',
                '<page><body><p><code>{nowiki}</code></p></body></page>'),
            (u'text: {{{nowiki}}}, text',
                '<page><body><p>text: <code>nowiki</code>, text</p></body></page>'),
            (u'{{{\nnowiki\n}}}',
                '<page><body><blockcode>nowiki</blockcode></body></page>'),
            (u'{{{\nnowiki\nno\nwiki\n}}}',
                '<page><body><blockcode>nowiki\nno\nwiki</blockcode></body></page>'),
            (u'{{{nowiki}}} {{{nowiki}}}',
                '<page><body><p><code>nowiki</code> <code>nowiki</code></p></body></page>'),
            (u'{{{}}}',
                '<page><body><p><code></code></p></body></page>'),
            (u'``',
                '<page><body><p /></body></page>'),
            # XXX: Is <page> correct?
            (u'{{{#!\nwiki\n}}}',
               '<page><body><page><body><p>wiki</p></body></page></body></page>'),
            (u'{{{#!(style="background-color: red")\nwiki\n}}}',
               '<page><body><page><body style="background-color: red"><p>wiki</p></body></page></body></page>'),
            (u'{{{#!wiki\nwiki\n}}}',
               '<page><body><page><body><p>wiki</p></body></page></body></page>'),
            (u'{{{#!wiki(style="background-color: red")\nwiki\n}}}',
               '<page><body><page><body style="background-color: red"><p>wiki</p></body></page></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_composite(self):
        data = [
            (u'Text\n * Item\n\nText',
                '<page><body><p>Text</p><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list><p>Text</p></body></page>'),
            (u'Text\n||Item||\nText',
                '<page><body><p>Text</p><table><table-body><table-row><table-cell>Item</table-cell></table-row></table-body></table><p>Text</p></body></page>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def serialize(self, elem, **options):
        from cStringIO import StringIO
        file = StringIO()
        tree = ET.ElementTree(elem)
        tree.write(file, namespaces=self.namespaces, **options)
        return self.output_re.sub(u'', file.getvalue())

    def do(self, input, output, args={}, skip=None):
        if skip:
            py.test.skip(skip)
        out = self.conv(input.split(u'\n'), **args)
        assert self.serialize(out) == output

