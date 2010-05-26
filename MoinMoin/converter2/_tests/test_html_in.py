"""
MoinMoin - Tests for MoinMoin.converter2.html_in

@copyright: 2010 MoinMoin:ValentinJaniaut
@license: GNU GPL, see COPYING for details.
"""

import py.test
import re

from MoinMoin.converter2.html_in import *
from emeraldtree.tree import *
import StringIO

class Base(object):
    output_namespaces = ns_all = 'xmlns="%s" xmlns:page="%s" xmlns:html="%s" xmlns:xlink="%s"' % (
        moin_page.namespace,
        moin_page.namespace,
        html.namespace,
        xlink.namespace)
    input_namespaces = {
        html.namespace: '',
        moin_page.namespace: 'page'
    }
        
    def do(self, input, path, string_test, args={}):
        out = self.conv(input, **args)
        tree = ET.ElementTree(out)
        dump(tree)
        assert tree.findtext(path) == string_test

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
