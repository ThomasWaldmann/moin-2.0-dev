"""
MoinMoin - Tests for MoinMoin.converter2.rst_out

@copyright: 2010 MoinMoin:DmitryAndreev
@license: GNU GPL, see COPYING for details.
"""

import py.test
import re

from MoinMoin.converter2.rst_out import *


class Base(object):
    input_namespaces = ns_all = 'xmlns="%s" xmlns:page="%s" xmlns:xlink="%s"' % (
        moin_page.namespace,
        moin_page.namespace,
        xlink.namespace)
    output_namespaces = {
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
        file.write(elem)
        return elem

    def do(self, input, output, args={}):
        out = self.conv(self.handle_input(input), **args)
        print self.handle_output(out)
        print input
        assert self.handle_output(out) == output


class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter()

    def test_base(self):
        data = [
            (u'<page:p>Text</page:p>', 'Text\n'),
            (u"<page:tag><page:p>Text</page:p><page:p>Text</page:p></page:tag>", 'Text\n\nText\n'),
            (u"<page:separator />", '\n\n----\n\n'),
            (u"<page:strong>strong</page:strong>", "**strong**"),
            (u"<page:emphasis>emphasis</page:emphasis>", "*emphasis*"),
            (u"<page:blockcode>blockcode</page:blockcode>", "::\n\n  blockcode\n\n"),
            (u"<page:code>monospace</page:code>", '``monospace``'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            (u"<page:list page:item-label-generate=\"unordered\"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>", "* A\n\n"),
            (u"<page:list page:item-label-generate=\"ordered\"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>", "1. A\n\n"),
            (u"<page:list page:item-label-generate=\"ordered\" page:list-style-type=\"upper-roman\"><page:list-item><page:list-item-body>A</page:list-item-body></page:list-item></page:list>", "I. A\n\n"),
            (u"<page:list page:item-label-generate=\"unordered\"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>B</page:p><page:list page:item-label-generate=\"ordered\"><page:list-item><page:list-item-body><page:p>C</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>D</page:p><page:list page:item-label-generate=\"ordered\" page:list-style-type=\"upper-roman\"><page:list-item><page:list-item-body><page:p>E</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>F</page:p></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list>", "* A\n\n* B\n\n  1. C\n\n  #. D\n\n     I. E\n\n     #. F\n\n"),
            (u"<page:list><page:list-item><page:list-item-label>A</page:list-item-label><page:list-item-body><page:p>B</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>C</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>D</page:p></page:list-item-body></page:list-item></page:list>", "A\n  B\n\n  C\n\n  D\n\n"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_table(self):
        data = [
            (u"<page:table><page:table-body><page:table-row><page:table-cell>A</page:table-cell><page:table-cell>B</page:table-cell><page:table-cell page:number-rows-spanned=\"2\">D</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-columns-spanned=\"2\">C</page:table-cell></page:table-row></page:table-body></page:table>", "+-+-+-+\n|A|B|D|\n+-+-+ +\n|C  | |\n+---+-+\n\n"),
            (u"<page:table><page:table-body><page:table-row><page:table-cell><page:strong>A</page:strong></page:table-cell><page:table-cell><page:strong>B</page:strong></page:table-cell><page:table-cell><page:strong>C</page:strong></page:table-cell></page:table-row><page:table-row><page:table-cell><page:p>1</page:p></page:table-cell><page:table-cell>2</page:table-cell><page:table-cell>3</page:table-cell></page:table-row></page:table-body></page:table>", u"+-----+-----+-----+\n|**A**|**B**|**C**|\n+-----+-----+-----+\n|1    |2    |3    |\n+-----+-----+-----+\n\n"),
            (u"<page:table><page:table-body><page:table-row><page:table-cell page:number-rows-spanned=\"2\">cell spanning 2 rows</page:table-cell><page:table-cell>cell in the 2nd column</page:table-cell></page:table-row><page:table-row><page:table-cell>cell in the 2nd column of the 2nd row</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-columns-spanned=\"2\">test</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-columns-spanned=\"2\">test</page:table-cell></page:table-row></page:table-body></page:table>", """+--------------------+-------------------------------------+
|cell spanning 2 rows|cell in the 2nd column               |
+                    +-------------------------------------+
|                    |cell in the 2nd column of the 2nd row|
+--------------------+-------------------------------------+
|test                                                      |
+----------------------------------------------------------+
|test                                                      |
+----------------------------------------------------------+

"""),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_p(self):
        data = [
            (u"<page:page><page:body><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:body></page:page>", "A\n\nB\n\nC\n\nD\n"),
            (u"<page:page><page:body><page:table><page:table_row><page:table_cell><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:table_cell></page:table_row></page:table></page:body></page:page>", "+-+\n|A|\n| |\n|B|\n| |\n|C|\n| |\n|D|\n+-+\n\n"),
            (u"<page:page><page:body><page:table><page:table_row><page:table_cell>Z</page:table_cell><page:table_cell><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:table_cell></page:table_row></page:table></page:body></page:page>", "+-+-+\n|Z|A|\n| | |\n| |B|\n| | |\n| |C|\n| | |\n| |D|\n+-+-+\n\n"),
            (u"<page:page><page:body><page:table><page:table_row><page:table_cell>Z</page:table_cell></page:table_row><page:table_row><page:table_cell><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:table_cell></page:table_row></page:table></page:body></page:page>", "+-+\n|Z|\n+-+\n|A|\n| |\n|B|\n| |\n|C|\n| |\n|D|\n+-+\n\n"),
            (u"<page:page><page:body>A<page:list page:item-label-generate=\"unordered\"><page:list-item><page:list-item-body><page:p>A</page:p><page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>A</page:p>A<page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body>A</page:list-item-body></page:list-item></page:list>A</page:body></page:page>", "A\n\n* A\n\n  A\n\n* A\n\n  A\n\n  A\n\n* A\n\nA")
        ]
        for i in data:
            yield (self.do, ) + i
