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

    def handle_input(self, input, args={}):
        out = self.conv(input, **args)
        f = StringIO.StringIO()
        out.write(f.write, namespaces=self.namespaces, )
        return self.output_re.sub(u'', f.getvalue())


    def do(self, input, path, text, args={}):
        string_to_parse = self.handle_input(input)
        tree = etree.parse(StringIO.StringIO(string_to_parse))
        r = tree.xpath(path)

        assert len(r) == 1
        assert r[0].text == text

    def do_with_attr(self, input, path, attr, attr_value, text, args={}):
        string_to_parse = self.handle_input(input)
        print string_to_parse
        tree = etree.parse(StringIO.StringIO(string_to_parse))
        r = tree.xpath(path)
        assert len(r) == 1
        assert r[0].get(attr) == attr_value
        assert r[0].text == text

class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter(self.request)

    def test_base(self):
        data = [
            ('<div><p>Test</p></div>',
             '/page/body/div/p',
             'Test'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_title(self):
        data = [
            ('<div><h2>Test</h2></div>',
              '/page/body/div/h',
              'outline-level',
              '2',
              'Test'),
            ('<div><h6>Test</h6></div>',
              '/page/body/div/h',
              'outline-level',
              '6',
              'Test'),
        ]
        for i in data:
            yield (self.do_with_attr, ) + i

    def test_basic_style(self):
        data = [
            ('<div><p><em>Test</em></p></div>',
              '/page/body/div/p/emphasis',
              'Test'),
            ('<div><p><strong>Test</strong></p></div>',
              '/page/body/div/p/strong',
              'Test'),
            ('<div><pre>Code</pre></div>',
              '/page/body/div/blockcode',
              'Code'),
            ('<div><p><tt>Code</tt></p></div>',
              '/page/body/div/p/code',
              'Code'),
        ]
        for i in data:
            yield (self.do, ) + i
