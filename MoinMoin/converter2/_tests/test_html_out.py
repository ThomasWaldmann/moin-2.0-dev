"""
MoinMoin - Tests for MoinMoin.converter2.html_out

@copyright: 2007 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test
import re

try:
    from lxml import etree
except:
    py.test.skip("lxml module required to run test for html_in converter.")

from MoinMoin.converter2.html_out import *
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
        html.namespace: '',
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
        tree.write(file, namespaces=self.output_namespaces, **options)
        return self.output_re.sub(u'', file.getvalue())

    def do(self, input, xpath, args={}):
        out = self.conv(self.handle_input(input), **args)
        string_to_parse = self.handle_output(out)
        logging.debug("After the HTML_OUT conversion : %s" % string_to_parse)
        tree = etree.parse(StringIO.StringIO(string_to_parse))
        assert (tree.xpath(xpath))

class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter(self.request)

    def test_base(self):
        data = [
            ('<page:page><page:body><page:p>Test</page:p></page:body></page:page>',
                '/div[p="Test"]'),
            ('<page:page><page:body><page:h>Test</page:h></page:body></page:page>',
                '/div[h1="Test"]'),
            ('<page:page><page:body><page:h page:outline-level="2">Test</page:h></page:body></page:page>',
                '/div[h2="Test"]'),
            ('<page:page><page:body><page:h page:outline-level="6">Test</page:h></page:body></page:page>',
                '/div[h6="Test"]'),
            ('<page:page><page:body><page:h page:outline-level="7">Test</page:h></page:body></page:page>',
                '/div[h6="Test"]'),
            ('<page:page><page:body><page:a xlink:href="uri:test">Test</page:a></page:body></page:page>',
              '/div/a[text()="Test"][@href="uri:test"]'),
            ('<page:page><page:body><page:p>Test<page:line-break/>Test</page:p></page:body></page:page>',
                '/div/p/br'),
            ('<page:page><page:body><page:p>Test<page:span>Test</page:span></page:p></page:body></page:page>',
                '/div/p[text()="Test"]/span[text()="Test"]'),
            ('<page:page><page:body><page:p><page:emphasis>Test</page:emphasis></page:p></page:body></page:page>',
                '/div/p[em="Test"]'),
            ('<page:page><page:body><page:p><page:strong>Test</page:strong></page:p></page:body></page:page>',
                '/div/p[strong="Test"]'),
            ('<page:page><page:body><page:blockcode>Code</page:blockcode></page:body></page:page>',
                '/div[pre="Code"]'),
            ('<page:page><page:body><page:p><page:code>Code</page:code></page:p></page:body></page:page>',
                '/div/p[tt="Code"]'),
            ('<page:page><page:body><page:separator/></page:body></page:page>',
                '/div/hr'),
            ('<page:page><page:body><page:div><page:p>Text</page:p></page:div></page:body></page:page>',
                '/div/div[p="Text"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_body(self):
        data = [
            ('<page><body /></page>',
                '/div'),
            ('<page><body class="red" /></page>',
                '/div[@class="red"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_html(self):
        data = [
            ('<html:div html:id="a" id="b"><html:p id="c">Test</html:p></html:div>',
                '/div[@id="a"]/p[@id="c"][text()="Test"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_inline_part(self):
        data = [
            ('<page><body><p><inline-part><inline-body>Test</inline-body></inline-part></p></body></page>',
                '/div/p[span="Test"]'),
            ('<page><body><p><inline-part alt="Alt" /></p></body></page>',
                '/div/p[span="Alt"]'),
            ('<page><body><p><inline-part><error /></inline-part></p></body></page>',
                '/div/p/span[@class="error"][text()="Error"]'),
            ('<page><body><p><inline-part><error>Text</error></inline-part></p></body></page>',
                '/div/p/span[@class="error"][text()="Text"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_span(self):
        data = [
            ('<page><body><p><span baseline-shift="sub">sub</span>script</p></body></page>',
                '/div/p[text()="script"][sub="sub"]'),
            ('<page><body><p><span baseline-shift="super">super</span>script</p></body></page>',
                '/div/p[text()="script"][sup="super"]'),
            ('<page><body><p><span text-decoration="underline">underline</span></p></body></page>',
                '/div/p[ins="underline"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            ('<page><body><list item-label-generate="unordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>',
                '/div/ul[li="Item"]'),
            ('<page><body><list item-label-generate="ordered"><list-item><list-item-body>Item</list-item-body></list-item></list></body></page>',
                '/div/ol[li="Item"]'),
            ('<page><body><list><list-item><list-item-label>Label</list-item-label><list-item-body>Item</list-item-body></list-item></list></body></page>',
                '/div/dl[dt="Label"][dd="Item"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_object(self):
        data = [
            ('<page><body><object xlink:href="href"/></body></page>',
                '/div/object[@data="href"]'),
            ('<page><body><object xlink:href="href.png"/></body></page>',
                '/div/img[@src="href.png"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_part(self):
        data = [
            ('<page><body><part><body><p>Test</p></body></part></body></page>',
                '/div/div[p="Test"]'),
            ('<page><body><part alt="Alt" /></body></page>',
                '/div[p="Alt"]'),
            ('<page><body><part><error /></part></body></page>',
                '/div/p[text()="Error"][@class="error"]'),
            ('<page><body><part><error>Error</error></part></body></page>',
                '/div/p[@class="error"][text()="Error"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_style(self):
        data = [
            ('<page><body><p style="font-size: 1em">Text</p></body></page>',
              '/div/p[@style="font-size: 1em"][text()="Text"]'),
            ('<page><body><p style="color: black; font-size: 1em">Text</p></body></page>',
              '/div/p[@style="color: black; font-size: 1em"][text()="Text"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_table(self):
        data = [
            ('<page><body><table><table-header><table-row><table-cell>Header</table-cell></table-row></table-header><table-footer><table-row><table-cell>Footer</table-cell></table-row></table-footer><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>',
                '/div/table[thead/tr[td="Header"]][tfoot/tr[td="Footer"]][tbody/tr[td="Cell"]]'),
            ('<page><body><table><table-body><table-row><table-cell number-columns-spanned="2">Cell</table-cell></table-row></table-body></table></body></page>',
                '/div/table/tbody/tr/td[@colspan="2"][text()="Cell"]'),
            ('<page><body><table><table-body><table-row><table-cell number-rows-spanned="2">Cell</table-cell></table-row></table-body></table></body></page>',
                '/div/table/tbody/tr/td[@rowspan="2"][text()="Cell"]'),
        ]
        for i in data:
            yield (self.do, ) + i


class TestConverterPage(Base):
    def setup_class(self):
        self.conv = ConverterPage(self.request)

    def test_note(self):
        data = [
            ('<page><body><p>Text<note note-class="footnote"><note-body>Note</note-body></note></p></body></page>',
                '/div[p[text()="Text"]/sup[@id="note-1-ref"]/a[@href="#note-1"][text()="1"]][p[@id="note-1"][text()="Note"]/sup/a[@href="#note-1-ref"][text()="1"]]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_unknown(self):
        page = ET.XML("<page:unknown %s/>" % self.input_namespaces)
        py.test.raises(ElementException, self.conv.__call__, page)
