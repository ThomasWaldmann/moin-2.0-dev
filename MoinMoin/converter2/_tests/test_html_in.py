"""
MoinMoin - Tests for MoinMoin.converter2.html_in

@copyright: 2010 MoinMoin:ValentinJaniaut
@license: GNU GPL, see COPYING for details.
"""

import py.test
import re

try:
    from lxml import etree
except:
    py.test.skip("lxml module required to run test for html_in converter.")

from MoinMoin.converter2.html_in import *
from emeraldtree.tree import *
import StringIO

class Base(object):
    namespaces = {
        moin_page.namespace: '',
        xlink.namespace: 'xlink',
    }

    namespaces_xpath = {'xlink': xlink.namespace}

    output_re = re.compile(r'\s+xmlns="[^"]+"')

    def handle_input(self, input, args={}):
        out = self.conv(input, **args)
        f = StringIO.StringIO()
        out.write(f.write, namespaces=self.namespaces, )
        return self.output_re.sub(u'', f.getvalue())


    def do(self, input, path, args={}):
        string_to_parse = self.handle_input(input)
        tree = etree.parse(StringIO.StringIO(string_to_parse))
        assert (tree.xpath(path, namespaces=self.namespaces_xpath))

        #assert len(r) == 1
        #assert r[0].text == text

class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter()

    def test_base(self):
        data = [
            ('<html><div><p>Test</p></div></html>',
             '/page/body/div[p="Test"]'),
            ('<html><div><p>First paragraph</p><h1>Title</h1><p><em>Paragraph</em></p></div></html>',
             '/page/body/div/p[2][emphasis="Paragraph"]'),
            ('<html><div><p>First Line<br />Second Line</p></div></html>',
             '/page/body/div/p[1]/line-break')
        ]
        for i in data:
            yield (self.do, ) + i

    def test_title(self):
        data = [
            ('<html><h2>Test</h2></html>',
              '/page/body/h[@outline-level=2] | /page/body[h="Test"]'),
            ('<html><h6>Test</h6></html>',
              '/page/body/h[@outline-level=6] | /page/body[h="Test"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_basic_style(self):
        data = [
            ('<html><p><em>Test</em></p></html>',
              '/page/body/p[emphasis="Test"]'),
            ('<html><p><i>Test</i></p></html>',
              '/page/body/p[emphasis="Test"]'),
            ('<html><p><strong>Test</strong></p></html>',
              '/page/body/p[strong="Test"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_span(self):
        data = [
            ('<html><p><sub>sub</sub>script</p></html>',
             '/page/body/p/span[@base-line-shift="sub"] | /page/body/p[span="sub"]'),
            ('<html><p><sup>super</sup>script</p></html>',
             '/page/body/p/span[@base-line-shift="super"] | /page/body/p[span="super"]'),
            ('<html><p><u>underline</u></html>',
             '/page/body/p/span[@text-decoration="underline"] | /page/body/p[span="underline"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_link(self):
        data = [
            ('<html><p><a href="uri:test">Test</a></p></html>',
              '/page/body/p/a[@xlink:href="uri:test"] | /page/body/p[a="Test"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_code(self):
        data = [
            ('<html><div><code>Code</code></div></html>',
             '/page/body/div[code="Code"]'),
            ('<html><div><samp>Code</samp></div></html>',
             '/page/body/div[code="Code"]'),
            ('<html><pre>Code</pre></html>',
              '/page/body[blockcode="Code"]'),
            ('<html><p><tt>Code</tt></p></html>',
              '/page/body/p[code="Code"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            ('<html><div><ul><li>Item</li></ul></div></html>',
              '/page/body/div/list[@item-label-generate="unordered"]/list-item[list-item-body="Item"]'),
            ('<html><div><ol><li>Item</li></ol></div></html>',
              '/page/body/div/list[@item-label-generate="ordered"]/list-item[list-item-body="Item"]'),
            ('<html><div><ol type="A"><li>Item</li></ol></div></html>',
              '/page/body/div/list[@item-label-generate="ordered" and @list-style-type="upper-alpha"]/list-item[list-item-body="Item"]'),
            ('<html><div><ol type="I"><li>Item</li></ol></div></html>',
              '/page/body/div/list[@item-label-generate="ordered" and @list-style-type="upper-roman"]/list-item[list-item-body="Item"]'),
            ('<html><div><dl><dt>Label</dt><dd>Item</dd></dl></div></html>',
             '/page/body/div/list/list-item[list-item-label="Label"] | /page/body/div/list/list-item[list-item-body="Item"]'),
        ]
        for i in data:
            yield (self.do, ) + i
