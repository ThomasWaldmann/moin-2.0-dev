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
    input_namespaces = ns_all = 'xmlns="%s"' % (
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
             '/page/body/list[@item-label-generate="Ordered"][list-item[1]/list-item-body[text()="Ordered Item 1"]][list-item[2]/list-item-body[text()="Ordered Item 2"]]'),
            # VARIABLE LIST --> list
            ('<article><variablelist><varlistentry><term>Term 1</term><listitem>Definition 1</listitem></varlistentry><varlistentry><term>Term 2</term><listitem>Definition 2</listitem></varlistentry></variablelist></article>',
            '/page/body/list[list-item[1][list-item-label="Term 1"][list-item-body="Definition 1"]][list-item[2][list-item-label="Term 2"][list-item-body="Definition 2"]]'),
        ]
        for i in data:
            yield (self.do, ) + i

