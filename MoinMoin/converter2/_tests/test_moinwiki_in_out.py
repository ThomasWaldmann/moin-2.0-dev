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
            (u"=== Text: ===\n'''strong'''\n''emphasis''\n{{{blockcode}}}\n`monospace`",''),
            (u"=== Table: ===\n||A||B||<|2>D||\n||||C||\n", ''),
            (u"=== List: ===\n * A\n  1. C\n  1. D\n", ''),
            (u"=== Span: ===\n--(stroke)--\n__underline__\n~+larger+~\n~-smaller-~\n^super^script\n,,sub,,script\n", ''),
            (u" * A\n * B\n * C\n * D\n * E\n * F", ''),
            (u" * A\n * B\n i. C\n i. D\n 1. E\n 1. F\n i. G\n 1. H\n", ''),
            (u"=== A ===\n dsfs:: dsf\n :: rdf\n :: sdfsdf\n :: dsfsf\n", ''),
            (u"=== A ===\n css:: \n :: rdf\n :: sdfsdf\n :: dsfsf\n", ''),
            (u"{{drawing:anywikitest.adraw}}", ''),
            (u'{{http://static.moinmo.in/logos/moinmoin.png|alt text|width=100 height=150 align=right}}', ''),
            (u'{{http://static.moinmo.in/logos/moinmoin.png|alt text}}', ''),
            (u"{{http://static.moinmo.in/logos/moinmoin.png}}\n", ''),
            (u'{{attachment:image.png|alt text|width=100 height=150 align=left}}', ''),
            (u'{{attachment:image.png|alt text}}', ''),
            (u'{{attachment:image.png}}', ''),
            (u'[[SomePage|{{attachment:samplegraphic.png}}|target=aaaa]]', ''),
            (u'[[SomePage#subsection|subsection of Some Page]]', ''),
            (u'[[../SisterPage|link text]]', ''),
            (u'[[http://static.moinmo.in/logos/moinmoin.png|{{attachment:samplegraphic.png}}|target=aaaa]]', ''),
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
        print self.serialize(out)
        out = self.conv_out(self.handle_input(self.serialize(out)), **args)
        assert self.handle_output(out) == output

