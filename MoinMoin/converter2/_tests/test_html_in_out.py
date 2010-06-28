"""
MoinMoin - Tests for MoinMoin.converter2.html_in and
           MoinMoin.converter2.html_out.

           It will check that roundtrip conversion is working well.

@copyright: 2010 MoinMoin:ValentinJaniaut
@license: GNU GPL, see COPYING for details
"""

import py.test
import re

try:
    from lxml import etree
except:
    py.test.py.test.skip("lxml module required to run test for html_in_out converter.")

from MoinMoin.converter2.html_in import Converter as HTML_IN
from MoinMoin.converter2.html_out import Converter as HTML_OUT
from MoinMoin.util.tree import html, moin_page, xlink
from MoinMoin import log
logging = log.getLogger(__name__)
import StringIO

class Base(object):

    namespaces = {
        html.namespace: '',
        moin_page.namespace:'',
        xlink.namespace: 'xlink',
    }

    output_re = re.compile(r'\s+xmlns="[^"]+"')

    def handle_input(self, input, args):
        f = StringIO.StringIO()
        out = self.conv_html_dom(input, **args)
        out.write(f.write, namespaces=self.namespaces, )
        logging.debug("After the HTML_IN conversion : %s" %
                      self.output_re.sub(u'', f.getvalue()))
        out = self.conv_dom_html(out, **args)
        f = StringIO.StringIO()
        out.write(f.write, namespaces=self.namespaces, )
        return self.output_re.sub(u'', f.getvalue())

    def do(self, input, path):
        string_to_parse = self.handle_input(input, args={})
        logging.debug("After the roundtrip : %s" % string_to_parse)
        tree = etree.parse(StringIO.StringIO(string_to_parse))
        assert (tree.xpath(path))

class TestConverter(Base):
    def setup_class(self):
        self.conv_html_dom = HTML_IN()
        self.conv_dom_html = HTML_OUT(self.request)

    def test_base(self):
        data = [
            ('<html><div><p>Test</p></div></html>',
             '/div/div[p="Test"]'),
            ('<html><div><p>First paragraph</p><h1>Title</h1><p><em>Paragraph</em></p></div></html>',
             '/div/div/p[2][em="Paragraph"]'),
            ('<html><div><p>First Line<br />Second line</p></div></html>',
             '/div/div/p[1]/br'),
            ('<div><p>Test</p></div>',
             '/div[p="Test"]'),
        ]
        for i in data:
            yield(self.do, ) + i

    def test_title(self):
        data = [
            ('<html><h2>Test</h2></html>',
             '/div[h2="Test"]'),
            ('<html><h6>Test</h6></html>',
             '/div[h6="Test"]'),
        ]
        for i in data:
          yield (self.do, ) + i

    def test_basic_style(self):
        data = [
            ('<html><p><em>Test</em></p></html>',
              '/div/p[em="Test"]'),
            ('<html><p><i>Test</i></p></html>',
              '/div/p[em="Test"]'),
            ('<html><p><strong>Test</strong></p></html>',
              '/div/p[strong="Test"]'),
            ('<html><p><b>Test</b></p></html>',
              '/div/p[strong="Test"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_span(self):
        data = [
            ('<html><p><sub>sub</sub>script</p></html>',
             '/div/p[sub="sub"]'),
            ('<html><p><sup>super</sup>script</p></html>',
             '/div/p[sup="super"]'),
            ('<html><p><u>underline</u></p></html>',
             '/div/p[ins="underline"]'),
            ('<html><p><big>Test</big></p></html>',
              '/div/p[big="Test"]'),
            ('<html><p><small>Test</small></p></html>',
              '/div/p[small="Test"]'),
            ('<html><p><ins>underline</ins></p></html>',
             '/div/p[ins="underline"]'),
            ('<html><p><del>Test</del></p></html>',
             '/div/p[del="Test"]'),
            ('<html><p><s>Test</s></p></html>',
             '/div/p[del="Test"]'),
            ('<html><p><strike>Test</strike></p></html>',
             '/div/p[del="Test"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_span_html_element(self):
        data = [
            ('<html><p><abbr>Text</abbr></p></html>',
             '/div/p[abbr="Text"]'),
            ('<html><p><acronym>Text</acronym></p></html>',
             '/div/p[acronym="Text"]'),
            ('<html><p><address>Text</address></p></html>',
             '/div/p[address="Text"]'),
            ('<html><p><dfn>Text</dfn></p></html>',
             '/div/p[dfn="Text"]'),
            ('<html><p><kbd>Text</kbd></p></html>',
             '/div/p[kbd="Text"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_link(self):
        data = [
            ('<html><p><a href="uri:test">Test</a></p></html>',
              '/div/p/a[@href="uri:test"] | /div/p[a="Test"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_code(self):
        py.test.skip()
        data = [
            ('<html><div><code>Code</code></div></html>',
             '/div/div[code="Code"]'),
            ('<html><div><samp>Code</samp></div></html>',
             '/div/div[code="Code"]'),
            ('<html><pre>Code</pre></html>',
              '/div[blockcode="Code"]'),
            ('<html><p><tt>Code</tt></p></html>',
              '/div/p[code="Code"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        py.test.skip()
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
              '/page/body/div/list[@item-label-generate="ordered" and @list-style-type="downer-alpha"]/list-item[list-item-body="Item"]'),
            ('<html><div><ol type="i"><li>Item</li></ol></div></html>',
              '/page/body/div/list[@item-label-generate="ordered" and @list-style-type="downer-roman"]/list-item[list-item-body="Item"]'),
            ('<html><div><dl><dt>Label</dt><dd>Item</dd></dl></div></html>',
             '/page/body/div/list/list-item[list-item-label="Label"] | /page/body/div/list/list-item[list-item-body="Item"]'),
            ('<html><div><dir><li>Item</li></dir></div></html>',
              '/page/body/div/list[@item-label-generate="unordered"]/list-item[list-item-body="Item"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_object(self):
        py.test.skip()
        data = [
            ('<html><div><img src="uri:test" /></div></html>',
              '/page/body/div/object/@xlink:href="uri:test"'),
            ('<html><div><object data="href"></object></div></html>',
              '/page/body/div/object/@xlink:href="href"'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_table(self):
        py.test.skip()
        data = [
            ('<html><div><table><thead><tr><td>Header</td></tr></thead><tfoot><tr><td>Footer</td></tr></tfoot><tbody><tr><td>Cell</td></tr></tbody></table></div></html>',
             '/page/body/div/table/table-header/table-row[table-cell="Header"] | /page/body/div/table/table-footer/table-row[table-cell="Footer"] | /page/body/div/table/table-body/table-row[table-cell="Cell"]'),
            ('<html><div><table><tbody><tr><td colspan="2">Cell</td></tr></tbody></table></div></html>',
             '/page/body/div/table/table-body/table-row/table-cell[@number-colmuns-spanned="2"] | /page/body/div/table/table-body/table-row[table-cell="Cell"]'),
            ('<html><div><table><tbody><tr><td rowspan="2">Cell</td></tr></tbody></table></div></html>',
             '/page/body/div/table/table-body/table-row/table-cell[@number-rows-spanned="2"] | /page/body/div/table/table-body/table-row[table-cell="Cell"]'),
        ]
        for i in data:
            yield (self.do, ) + i
