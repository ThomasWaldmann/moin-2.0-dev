"""
MoinMoin - Tests for moinwiki->DOM->moinwiki using moinwiki_in and moinwiki_out converters

It is merege of test_moinwiki_in and test_moinwiki_out, looks bad but works.

@copyright: 2008 MoinMoin:BastianBlank
            2010 MoinMoin:DmitryAndreev
@license: GNU GPL, see COPYING for details.
"""

import py.test
import re

from emeraldtree import ElementTree as ET
from MoinMoin.util.tree import moin_page, xlink
from MoinMoin.converter2.moinwiki_in import Converter as conv_in
from MoinMoin.converter2.moinwiki_out import Converter as conv_out


class TestConverter(object):

    input_namespaces =  'xmlns="%s" xmlns:page="%s" xmlns:xlink="%s"' % (
        moin_page.namespace,
        moin_page.namespace,
        xlink.namespace)

    namespaces = {
        moin_page.namespace: 'page',
        xlink.namespace: 'xlink',
    }
    input_re = re.compile(r'^(<[a-z:]+)')
    output_re = re.compile(r'\s+xmlns(:\S+)?="[^"]+"')

    def setup_class(self):
        self.conv_in = conv_in(self.request)
        self.conv_out = conv_out(self.request) 

    def test_base(self):
        data = [
            (u'Text',
                'Text'),
        ]
        for i in data:
            yield (self.do, ) + i

    def handle_input(self, input):
        i = self.input_re.sub(r'\1 ' + self.input_namespaces, input)
        return ET.XML(i)

    def handle_output(self, elem, **options):
        from cStringIO import StringIO
        file = StringIO()
        file.write(elem)
        return elem
    
    def serialize(self, elem, **options):
        from StringIO import StringIO
        file = StringIO()
        elem.write(file.write, namespaces=self.namespaces, **options)
        return self.output_re.sub(u'', file.getvalue())

    def do(self, input, output, args={}, skip=None):
        if skip:
            py.test.skip(skip)
        out = self.conv_in(input.split(u'\n'), **args)
        out = self.conv_out(self.handle_input(self.serialize(out)), **args)
        assert self.handle_output(out) == output

