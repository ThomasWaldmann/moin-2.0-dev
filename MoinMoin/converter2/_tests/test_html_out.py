"""
MoinMoin - Tests for MoinMoin.converter2.html_out

@copyright: 2007 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.converter2.html_out import *

namespaces_string_html = 'xmlns:html="%s"' % namespaces.html
namespaces_string_html_default = 'xmlns="%s"' % namespaces.html
namespaces_string_page = 'xmlns:page="%s"' % namespaces.moin_page
namespaces_string_page_default = 'xmlns="%s"' % namespaces.moin_page
namespaces_string_xlink = 'xmlns:xlink="%s"' % namespaces.xlink

def serialize(elem, **options):
    from cStringIO import StringIO
    file = StringIO()
    tree = ET.ElementTree(elem)
    n = {namespaces.html: '', namespaces.moin_page: 'page'}
    tree.write(file, namespaces=n, **options)
    return file.getvalue()

class TestConverterBase(object):
    def setup_class(self):
        self.conv = ConverterBase(self.request)

    def test_base(self):
        pairs = [
            ('<page:page %s><page:p>Test</page:p></page:page>' % namespaces_string_page,
                '<div %s><p>Test</p></div>' % namespaces_string_html_default),
            ('<page:page %s><page:h>Test</page:h></page:page>' % namespaces_string_page,
                '<div %s><h1>Test</h1></div>' % namespaces_string_html_default),
            ('<page:page %s><page:h page:outline-level="2">Test</page:h></page:page>' % namespaces_string_page,
                '<div %s><h2>Test</h2></div>' % namespaces_string_html_default),
            ('<page:page %s><page:h page:outline-level="6">Test</page:h></page:page>' % namespaces_string_page,
                '<div %s><h6>Test</h6></div>' % namespaces_string_html_default),
            ('<page:page %s><page:h page:outline-level="7">Test</page:h></page:page>' % namespaces_string_page,
                '<div %s><h6>Test</h6></div>' % namespaces_string_html_default),
            ('<page:page %s><page:a xlink:href="uri:test">Test</page:a></page:page>' %
                ' '.join([namespaces_string_page, namespaces_string_xlink]),
                '<div %s><a href="uri:test">Test</a></div>' % namespaces_string_html_default),
            ('<page:page %s><page:p>Test<page:line-break/>Test</page:p></page:page>' % namespaces_string_page,
                '<div %s><p>Test<br />Test</p></div>' % namespaces_string_html_default),
            ('<page:page %s><page:p>Test<page:span>Test</page:span></page:p></page:page>' % namespaces_string_page,
                '<div %s><p>Test<span>Test</span></p></div>' % namespaces_string_html_default),
            ('<page:page %s><page:p><page:emphasis>Test</page:emphasis></page:p></page:page>' % namespaces_string_page,
                '<div %s><p><em>Test</em></p></div>' % namespaces_string_html_default),
            ('<page:page %s><page:p><page:strong>Test</page:strong></page:p></page:page>' % namespaces_string_page,
                '<div %s><p><strong>Test</strong></p></div>' % namespaces_string_html_default),
            ('<page:page %s><page:blockcode>Code</page:blockcode></page:page>' % namespaces_string_page,
                '<div %s><pre>Code</pre></div>' % namespaces_string_html_default),
            ('<page:page %s><page:p><page:code>Code</page:code></page:p></page:page>' % namespaces_string_page,
                '<div %s><p><tt>Code</tt></p></div>' % namespaces_string_html_default),
            ('<page:page %s><page:separator/></page:page>' % namespaces_string_page,
                '<div %s><hr /></div>' % namespaces_string_html_default),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_html(self):
        pairs = [
            ('<html:div html:id="a" id="b" %s><html:p id="c">Test</html:p></html:div>' % namespaces_string_html,
                '<div id="a" %s><p id="c">Test</p></div>' % namespaces_string_html_default),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_list(self):
        pairs = [
            ('<page %s><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></page>' % namespaces_string_page_default,
                '<div %s><ul><li>Item</li></ul></div>' % namespaces_string_html_default),
            ('<page %s><list item-label-generate="ordered"><list-item><list-item-body>Item</list-item-body></list-item></list></page>' % namespaces_string_page_default,
                '<div %s><ol><li>Item</li></ol></div>' % namespaces_string_html_default),
            ('<page %s><list><list-item><list-item-label>Label</list-item-label><list-item-body>Item</list-item-body></list-item></list></page>' % namespaces_string_page_default,
                '<div %s><dl><dt>Label</dt><dd>Item</dd></dl></div>' % namespaces_string_html_default),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_style(self):
        pairs = [
            ('<page %s><p font-size="1em">Text</p></page>' % namespaces_string_page_default,
                '<div %s><p style="font-size: 1em">Text</p></div>' % namespaces_string_html_default),
            ('<page %s %s><p html:style="color: black" font-size="1em">Text</p></page>' % (namespaces_string_page_default, namespaces_string_html),
                '<div %s><p style="font-size: 1em; color: black">Text</p></div>' % namespaces_string_html_default),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_table(self):
        pairs = [
            ('<page %s><table><table-header><table-row><table-cell>Header</table-cell></table-row></table-header><table-footer><table-row><table-cell>Footer</table-cell></table-row></table-footer><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></page>' % namespaces_string_page_default,
                '<div %s><table><thead><tr><td>Header</td></tr></thead><tfoot><tr><td>Footer</td></tr></tfoot><tbody><tr><td>Cell</td></tr></tbody></table></div>' % namespaces_string_html_default),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def _do(self, input, output):
        page = ET.XML(input)
        out = self.conv(page)
        assert serialize(out) == output

class TestConverter(object):
    def setup_class(self):
        self.conv = Converter(self.request)

    def test_macro(self):
        pairs = [
            ('<page:page %s><page:macro><page:macro-body><page:p>Test</page:p></page:macro-body></page:macro></page:page>' % namespaces_string_page,
                '<div %s %s><page:macro><page:macro-body><p>Test</p></page:macro-body></page:macro></div>' % (namespaces_string_html_default, namespaces_string_page)),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def _do(self, input, output):
        page = ET.XML(input)
        out = self.conv(page)
        assert serialize(out) == output

class TestConverterPage(object):
    def setup_class(self):
        self.conv = ConverterPage(self.request)

    def test_macro(self):
        pairs = [
            ('<page:page %s><page:macro><page:macro-body><page:p>Test</page:p></page:macro-body></page:macro></page:page>' % namespaces_string_page,
                '<div %s><p>Test</p></div>' % namespaces_string_html_default),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_note(self):
        pairs = [
            ('<page %s><p>Text<note note-class="footnote"><note-body>Note</note-body></note></p></page>' % namespaces_string_page_default,
                '<div %s><p>Text<sup id="note-1-ref"><a href="#note-1">1</a></sup></p><p id="note-1"><sup><a href="#note-1-ref">1</a></sup>Note</p></div>' % namespaces_string_html_default),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_unknown(self):
        page = ET.XML("<page:unknown %s/>" % namespaces_string_page)
        py.test.raises(ElementException, self.conv.__call__, page)

    def _do(self, input, output):
        page = ET.XML(input)
        out = self.conv(page)
        assert serialize(out) == output


