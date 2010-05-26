"""
MoinMoin - Tests for MoinMoin.converter2.html_in

@copyright: 2010 MoinMoin:ValentinJaniaut
@license: GNU GPL, see COPYING for details.
"""

import py.test
import re

from MoinMoin.converter2.html_in import *
from emeraldtree.tree import *
from lxml import etree
import StringIO

class Base(object):
    namespaces = {
        moin_page.namespace: '',
        xlink.namespace: 'xlink',
    }

    output_re = re.compile(r'\s+xmlns(:\S+)?="[^"]+"')

    def do(self, input, path, string_test, args={}):
        out = self.conv(input, **args)
        f = StringIO.StringIO()
        out.write(f.write, namespaces=self.namespaces,)

        str_input = self.output_re.sub(u'',f.getvalue())
        tree = etree.parse(StringIO.StringIO(str_input))
        
        r = tree.xpath(path)

        assert len(r) == 1
        assert tree.xpath(path) == string_test

class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter(self.request)

    def test_base(self):
        data = [
            ('<div><p>Test</p></div>',
             'body/p',
             'Test'),
        ]
        for i in data:
            yield (self.do, ) + i
