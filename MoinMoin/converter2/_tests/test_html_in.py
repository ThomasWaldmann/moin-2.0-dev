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
from MoinMoin import log
logging = log.getLogger(__name__)
import StringIO

class Base(object):
    namespaces = {
        moin_page.namespace: '',
        xlink.namespace: 'xlink',
    }

    namespaces_xpath = {'xlink': xlink.namespace}

    output_re = re.compile(r'\s+xmlns="[^"]+"')

    def handle_input(self, input, args):
        out = self.conv(input, **args)
        f = StringIO.StringIO()
        out.write(f.write, namespaces=self.namespaces, )
        return self.output_re.sub(u'', f.getvalue())


    def do(self, input, path):
        string_to_parse = self.handle_input(input, args={})
        logging.debug("After the HTML_IN conversion : %s" % string_to_parse)
        tree = etree.parse(StringIO.StringIO(string_to_parse))
        assert (tree.xpath(path, namespaces=self.namespaces_xpath))

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
             '/page/body/div/p[1]/line-break'),
            ('<html><div><p>First Paragraph</p><hr /><p>Second Paragraph</p></div></html>',
             '/page/body/div/separator'),
            ('<div><p>Test</p></div>',
             '/page/body[p="Test"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_title(self):
        data = [
            ('<html><h2>Test</h2></html>',
              '/page/body/h[text()="Test"][@outline-level=2]'),
            ('<html><h6>Test</h6></html>',
              '/page/body/h[text()="Test"][@outline-level=6]'),
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
            ('<html><p><b>Test</b></p></html>',
              '/page/body/p[strong="Test"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_span(self):
        data = [
            ('<html><p><sub>sub</sub>script</p></html>',
             '/page/body/p/span[text()="sub"][@baseline-shift="sub"]'),
            ('<html><p><sup>super</sup>script</p></html>',
             '/page/body/p/span[text()="super"][@baseline-shift="super"]'),
            ('<html><p><u>underline</u></p></html>',
             '/page/body/p/span[text()="underline"][@text-decoration="underline"]'),
            ('<html><p><big>Test</big></p></html>',
              '/page/body/p/span[text()="Test"][@font-size="120%"]'),
            ('<html><p><small>Test</small></p></html>',
              '/page/body/p/span[text()="Test"][@font-size="85%"]'),
            ('<html><p><ins>underline</ins></p></html>',
             '/page/body/p/span[text()="underline"][@text-decoration="underline"]'),
            ('<html><p><del>Test</del></p></html>',
             '/page/body/p/span[text()="Test"][@text-decoration="line-through"]'),
            ('<html><p><s>Test</s></p></html>',
             '/page/body/p/span[text()="Test"][@text-decoration="line-through"]'),
            ('<html><p><strike>Test</strike></p></html>',
             '/page/body/p/span[text()="Test"][@text-decoration="line-through"]'),

        ]
        for i in data:
            yield (self.do, ) + i

    def test_span_html_element(self):
        data = [
            ('<html><p><abbr>Text</abbr></p></html>',
             '/page/body/p/span[text()="Text"][@html-element="abbr"]'),
            ('<html><p><acronym>Text</acronym></p></html>',
             '/page/body/p/span[text()="Text"][@html-element="acronym"]'),
            ('<html><p><address>Text</address></p></html>',
             '/page/body/p/span[text()="Text"][@html-element="address"]'),
            ('<html><p><dfn>Text</dfn></p></html>',
             '/page/body/p/span[text()="Text"][@html-element="dfn"]'),
            ('<html><p><kbd>Text</kbd></p></html>',
             '/page/body/p/span[text()="Text"][@html-element="kbd"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_link(self):
        data = [
            ('<html><p><a href="uri:test">Test</a></p></html>',
              '/page/body/p/a[text()="Test"][@xlink:href="uri:test"]'),
            ('<html><base href="http://www.base-url.com/" /><body><div><p><a href="myPage.html">Test</a></p></div></body></html>',
              '/page/body/div/p/a[@xlink:href="http://www.base-url.com/myPage.html"]'),
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
            ('<html><div><ol type="a"><li>Item</li></ol></div></html>',
              '/page/body/div/list[@item-label-generate="ordered" and @list-style-type="lower-alpha"]/list-item[list-item-body="Item"]'),
            ('<html><div><ol type="i"><li>Item</li></ol></div></html>',
              '/page/body/div/list[@item-label-generate="ordered" and @list-style-type="lower-roman"]/list-item[list-item-body="Item"]'),
            ('<html><div><dl><dt>Label</dt><dd>Item</dd></dl></div></html>',
             '/page/body/div/list/list-item[list-item-label="Label"][list-item-body="Item"]'),
            ('<html><div><dir><li>Item</li></dir></div></html>',
              '/page/body/div/list[@item-label-generate="unordered"]/list-item[list-item-body="Item"]'),
            ('<div><ul><li>Item 1</li><li>Item 2</li><li>Item 3</li></ul></div>',
             '/page/body/list[@item-label-generate="unordered"][list-item[1]/list-item-body[text()="Item 1"]][list-item[2]/list-item-body[text()="Item 2"]][list-item[3]/list-item-body[text()="Item 3"]]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_object(self):
        data = [
            ('<html><div><img src="uri:test" /></div></html>',
              '/page/body/div/object/@xlink:href="uri:test"'),
            ('<html><div><object data="href"></object></div></html>',
              '/page/body/div/object/@xlink:href="href"'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_table(self):
        data = [
            ('<html><div><table><thead><tr><td>Header</td></tr></thead><tfoot><tr><td>Footer</td></tr></tfoot><tbody><tr><td>Cell</td></tr></tbody></table></div></html>',
             '/page/body/div/table[./table-header/table-row[table-cell="Header"]][./table-footer/table-row[table-cell="Footer"]][./table-body/table-row[table-cell="Cell"]]'),
            ('<html><div><table><tbody><tr><td colspan="2">Cell</td></tr></tbody></table></div></html>',
             '/page/body/div/table/table-body/table-row/table-cell[text()="Cell"][@number-columns-spanned="2"]'),
            ('<html><div><table><tbody><tr><td rowspan="2">Cell</td></tr></tbody></table></div></html>',
             '/page/body/div/table/table-body/table-row/table-cell[text()="Cell"][@number-rows-spanned="2"]'),
        ]
        for i in data:
            yield (self.do, ) + i
