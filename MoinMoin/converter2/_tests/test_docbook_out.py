"""
MoinMoin - Tests for MoinMoin.converter2.docbook_out

@copyright: 2010 MoinMoin:ValentinJaniaut
@license: GNU GPL, see COPYING for details.
"""

import re
import StringIO

import py.test
try:
    from lxml import etree
except:
    py.test.skip("lxml module required to run test for docbook_out converter.")

from emeraldtree.tree import *

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.converter2.docbook_out import *

class Base(object):
    input_namespaces = ns_all = 'xmlns="%s" xmlns:page="%s" xmlns:html="%s" xmlns:xlink="%s"' % (
        moin_page.namespace,
        moin_page.namespace,
        html.namespace,
        xlink.namespace)
    output_namespaces = {
        docbook.namespace: '',
        moin_page.namespace: 'page',
        xlink.namespace: 'xlink'
    }

    namespaces_xpath = {'xlink': xlink.namespace}

    input_re = re.compile(r'^(<[a-z:]+)')
    output_re = re.compile(r'\s+xmlns="[^"]+"')

    def handle_input(self, input):
        i = self.input_re.sub(r'\1 ' + self.input_namespaces, input)
        return ET.XML(i)

    def handle_output(self, elem, **options):
        file = StringIO.StringIO()
        tree = ET.ElementTree(elem)
        tree.write(file, namespaces=self.output_namespaces, **options)
        return self.output_re.sub(u'', file.getvalue())

    def do(self, input, xpath, args={}):
        out = self.conv(self.handle_input(input), **args)
        string_to_parse = self.handle_output(out)
        logging.debug("After the docbook_OUT conversion : %s" % string_to_parse)
        tree = etree.parse(StringIO.StringIO(string_to_parse))
        assert (tree.xpath(xpath, namespaces=self.namespaces_xpath))

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

    def test_title(self):
        data = [
            ('<page><body><h page:outline-level="1">Heading 1</h><p>First</p><h page:outline-level="2">Heading 2</h><p>Second</p></body></page>',
             '/article/sect1[title="Heading 1"][para="First"]/sect2[title="Heading 2"][para="Second"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            # Simple unordered list
            ('<page><body><list page:item-label-generate="unordered"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>',
             '/article/itemizedlist[listitem[1]/para[text()="Item 1"]][listitem[2]/para[text()="Item 2"]]'),
            # Simple ordered list (use default arabic numeration)
            ('<page><body><list page:item-label-generate="ordered"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>',
             '/article/orderedlist[@numeration="arabic"][listitem[1]/para[text()="Item 1"]][listitem[2]/para[text()="Item 2"]]'),
            # Simple ordered list with upper-alpha numeration
            ('<page><body><list page:item-label-generate="ordered" page:list-style-type="upper-alpha"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>',
             '/article/orderedlist[@numeration="upperalpha"][listitem[1]/para[text()="Item 1"]][listitem[2]/para[text()="Item 2"]]'),
            # Simple ordered list with lower-alpha numeration
            ('<page><body><list page:item-label-generate="ordered" page:list-style-type="lower-alpha"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>',
             '/article/orderedlist[@numeration="loweralpha"][listitem[1]/para[text()="Item 1"]][listitem[2]/para[text()="Item 2"]]'),
            # Simple ordered list with upper-roman numeration
            ('<page><body><list page:item-label-generate="ordered" page:list-style-type="upper-roman"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>',
             '/article/orderedlist[@numeration="upperroman"][listitem[1]/para[text()="Item 1"]][listitem[2]/para[text()="Item 2"]]'),
            # Simple ordered list with lower-roman numeration
            ('<page><body><list page:item-label-generate="ordered" page:list-style-type="lower-roman"><list-item><list-item-body>Item 1</list-item-body></list-item><list-item><list-item-body>Item 2</list-item-body></list-item></list></body></page>',
             '/article/orderedlist[@numeration="lowerroman"][listitem[1]/para[text()="Item 1"]][listitem[2]/para[text()="Item 2"]]'),
            # Simple definition list
            ('<page><body><list><list-item><list-item-label>First Term</list-item-label><list-item-body>First Definition</list-item-body></list-item><list-item><list-item-label>Second Term</list-item-label><list-item-body>Second Definition</list-item-body></list-item></list></body></page>',
             '/article/variablelist[varlistentry[1][./term[text()="First Term"]][./listitem/para[text()="First Definition"]]][varlistentry[2][./term[text()="Second Term"]][./listitem/para[text()="Second Definition"]]]')
        ]

        for i in data:
            yield (self.do, ) + i

    def test_table(self):
        data = [
            ('<page><body><table><table-header><table-row><table-cell>Header</table-cell></table-row></table-header><table-footer><table-row><table-cell>Footer</table-cell></table-row></table-footer><table-body><table-row><table-cell>Cell</table-cell></table-row></table-body></table></body></page>',
                '/article/table[thead/tr[td="Header"]][tfoot/tr[td="Footer"]][tbody/tr[td="Cell"]]'),
            ('<page><body><table><table-body><table-row><table-cell page:number-columns-spanned="2">Cell</table-cell></table-row></table-body></table></body></page>',
                '/article/table/tbody/tr/td[@colspan="2"][text()="Cell"]'),
            ('<page><body><table><table-body><table-row><table-cell page:number-rows-spanned="2">Cell</table-cell></table-row></table-body></table></body></page>',
                '/article/table/tbody/tr/td[@rowspan="2"][text()="Cell"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_paragraph_elements(self):
        data = [
            # Footnote conversion
            ('<page><body><p>Text Para<note page:note-class="footnote"><note-body>Text Footnote</note-body></note></p></body></page>',
             '/article/para[text()="Text Para"]/footnote[para="Text Footnote"]'),
            # Link conversion
            ('<page><body><p><a xlink:href="uri:test" xlink:title="title">link</a></p></body></page>',
              '/article/para/link[@xlink:href="uri:test"][@xlink:title="title"][text()="link"]'),
            # Blockcode conversion into <screen> with CDATA
            ('<page><body><blockcode>Text</blockcode></body></page>',
             '/article[screen="<![CDATA[Text]]>"]'),
            # SPAN --> PHRASE
            ('<page><body><p><span>Text</span></p></body></page>',
             '/article/para[phrase="Text"]'),
            # SPAN baseline-shift=sub --> subscript
            ('<page><body><p>sub<span page:baseline-shift="sub">sub</span>script</p></body></page>',
             '/article/para[text()="script"][subscript="sub"]'),
            # SPAN baseline-shift=super --> superscript
            ('<page><body><p>sub<span page:baseline-shift="super">super</span>script</p></body></page>',
             '/article/para[text()="script"][superscript="super"]'),
            # STRONG --> EMPHASIS role='strong'
            ('<page><body><p>text<strong>strong</strong></p></body></page>',
             '/article/para[text()="text"]/emphasis[@role="strong"][text()="strong"]'),
            # EMPHASIS --> EMPHASIS
            ('<page><body><p>text<emphasis>emphasis</emphasis></p></body></page>',
             '/article/para[text()="text"][emphasis="emphasis"]'),
        ]
        for i in data:
            yield (self.do, ) + i
