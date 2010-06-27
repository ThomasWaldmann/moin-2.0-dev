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

