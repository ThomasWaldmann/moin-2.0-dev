"""
MoinMoin - Tests for MoinMoin.converter2.moinwiki_out

@copyright: 2010 MoinMoin:DmitryAndreev
@license: GNU GPL, see COPYING for details.
"""

import py.test
import re

from MoinMoin.converter2.moinwiki_out import *


class Base(object):
    input_namespaces = ns_all = 'xmlns="%s" xmlns:page="%s" xmlns:xlink="%s"' % (
        moin_page.namespace,
        moin_page.namespace,
        xlink.namespace)
    output_namespaces = {
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
        file.write(elem)
        return elem 

    def do(self, input, output, args={}):
        out = self.conv(self.handle_input(input), **args)
        assert self.handle_output(out) == output


class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter(self.request)

    def test_base(self):
        data = [
            ('<page:page><page:body><page:h page:outline-level="2">Test:</page:h>\n<page:strong>strong</page:strong>\n<page:emphasis>emphasis</page:emphasis>\n<page:blockcode>blockcode</page:blockcode>\n<page:code>monospace</page:code></page:body></page:page>',
                "== Test: ==\n'''strong'''\n''emphasis''\n{{{blockcode}}}\n`monospace`"),
        ]
        for i in data:
            yield (self.do, ) + i

