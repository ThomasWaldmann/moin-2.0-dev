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
    input_namespaces = ns_all = 'xmlns="%s" xmlns:db="%s"' % (
        docbook.namespace,
        docbook.namespace)

    output_namespaces = {
        moin_page.namespace: '',
        xlink.namespace: 'xlink',
    }

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
        logging.debug("After the DOCBOOK_IN conversion : %s" % string_to_parse)
        tree = etree.parse(StringIO.StringIO(string_to_parse))
        assert (tree.xpath(xpath_query))

class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter()

    def test_base(self):
        data = [
            ('<article><para>Test</para></article>',
             '/page/body[p="Test"]'),
            ('<article><sect1><title>Heading 1</title> <para>First Paragraph</para></sect1></article>',
             '/page/body[./h[@outline-level="1"][text()="Heading 1"]][./p[text()="First Paragraph"]]'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_title(self):
        data = [
            ('<article><sect1><title>Heading 1</title> <para>First</para><sect2><title>Heading 2</title><para>Second</para></sect2></sect1></article>',
             '/page/body[h[1][@outline-level="1"][text()="Heading 1"]][p[1][text()="First"]][h[2][@outline-level="2"][text()="Heading 2"]][p[2][text()="Second"]]'),
        ]

        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            # ITEMIZED LIST --> unordered list
            ('<article><itemizedlist><listitem>Unordered Item 1</listitem><listitem>Unordered Item 2</listitem></itemizedlist></article>',
             '/page/body/list[@item-label-generate="unordered"][list-item[1]/list-item-body[text()="Unordered Item 1"]][list-item[2]/list-item-body[text()="Unordered Item 2"]]'),
            # ORDERED LIST --> ordered list
            ('<article><orderedlist><listitem>Ordered Item 1</listitem><listitem>Ordered Item 2</listitem></orderedlist></article>',
             '/page/body/list[@item-label-generate="ordered"][list-item[1]/list-item-body[text()="Ordered Item 1"]][list-item[2]/list-item-body[text()="Ordered Item 2"]]'),
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

