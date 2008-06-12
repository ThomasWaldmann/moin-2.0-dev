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

    def _do(self, input, output):
        page = ElementTree.XML(input)
        out = self.conv(page)
        assert serialize(out) == output

    def test_unknown(self):
        page = ElementTree.XML("<page:unknown %s/>" % namespaces_string_page)
        py.test.raises(ElementException, self.conv.__call__, page)

