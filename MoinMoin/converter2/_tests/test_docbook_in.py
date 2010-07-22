# -*- coding: utf-8 -*-
"""
MoinMoin - Tests for MoinMoin.converter2.docbook_in

@copyright: 2010 MoinMoin:ValentinJaniaut
@license: GNU GPL, see COPYING for details.
"""

import py.test
import re

try:
    from lxml import etree
except:
    py.test.skip("lxml module required to run test for docbook_in converter.")

from MoinMoin.converter2.docbook_in import *
from emeraldtree.tree import *
from MoinMoin import log
logging = log.getLogger(__name__)
import StringIO

class Base(object):
    input_namespaces = ns_all = u'xmlns="%s" xmlns:db="%s" xmlns:xlink="%s"' % (
        docbook.namespace,
        docbook.namespace,
        xlink.namespace)

    output_namespaces = {
        moin_page.namespace: u'',
        xlink.namespace: u'xlink',
    }

    namespaces_xpath = {'xlink': xlink.namespace}

    input_re = re.compile(r'^(<[a-z:]+)')
    output_re = re.compile(r'\s+xmlns="[^"]+"')

    def handle_input(self, input):
        return self.input_re.sub(r'\1 ' + self.input_namespaces, input)

    def handle_output(self, input, args):
        to_conv = self.handle_input(input)
        out = self.conv(to_conv, **args)
        f = StringIO.StringIO()
        out.write(f.write, namespaces=self.output_namespaces, )
        return self.output_re.sub(u'', f.getvalue())


    def do(self, input, xpath_query):
        string_to_parse = self.handle_output(input, args={})
        logging.debug(u"After the DOCBOOK_IN conversion : %s" % string_to_parse)
        tree = etree.parse(StringIO.StringIO(string_to_parse))
        assert (tree.xpath(xpath_query, namespaces=self.namespaces_xpath))

class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter()

    def test_base(self):
        data = [
            ('<article><para>Test</para></article>',
            # <page><body><p>Test</p></body></page>
             '/page/body[p="Test"]'),
            ('<article><sect1><title>Heading 1</title> <para>First Paragraph</para></sect1></article>',
            # <page><body><h outline-level="1">Heading 1</h><p>First Paragraph</p></body></page>
             '/page/body[./h[@outline-level="1"][text()="Heading 1"]][./p[text()="First Paragraph"]]'),
            # Test for conversion with unicode char
            (u'<article><para>안녕 유빈</para></article>',
            # <page><body><p>안녕 유빈</p></body></page>
             u'/page/body[p="안녕 유빈"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_title(self):
        data = [
            # Test simple numbered section conversion into headings.
            ('<article><sect1><title>Heading 1</title> <para>First</para><sect2><title>Heading 2</title><para>Second</para></sect2></sect1></article>',
            # <page><body><h outline-level="1">Heading 1</h><p>First</p><h outline-level="2">Heading 2</h><p>Second</p></body></page>
             '/page/body[h[1][@outline-level="1"][text()="Heading 1"]][p[1][text()="First"]][h[2][@outline-level="2"][text()="Heading 2"]][p[2][text()="Second"]]'),
            ('<article><section><title>Heading 1</title> <para>First</para><section><title>Heading 2</title><para>Second</para></section></section></article>',
            # <page><body><h outline-level="1">Heading 1</h><p>First</p><h outline-level="2">Heading 2</h><p>Second</p></body></page>
             '/page/body[h[1][@outline-level="1"][text()="Heading 1"]][p[1][text()="First"]][h[2][@outline-level="2"][text()="Heading 2"]][p[2][text()="Second"]]'),
            # Test complex recursive section conversion into headings.
            ('<article><section><title>Heading 1 A</title><para>First</para><section><title>Heading 2 A</title><para>Second</para><section><title>Heading 3 A</title><para>Third</para></section></section></section><section><title>Heading 1 B</title><para>Fourth</para></section></article>',
            # <page><body><h outline-level="1">Heading 1 A</h><p>First</p><h outline-level="2">Heading 2 A</h><p>Second</p><h outline-level="3">Heading 3 A</h><p>Third</p><h outline-level="1">Heading 1 B</h><p>Fourth</p></body></page>
             '/page/body[h[1][@outline-level="1"][text()="Heading 1 A"]][p[1][text()="First"]][h[2][@outline-level="2"][text()="Heading 2 A"]][p[2][text()="Second"]][h[3][@outline-level="3"][text()="Heading 3 A"]][p[3][text()="Third"]][h[4][@outline-level="1"][text()="Heading 1 B"]][p[4][text()="Fourth"]]'),
        ]

        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            # ITEMIZED LIST --> unordered list
            ('<article><itemizedlist><listitem>Unordered Item 1</listitem><listitem>Unordered Item 2</listitem></itemizedlist></article>',
            # <page><body><list item-label-generate="unordered"><list-item><list-item-body>Unordered Item 1</list-item-body></list-item><list-item><list-item-body>Unordered Item 2</list-item-body></list-item></list></body></page>
             '/page/body/list[@item-label-generate="unordered"][list-item[1]/list-item-body[text()="Unordered Item 1"]][list-item[2]/list-item-body[text()="Unordered Item 2"]]'),
            # ORDERED LIST --> ordered list
            ('<article><orderedlist><listitem>Ordered Item 1</listitem><listitem>Ordered Item 2</listitem></orderedlist></article>',
            # <page><body><list item-label-generate="ordered"><list-item><list-item-body>Ordered Item 1</list-item-body></list-item><list-item><list-item-body>Ordered Item 2</list-item-body></list-item></list></body></page>
             '/page/body/list[@item-label-generate="ordered"][list-item[1]/list-item-body[text()="Ordered Item 1"]][list-item[2]/list-item-body[text()="Ordered Item 2"]]'),
            # ORDERED LIST with upperalpha numeration --> ordered list with upper-alpha list-style-type
            ('<article><orderedlist db:numeration="upperalpha"><listitem>Ordered Item 1</listitem><listitem>Ordered Item 2</listitem></orderedlist></article>',
             '/page/body/list[@item-label-generate="ordered"][@list-style-type="upper-alpha"][list-item[1]/list-item-body[text()="Ordered Item 1"]][list-item[2]/list-item-body[text()="Ordered Item 2"]]'),
            # ORDERED LIST with loweralpha numeration --> ordered list with lower-alpha list-style-type
            ('<article><orderedlist db:numeration="loweralpha"><listitem>Ordered Item 1</listitem><listitem>Ordered Item 2</listitem></orderedlist></article>',
             '/page/body/list[@item-label-generate="ordered"][@list-style-type="lower-alpha"][list-item[1]/list-item-body[text()="Ordered Item 1"]][list-item[2]/list-item-body[text()="Ordered Item 2"]]'),
            # ORDERED LIST with upperroman numeration --> ordered list with upper-roman list-style-type
            ('<article><orderedlist db:numeration="upperroman"><listitem>Ordered Item 1</listitem><listitem>Ordered Item 2</listitem></orderedlist></article>',
             '/page/body/list[@item-label-generate="ordered"][@list-style-type="upper-roman"][list-item[1]/list-item-body[text()="Ordered Item 1"]][list-item[2]/list-item-body[text()="Ordered Item 2"]]'),
            # ORDERED LIST with lowerroman numeration --> ordered list with lower-roman list-style-type
            ('<article><orderedlist db:numeration="lowerroman"><listitem>Ordered Item 1</listitem><listitem>Ordered Item 2</listitem></orderedlist></article>',
             '/page/body/list[@item-label-generate="ordered"][@list-style-type="lower-roman"][list-item[1]/list-item-body[text()="Ordered Item 1"]][list-item[2]/list-item-body[text()="Ordered Item 2"]]'),
            # VARIABLE LIST --> list
            ('<article><variablelist><varlistentry><term>Term 1</term><listitem>Definition 1</listitem></varlistentry><varlistentry><term>Term 2</term><listitem>Definition 2</listitem></varlistentry></variablelist></article>',
            '/page/body/list[list-item[1][list-item-label="Term 1"][list-item-body="Definition 1"]][list-item[2][list-item-label="Term 2"][list-item-body="Definition 2"]]'),
            # PROCEDURE --> ordered list (with arabic numeration)
            ('<article><procedure><step>First Step</step><step>Second Step</step></procedure></article>',
             '/page/body/list[@item-label-generate="ordered"][list-item[1]/list-item-body[text()="First Step"]][list-item[2]/list-item-body[text()="Second Step"]]'),
            # GLOSS LIST --> Definition list
            ('<article><glosslist><glossentry><glossterm>Term 1</glossterm><glossdef><para>Definition 1</para></glossdef></glossentry><glossentry><glossterm>Term 2</glossterm><glossdef><para>Definition 2</para></glossdef></glossentry></glosslist></article>',
            '/page/body/list[list-item[1][list-item-label="Term 1"][list-item-body[p="Definition 1"]]][list-item[2][list-item-label="Term 2"][list-item-body[p="Definition 2"]]]'),
            # SEGMENTED LIST --> Definition List
            ('<article><segmentedlist><segtitle>Term 1</segtitle><segtitle>Term 2</segtitle><segtitle>Term 3</segtitle><seglistitem><seg>Def 1:1</seg><seg>Def 1:2</seg><seg>Def 1:3</seg></seglistitem><seglistitem><seg>Def 2:1</seg><seg>Def 2:2</seg><seg>Def 2:3</seg></seglistitem></segmentedlist></article>',
              '/page/body/list[list-item[1][list-item-label="Term 1"][list-item-body="Def 1:1"]][list-item[2][list-item-label="Term 2"][list-item-body="Def 1:2"]][list-item[3][list-item-label="Term 3"][list-item-body="Def 1:3"]][list-item[4][list-item-label="Term 1"][list-item-body="Def 2:1"]][list-item[5][list-item-label="Term 2"][list-item-body="Def 2:2"]][list-item[6][list-item-label="Term 3"][list-item-body="Def 2:3"]]'),
            # SIMPLE LIST --> unordered list
            ('<article><simplelist><member>Item 1</member><member>Item 2</member></simplelist></article>',
             '/page/body/list[@item-label-generate="unordered"][list-item[1]/list-item-body[text()="Item 1"]][list-item[2]/list-item-body[text()="Item 2"]]'),
            # Q and A set with defaultlabel = number --> ordered list
            ("<article><qandaset db:defaultlabel='number'><qandaentry><question><para>Question 1</para></question><answer><para>Answer 1</para></answer></qandaentry><qandaentry><question><para>Question 2</para></question><answer><para>Answer 2</para></answer></qandaentry></qandaset></article> ",
             '/page/body/list[@item-label-generate="ordered"][list-item[1]/list-item-body[p[1][text()="Question 1"]][p[2][text()="Answer 1"]]][list-item[2]/list-item-body[p[1][text()="Question 2"]][p[2][text()="Answer 2"]]]'),
            # Q and A set with defaultlabel = qanda --> definition list, with Q: and A: for the label
            ("<article><qandaset db:defaultlabel='qanda'><qandaentry><question><para>Question 1</para></question><answer><para>Answer 1</para></answer></qandaentry><qandaentry><question><para>Question 2</para></question><answer><para>Answer 2</para></answer></qandaentry></qandaset></article> ",
              '/page/body/list[list-item[1][list-item-label="Q:"][list-item-body="Question 1"]][list-item[2][list-item-label="A:"][list-item-body="Answer 1"]][list-item[3][list-item-label="Q:"][list-item-body="Question 2"]][list-item[4][list-item-label="A:"][list-item-body="Answer 2"]]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_table(self):
        data = [
            ('<article><table><thead><tr><td>Header</td></tr></thead><tfoot><tr><td>Footer</td></tr></tfoot><tbody><tr><td>Cell</td></tr></tbody></table></article>',
             '/page/body/table[./table-header/table-row[table-cell="Header"]][./table-footer/table-row[table-cell="Footer"]][./table-body/table-row[table-cell="Cell"]]'),
            ('<article><table><tbody><tr><td db:colspan="2">Cell</td></tr></tbody></table></article>',
             '/page/body/table/table-body/table-row/table-cell[text()="Cell"][@number-columns-spanned="2"]'),
            ('<article><table><tbody><tr><td db:rowspan="2">Cell</td></tr></tbody></table></article>',
             '/page/body/table/table-body/table-row/table-cell[text()="Cell"][@number-rows-spanned="2"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_misc(self):
        data = [
            ('<article><para>Text Para<footnote><para>Text Footnote</para></footnote></para></article>',
             '/page/body/p[text()="Text Para"]/note[@note-class="footnote"]/note-body/p[text()="Text Footnote"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_link(self):
        data = [
            # Normal link, with conversion of all the xlink attributes
            ('<article><para><link xlink:href="uri:test" xlink:title="title">link</link></para></article>',
             '/page/body/p/a[@xlink:href="uri:test"][@xlink:title="title"][text()="link"]'),
            # XREF link TODO : Check that it works with any href attribute
            #('<article><para><xref xlink:href="uri:test" xlink:title="title">link</link></para></article>',
            # '/page/body/p/a[@xlink:href="uri:test"][@xlink:title="title"][text()="link"]'),
            # Old link from DocBook v.4.X for backward compatibility
            ('<article><para><ulink url="url:test">link</ulink></para></article>',
             '/page/body/p/a[@xlink:href="url:test"][text()="link"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_code(self):
        data = [
            ('<article><screen>Text</screen></article>',
             '/page/body[blockcode="Text"]'),
            # Test for <screen> with CDATA
            ('<article><screen><![CDATA[Text]]></screen></article>',
             '/page/body[blockcode="Text"]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_object(self):
        data = [
            # Test for image conversion
            ('<article><para><inlinemediaobject><imageobject><imagedata fileref="test.png"/></imageobject></inlinemediaobject></para></article>',
              '/page/body/object/@xlink:href="test.png"'),
        ]
        for i in data:
            yield (self.do, ) + i
