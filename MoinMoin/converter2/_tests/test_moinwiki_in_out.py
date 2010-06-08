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
            (u'Text', 'Text\n'),
            (u"Text\n\nText\n", 'Text\n\nText\n'),
            (u"----\n-----\n------\n", '----\n-----\n------\n'),
            (u"'''strong'''\n", "'''strong'''\n"),
            (u"''emphasis''\n", "''emphasis''\n"),
            (u"{{{\nblockcode\n}}}\n", "{{{\nblockcode\n}}}\n"),
            (u"`monospace`\n",'`monospace`\n'),
            (u"--(stroke)--\n", '--(stroke)--\n'),
            (u"__underline__\n", '__underline__\n'),
            (u"~+larger+~\n", '~+larger+~\n'),
            (u"~-smaller-~\n", '~-smaller-~\n'),
            (u"^super^script\n", '^super^script\n'),
            (u",,sub,,script\n", ',,sub,,script\n'),
            (u"## comment\n", "## comment\n"),
            (u"#ANY any", "#ANY any\n"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_macros(self):
        data = [
            (u"<<Anchor(anchorname)>>", '<<Anchor(anchorname)>>'),
            (u"<<MonthCalendar(,,12)>>", '<<MonthCalendar(,,12)>>'),
            (u"<<FootNote(test)>>", "<<FootNote(test)>>\n"),
            (u"<<TableOfContents(2)>>", "<<TableOfContents(2)>>"),
            (u"<<TeudView()>>", "<<TeudView()>>"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_parsers(self):
        data = [
            (u"{{{#!wiki comment/dotted\nThis is a wiki parser.\n\nIts visibility gets toggled the same way.\n}}}", u"{{{#!wiki comment/dotted\nThis is a wiki parser.\n\nIts visibility gets toggled the same way.\n}}}"),
            (u"{{{#!wiki red/solid\nThis is wiki markup in a '''div''' with __css__ `class=\"red solid\"`.\n}}}", "{{{#!wiki red/solid\nThis is wiki markup in a '''div''' with __css__ `class=\"red solid\"`.\n}}}\n"),
            (u"{{{#!creole\n... **bold** ...\n}}}", u"{{{#!creole\n\n}}}"),
            (u"#format creole\n... **bold** ...\n", "#format creole\n... **bold** ...\n"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_variables(self):
        data = [
            (u"VAR:: text", u"VAR:: text"),
            (u"@TIME@", u""),
            (u"@DATE@", u""),
            (u"@PAGE@", u""),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_link(self):
        data = [
            (u'[[SomePage#subsection|subsection of Some Page]]', '[[SomePage#subsection|subsection of Some Page]]\n'),
            (u'[[SomePage|{{attachment:samplegraphic.png}}|target=_blank]]', '[[SomePage|{{attachment:samplegraphic.png}}|target=_blank]]\n'),
            (u'[[SomePage|{{attachment:samplegraphic.png}}|&target=_blank]]', '[[SomePage|{{attachment:samplegraphic.png}}|&target=_blank]]\n'),
            (u'[[../SisterPage|link text]]', '[[../SisterPage|link text]]\n'),
            (u'[[http://static.moinmo.in/logos/moinmoin.png|{{attachment:samplegraphic.png}}|target=_blank,class=aaa]]', '[[http://static.moinmo.in/logos/moinmoin.png|{{attachment:samplegraphic.png}}|target=_blank]]\n'),
            (u'[[http://moinmo.in/|MoinMoin Wiki|class=green dotted,accesskey=1]]', '[[http://moinmo.in/|MoinMoin Wiki|class=green dotted,accesskey=1]]\n'),
            (u'[[http://moinmo.in/|MoinMoin Wiki|class=green]]', '[[http://moinmo.in/|MoinMoin Wiki|class=green]]\n'),
            (u'[[MoinMoin:MoinMoinWiki|MoinMoin Wiki|&action=diff,&rev1=1,&rev2=2]]', '[[MoinMoin:MoinMoinWiki|MoinMoin Wiki|&action=diff,&rev1=1,&rev2=2]]\n'),
            (u'[[attachment:HelpOnImages/pineapple.jpg|a pineapple|&do=get]]', '[[attachment:HelpOnImages/pineapple.jpg|a pineapple|&do=get]]\n'),
            (u'[[attachment:filename.txt]]','[[attachment:filename.txt]]\n')
        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            (u" * A\n * B\n  1. C\n  1. D\n   I. E\n   I. F\n", ' * A\n * B\n  1. C\n  1. D\n   I. E\n   I. F\n'),
            (u" A:: B\n :: C\n :: D\n", ' A::\n :: B\n :: C\n :: D\n'),
            (u" A::\n :: B\n :: C\n :: D\n", ' A::\n :: B\n :: C\n :: D\n'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_table(self):
        data = [
            (u"||A||B||<|2>D||\n||||C||\n", '||A||B||<|2>D||\n||||C||\n'),
            (u"||'''A'''||'''B'''||'''C'''||\n||1      ||2      ||3     ||\n", u"||'''A'''||'''B'''||'''C'''||\n||1||2||3||\n"),
            (u"||<|2> cell spanning 2 rows ||cell in the 2nd column ||\n||cell in the 2nd column of the 2nd row ||\n||<-2>test||\n||||test||",
             u"||<|2>cell spanning 2 rows||cell in the 2nd column||\n||cell in the 2nd column of the 2nd row||\n||||test||\n||||test||\n"),

        ]
        for i in data:
            yield (self.do, ) + i

    def test_object(self):
        data = [
            (u"{{drawing:anywikitest.adraw}}", '{{drawing:anywikitest.adraw}}\n'),
            (u"{{http://static.moinmo.in/logos/moinmoin.png}}\n", '{{http://static.moinmo.in/logos/moinmoin.png}}\n'),
            (u'{{http://static.moinmo.in/logos/moinmoin.png|alt text}}', '{{http://static.moinmo.in/logos/moinmoin.png|alt text}}\n'),
            (u'{{http://static.moinmo.in/logos/moinmoin.png|alt text|width=100 height=150 align=right}}', '{{http://static.moinmo.in/logos/moinmoin.png|alt text|width=100 height=150 align=right}}\n'),
            (u'{{attachment:image.png}}', '{{attachment:image.png}}\n'),
            (u'{{attachment:image.png|alt text}}', '{{attachment:image.png|alt text}}\n'),
            (u'{{attachment:image.png|alt text|width=100 align=left height=150}}', '{{attachment:image.png|alt text|width=100 align=left height=150}}\n'),

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

