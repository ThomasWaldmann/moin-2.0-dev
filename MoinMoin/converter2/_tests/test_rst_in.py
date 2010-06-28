"""
MoinMoin - Tests for MoinMoin.converter2.rst_in

@copyright: 2008 MoinMoin:BastianBlank
            2010 MoinMoin:DmitryAndreev
@license: GNU GPL, see COPYING for details.
"""

import py.test
import re

from MoinMoin.converter2.rst_in import *


class TestConverter(object):
    namespaces = {
        moin_page.namespace: '',
        xlink.namespace: 'xlink',
    }

    output_re = re.compile(r'\s+xmlns(:\S+)?="[^"]+"')

    def setup_class(self):
        self.conv = Converter()

    def test_base(self):
        data = [
            (u'Text',
                '<page><body><p>Text</p></body></page>'),
            (u'Text\nTest',
                '<page><body><p>Text\nTest</p></body></page>'),
            (u'Text\n\nTest',
                '<page><body><p>Text</p><p>Test</p></body></page>'),
            (u'H\ :sub:`2`\ O\n\nE = mc\ :sup:`2`',''),

        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            (u'1. a\n2. b\n\nA. c\nc\n\n   e\n\na. A\n\n   3. B\n\n   4. C\n\n',''),
            (u'* A\n\n   - B\n\n      + C\n\n   - D\n\n* E', ''),
            (u'what\n      def\n\nhow\n      to', '')
            ]
        for i in data:
            yield (self.do, ) + i

    def test_image(self):
        data = [
            (u'.. image:: images/biohazard.png', ''),
            ]
        for i in data:
            yield (self.do, ) + i

    def test_headers(self):
        data = [
            (u'Chapter 1 Title\n===============\n\nSection 1.1 Title\n-----------------\n\nSubsection 1.1.1 Title\n~~~~~~~~~~~~~~~~~~~~~~\n\nSection 1.2 Title\n-----------------\n\nChapter 2 Title\n===============\n',''),
            (u'================\n Document Title\n================\n\n----------\n Subtitle\n----------\n\nSection Title\n=============', '')
            ]
        for i in data:
            yield (self.do, ) + i

    def test_footnote(self):
        data = [
            (u'Abra [1]_\n\n.. [1] arba', ''),
            (u'Abra [#]_\n\n.. [#] arba', ''),
            ]
        for i in data:
            yield (self.do, ) + i

    def test_link(self):
        data = [
            (u'Abra test_ arba\n\n.. _test: http://python.org', ''),
            ]
        for i in data:
            yield (self.do, ) + i
    
    def test_table(self):
        data = [
            (u"+-+-+-+\n|A|B|D|\n+-+-+ +\n|C  | |\n+---+-+\n\n", '<table><table-body><table-row><table-cell>A</table-cell><table-cell>B</table-cell><table-cell number-rows-spanned=\"2\">D</table-cell></table-row><table-row><table-cell number-columns-spanned=\"2\">C</table-cell></table-row></table-body></table>'),
            (u"+-----+-----+-----+\n|**A**|**B**|**C**|\n+-----+-----+-----+\n|1    |2    |3    |\n+-----+-----+-----+\n\n", '<table><table-body><table-row><table-cell><strong>A</strong></table-cell><table-cell><strong>B</strong></table-cell><table-cell><strong>C</strong></table-cell></table-row><table-row><table-cell><p>1</p></table-cell><table-cell>2</table-cell><table-cell>3</table-cell></table-row></table-body></table>'),
            ("""+--------------------+-------------------------------------+
|cell spanning 2 rows|cell in the 2nd column               |
+                    +-------------------------------------+
|                    |cell in the 2nd column of the 2nd row|
+--------------------+-------------------------------------+
|test                                                      |
+----------------------------------------------------------+
|test                                                      |
+----------------------------------------------------------+

""", '<table><table-body><table-row><table-cell number-rows-spanned=\"2\">cell spanning 2 rows</table-cell><table-cell>cell in the 2nd column</table-cell></table-row><table-row><table-cell>cell in the 2nd column of the 2nd row</table-cell></table-row><table-row><table-cell number-columns-spanned=\"2\">test</table-cell></table-row><table-row><table-cell number-columns-spanned=\"2\">test</table-cell></table-row></table-body></table>'),
        ]
        for i in data:
            yield (self.do, ) + i

    def serialize(self, elem, **options):
        from StringIO import StringIO
        file = StringIO()
        elem.write(file.write, namespaces=self.namespaces, **options)
        return self.output_re.sub(u'', file.getvalue())

    def do(self, input, output, args={}, skip=None):
        if skip:
            py.test.skip(skip)
        out = self.conv(input, **args)
        print self.serialize(out) # delete this
        assert self.serialize(out) == output

