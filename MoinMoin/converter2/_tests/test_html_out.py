"""
MoinMoin - Tests for MoinMoin.converter2.html_out

@copyright: 2007 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.converter2.html_out import *

namespaces_string = 'xmlns:page="%s" xmlns:html="%s"' % (namespaces.moin_page, namespaces.html)

def serialize(elem, **options):
    from cStringIO import StringIO
    file = StringIO()
    tree = ElementTree.ElementTree(elem)
    tree.write(file, **options)
    return file.getvalue()

class TestConverterBase(object):
    def setup_class(self):
        self.conv = ConverterBase()

    def test_base(self):
        pairs = [
            ('<page:page %s><page:p>Test</page:p></page:page>',
                '<html:div xmlns:html="http://www.w3.org/1999/xhtml"><html:p>Test</html:p></html:div>'),
            ('<page:page %s><page:h>Test</page:h></page:page>',
                '<html:div xmlns:html="http://www.w3.org/1999/xhtml"><html:h1>Test</html:h1></html:div>'),
            ('<page:page %s><page:h page:outline-level="2">Test</page:h></page:page>',
                '<html:div xmlns:html="http://www.w3.org/1999/xhtml"><html:h2>Test</html:h2></html:div>'),
        ]
        for i in pairs:
            yield (self._do_base,) + i

    def _do_base(self, input, output):
        page = ElementTree.XML(input % namespaces_string)
        out = self.conv(page)
        assert serialize(out) == output

    def test_unknown(self):
        page = ElementTree.XML("<page:unknown %s/>" % namespaces_string)
        py.test.raises(ElementException, self.conv.__call__, page)

