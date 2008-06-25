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
    tree = ElementTree.ElementTree(elem)
    tree.write(file, default_namespace = namespaces.html, **options)
    return file.getvalue()

class TestConverterBase(object):
    def setup_class(self):
        self.conv = ConverterBase()

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
        ]
        for i in pairs:
            yield (self._do,) + i

    def test_html(self):
        pairs = [
            ('<html:div html:id="a" id="b" %s><html:p id="c">Test</html:p></html:div>' % namespaces_string_html,
                '<div id="a" %s><p id="c">Test</p></div>' % namespaces_string_html_default),
        ]
        for i in pairs:
            yield (self._do,) + i

    def test_list(self):
        pairs = [
            ('<page %s><list><list-item><list-item-body>Item</list-item-body></list-item></list></page>' % namespaces_string_page_default,
                '<div %s><ul><li>Item</li></ul></div>' % namespaces_string_html_default),
        ]
        for i in pairs:
            yield (self._do,) + i

    def _do(self, input, output):
        page = ElementTree.XML(input)
        out = self.conv(page)
        assert serialize(out) == output

    def test_unknown(self):
        page = ElementTree.XML("<page:unknown %s/>" % namespaces_string_page)
        py.test.raises(ElementException, self.conv.__call__, page)

