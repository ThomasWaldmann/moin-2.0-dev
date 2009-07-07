"""
MoinMoin - Tests for MoinMoin.converter2.html_out

@copyright: 2007 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.converter2.html_out import *

ns_all = 'xmlns="%s" xmlns:page="%s" xmlns:html="%s" xmlns:xlink="%s"' % (
        moin_page.namespace,
        moin_page.namespace,
        html.namespace,
        xlink.namespace)
ns_html = 'xmlns="%s"' % html.namespace
ns_html_real = 'xmlns:html="%s"' % html.namespace
ns_page = 'xmlns:page="%s"' % moin_page.namespace

def serialize(elem, **options):
    from cStringIO import StringIO
    file = StringIO()
    tree = ET.ElementTree(elem)
    n = {html.namespace: '', moin_page.namespace: 'page'}
    tree.write(file, namespaces=n, **options)
    return file.getvalue()

class TestConverter(object):
    def setup_class(self):
        self.conv = Converter(self.request)

    def test_base(self):
        pairs = [
            ('<page:page %s><page:body><page:p>Test</page:p></page:body></page:page>' % ns_all,
                '<div %s><p>Test</p></div>' % ns_html),
            ('<page:page %s><page:body><page:h>Test</page:h></page:body></page:page>' % ns_all,
                '<div %s><h1>Test</h1></div>' % ns_html),
            ('<page:page %s><page:body><page:h page:outline-level="2">Test</page:h></page:body></page:page>' % ns_all,
                '<div %s><h2>Test</h2></div>' % ns_html),
            ('<page:page %s><page:body><page:h page:outline-level="6">Test</page:h></page:body></page:page>' % ns_all,
                '<div %s><h6>Test</h6></div>' % ns_html),
            ('<page:page %s><page:body><page:h page:outline-level="7">Test</page:h></page:body></page:page>' % ns_all,
                '<div %s><h6>Test</h6></div>' % ns_html),
            ('<page:page %s><page:body><page:a xlink:href="uri:test">Test</page:a></page:body></page:page>' % ns_all,
                '<div %s><a href="uri:test">Test</a></div>' % ns_html),
            ('<page:page %s><page:body><page:p>Test<page:line-break/>Test</page:p></page:body></page:page>' % ns_all,
                '<div %s><p>Test<br />Test</p></div>' % ns_html),
            ('<page:page %s><page:body><page:p>Test<page:span>Test</page:span></page:p></page:body></page:page>' % ns_all,
                '<div %s><p>Test<span>Test</span></p></div>' % ns_html),
            ('<page:page %s><page:body><page:p><page:emphasis>Test</page:emphasis></page:p></page:body></page:page>' % ns_all,
                '<div %s><p><em>Test</em></p></div>' % ns_html),
            ('<page:page %s><page:body><page:p><page:strong>Test</page:strong></page:p></page:body></page:page>' % ns_all,
                '<div %s><p><strong>Test</strong></p></div>' % ns_html),
            ('<page:page %s><page:body><page:blockcode>Code</page:blockcode></page:body></page:page>' % ns_all,
                '<div %s><pre>Code</pre></div>' % ns_html),
            ('<page:page %s><page:body><page:p><page:code>Code</page:code></page:p></page:body></page:page>' % ns_all,
                '<div %s><p><tt>Code</tt></p></div>' % ns_html),
            ('<page:page %s><page:body><page:separator/></page:body></page:page>' % ns_all,
                '<div %s><hr /></div>' % ns_html),
            ('<page:page %s><page:body><page:div><page:p>Text</page:p></page:div></page:body></page:page>' % ns_all,
                '<div %s><div><p>Text</p></div></div>' % ns_html),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_html(self):
        pairs = [
            ('<html:div html:id="a" id="b" %s><html:p id="c">Test</html:p></html:div>' % ns_all,
                '<div id="a" %s><p id="c">Test</p></div>' % ns_html),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_list(self):
        pairs = [
            ('<page %s><body><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>' % ns_all,
                '<div %s><ul><li>Item</li></ul></div>' % ns_html),
            ('<page %s><body><list item-label-generate="ordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>' % ns_all,
                '<div %s><ol><li>Item</li></ol></div>' % ns_html),
            ('<page %s><body><list><list-item><list-item-label>Label</list-item-label><list-item-body>Item</list-item-body></list-item></list></body></page>' % ns_all,
                '<div %s><dl><dt>Label</dt><dd>Item</dd></dl></div>' % ns_html),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_object(self):
        pairs = [
            ('<page %s><body><object xlink:href="href"/></body></page>' % ns_all,
                '<div %s><object data="href" /></div>' % ns_html),
            ('<page %s><body><object xlink:href="href.png"/></body></page>' % ns_all,
                '<div %s><img src="href.png" /></div>' % ns_html),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_style(self):
        pairs = [
            ('<page %s><body><p font-size="1em">Text</p></body></page>' % ns_all,
                '<div %s><p style="font-size: 1em">Text</p></div>' % ns_html),
            ('<page %s><body><p html:style="color: black" font-size="1em">Text</p></body></page>' % ns_all,
                '<div %s><p style="font-size: 1em; color: black">Text</p></div>' % ns_html),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_table(self):
        pairs = [
            ('<page %s><body><table><table-header><table-row><table-cell>Header</table-cell></table-row></table-header><table-footer><table-row><table-cell>Footer</table-cell></table-row></table-footer><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>' % ns_all,
                '<div %s><table><thead><tr><td>Header</td></tr></thead><tfoot><tr><td>Footer</td></tr></tfoot><tbody><tr><td>Cell</td></tr></tbody></table></div>' % ns_html),
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
            ('<page:page %s><page:body><page:macro><page:macro-body><page:p>Test</page:p></page:macro-body></page:macro></page:body></page:page>' % ns_all,
                '<div %s %s><page:macro><page:macro-body><p>Test</p></page:macro-body></page:macro></div>' % (ns_html, ns_page)),
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
            ('<page:page %s><page:body><page:macro><page:macro-body><page:p>Test</page:p></page:macro-body></page:macro></page:body></page:page>' % ns_all,
                '<div %s><p>Test</p></div>' % ns_html),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_note(self):
        pairs = [
            ('<page %s><body><p>Text<note note-class="footnote"><note-body>Note</note-body></note></p></body></page>' % ns_all,
                '<div %s><p>Text<sup id="note-1-ref"><a href="#note-1">1</a></sup></p><p id="note-1"><sup><a href="#note-1-ref">1</a></sup>Note</p></div>' % ns_html),
        ]
        for i in pairs:
            yield (self._do, ) + i

    def test_unknown(self):
        page = ET.XML("<page:unknown %s/>" % ns_all)
        py.test.raises(ElementException, self.conv.__call__, page)

    def _do(self, input, output):
        page = ET.XML(input)
        out = self.conv(page)
        assert serialize(out) == output


