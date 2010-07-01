"""
MoinMoin - Tests for MoinMoin.converter2.docbook_out

@copyright: 2010 MoinMoin:ValentinJaniaut
@license: GNU GPL, see COPYING for details.
"""

import py.test
import re

try:
    from lxml import etree
except:
    py.test.skip("lxml module required to run test for docbook_out converter.")

from MoinMoin.converter2.docbook_out import *
from emeraldtree.tree import *
from MoinMoin import log
logging = log.getLogger(__name__)
import StringIO

class Base(object):
    input_namespaces = ns_all = 'xmlns="%s" xmlns:page="%s" xmlns:html="%s" xmlns:xlink="%s"' % (
        moin_page.namespace,
        moin_page.namespace,
        html.namespace,
        xlink.namespace)
    output_namespaces = {
        docbook.namespace: '',
        moin_page.namespace: 'page'
    }

    input_re = re.compile(r'^(<[a-z:]+)')
    output_re = re.compile(r'\s+xmlns(:\S+)?="[^"]+"')

    def handle_input(self, input):
        i = self.input_re.sub(r'\1 ' + self.input_namespaces, input)
        return ET.XML(i)

    def handle_output(self, elem, **options):
        from cStringIO import StringIO
        file = StringIO()
        tree = ET.ElementTree(elem)

    def handle_input(self, input):
        i = self.input_re.sub(r'\1 ' + self.input_namespaces, input)
        return ET.XML(i)

    def handle_output(self, elem, **options):
        from cStringIO import StringIO
        file = StringIO()
        tree = ET.ElementTree(elem)
        tree.write(file, namespaces=self.output_namespaces, **options)
        return self.output_re.sub(u'', file.getvalue())

    def do(self, input, xpath, args={}):
        out = self.conv(self.handle_input(input), **args)
        string_to_parse = self.handle_output(out)
        logging.debug("After the docbook_OUT conversion : %s" % string_to_parse)
        tree = etree.parse(StringIO.StringIO(string_to_parse))
        assert (tree.xpath(xpath))

class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter()

    def test_base(self):
        data = [
            ('<page><body><p>Test</p></body></page>',
              '/article[para="Test"]'),
        ]
        for i in data:
            yield (self.do, ) + i

