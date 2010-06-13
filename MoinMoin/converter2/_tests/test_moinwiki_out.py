"""
MoinMoin - Tests for MoinMoin.converter2.moinwiki_out

@copyright: 2010 MoinMoin:DmitryAndreev
@license: GNU GPL, see COPYING for details.
"""

import py.test
import re

from MoinMoin.converter2.moinwiki_out import *


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
        assert self.handle_output(out) == output


class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter()

    def test_base(self):
        data = [
            (u'<page:p>Text</page:p>', 'Text\n'),
            (u"<page:tag><page:p>Text</page:p><page:p>Text</page:p></page:tag>", 'Text\n\nText\n'),
            (u"<page:separator />", '----\n'),
            (u"<page:strong>strong</page:strong>", "'''strong'''"),
            (u"<page:emphasis>emphasis</page:emphasis>", "''emphasis''"),
            (u"<page:blockcode>blockcode</page:blockcode>", "{{{\nblockcode\n}}}\n"),
            (u"<page:code>monospace</page:code>",'`monospace`'),
            (u'<page:span page:text-decoration="line-through">stroke</page:span>', '--(stroke)--'),
            (u'<page:span page:text-decoration="underline">underline</page:span>', '__underline__'),
            (u'<page:span page:font-size="120%">larger</page:span>', '~+larger+~'),
            (u'<page:span page:font-size="85%">smaller</page:span>', '~-smaller-~'),
            (u'<page:tag><page:span page:baseline-shift="super">super</page:span>script</page:tag>', '^super^script'),
            (u'<page:tag><page:span page:baseline-shift="sub">sub</page:span>script</page:tag>', ',,sub,,script'),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_link(self):
        data = [
            (u'<page:a xlink:href="wiki.local:SomePage#subsection">subsection of Some Page</page:a>', '[[SomePage#subsection|subsection of Some Page]]'),
            (u'<page:a xlink:target="_blank" xlink:href="wiki.local:SomePage">{{attachment:samplegraphic.png}}</page:a>', '[[SomePage|{{attachment:samplegraphic.png}}|target=_blank]]'),
            (u'<page:a xlink:href="wiki.local:SomePage?target=_blank">{{attachment:samplegraphic.png}}</page:a>', '[[SomePage|{{attachment:samplegraphic.png}}|&target=_blank]]'),
            (u'<page:a xlink:href="../SisterPage">link text</page:a>', '[[../SisterPage|link text]]'),
            (u'<page:a xlink:target="_blank" xlink:class="aaa" xlink:href="http://static.moinmo.in/logos/moinmoin.png">{{attachment:samplegraphic.png}}</page:a>', '[[http://static.moinmo.in/logos/moinmoin.png|{{attachment:samplegraphic.png}}|target=_blank,class=aaa]]'),
            (u'<page:a xlink:class="green dotted" xlink:accesskey="1" xlink:href="http://moinmo.in/">MoinMoin Wiki</page:a>', '[[http://moinmo.in/|MoinMoin Wiki|accesskey=1,class=green dotted]]'),
            (u'<page:a xlink:href="MoinMoin:MoinMoinWiki?action=diff&amp;rev1=1&amp;rev2=2">MoinMoin Wiki</page:a>', '[[MoinMoin:MoinMoinWiki|MoinMoin Wiki|&action=diff,&rev1=1,&rev2=2]]'),
            (u'<page:a xlink:href="attachment:HelpOnImages/pineapple.jpg?do=get">a pineapple</page:a>', '[[attachment:HelpOnImages/pineapple.jpg|a pineapple|&do=get]]'),
            (u'<page:a xlink:href="attachment:filename.txt">attachment:filename.txt</page:a>','[[attachment:filename.txt]]')
        ]
        for i in data:
            yield (self.do, ) + i

    def test_object(self):
        data = [
            (u"<page:object xlink:href=\"drawing:anywikitest.adraw\">{{drawing:anywikitest.adraw</page:object>", '{{drawing:anywikitest.adraw}}'),
            (u"<page:object xlink:href=\"http://static.moinmo.in/logos/moinmoin.png\" />", '{{http://static.moinmo.in/logos/moinmoin.png}}'),
            (u'<page:object page:alt="alt text" xlink:href="http://static.moinmo.in/logos/moinmoin.png">alt text</page:object>', '{{http://static.moinmo.in/logos/moinmoin.png|alt text}}'),
            (u'<page:object xlink:href="attachment:image.png" />', '{{attachment:image.png}}'),
            (u'<page:object page:alt="alt text" xlink:href="attachment:image.png">alt text</page:object>', '{{attachment:image.png|alt text}}'),
            (u'<page:object page:alt="alt text" xlink:href="attachment:image.png?width=100&amp;height=150&amp;align=left" />', '{{attachment:image.png|alt text|width=100 height=150 align=left}}'),

        ]
        for i in data:
            yield (self.do, ) + i

    def test_list(self):
        data = [
            (u"<page:list page:item-label-generate=\"unordered\"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>", " * A\n"),
            (u"<page:list page:item-label-generate=\"ordered\"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>", " 1. A\n"),
            (u"<page:list page:item-label-generate=\"ordered\" page:list-style-type=\"upper-roman\"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>", " I. A\n"),
            (u"<page:list page:item-label-generate=\"unordered\"><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>B</page:p><page:list page:item-label-generate=\"ordered\"><page:list-item><page:list-item-body><page:p>C</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>D</page:p><page:list page:item-label-generate=\"ordered\" page:list-style-type=\"upper-roman\"><page:list-item><page:list-item-body><page:p>E</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>F</page:p></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list>", " * A\n * B\n  1. C\n  1. D\n   I. E\n   I. F\n"),
            (u"<page:list><page:list-item><page:list-item-label>A</page:list-item-label><page:list-item-body><page:p>B</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>C</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>D</page:p></page:list-item-body></page:list-item></page:list>", " A::\n :: B\n :: C\n :: D\n"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_table(self):
        data = [
            (u"<page:table><page:table-body><page:table-row><page:table-cell>A</page:table-cell><page:table-cell>B</page:table-cell><page:table-cell page:number-rows-spanned=\"2\">D</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-columns-spanned=\"2\">C</page:table-cell></page:table-row></page:table-body></page:table>", "||A||B||<|2>D||\n||||C||\n"),
            (u"<page:table><page:table-body><page:table-row><page:table-cell><page:strong>A</page:strong></page:table-cell><page:table-cell><page:strong>B</page:strong></page:table-cell><page:table-cell><page:strong>C</page:strong></page:table-cell></page:table-row><page:table-row><page:table-cell><page:p>1</page:p></page:table-cell><page:table-cell>2</page:table-cell><page:table-cell>3</page:table-cell></page:table-row></page:table-body></page:table>", u"||'''A'''||'''B'''||'''C'''||\n||1||2||3||\n"),
            (u"<page:table><page:table-body><page:table-row><page:table-cell page:number-rows-spanned=\"2\">cell spanning 2 rows</page:table-cell><page:table-cell>cell in the 2nd column</page:table-cell></page:table-row><page:table-row><page:table-cell>cell in the 2nd column of the 2nd row</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-columns-spanned=\"2\">test</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-columns-spanned=\"2\">test</page:table-cell></page:table-row></page:table-body></page:table>", "||<|2>cell spanning 2 rows||cell in the 2nd column||\n||cell in the 2nd column of the 2nd row||\n||||test||\n||||test||\n"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_macros(self):
        data = [
            (u"<page:note page:note-class=\"footnote\"><page:note-body>test</page:note-body></page:note>", "<<FootNote(test)>>"),
            (u"<page:tag><page:table-of-content page:outline-level=\"2\" /></page:tag>", "<<TableOfContents(2)>>\n"),
            (u"<page:part page:alt=\"&lt;&lt;Anchor(anchorname)&gt;&gt;\" page:content-type=\"x-moin/macro;name=Anchor\"><page:arguments><page:argument>anchorname</page:argument></page:arguments></page:part>", "<<Anchor(anchorname)>>"),
            (u"<page:part page:alt=\"&lt;&lt;MonthCalendar(,,12)&gt;&gt;\" page:content-type=\"x-moin/macro;name=MonthCalendar\"><page:arguments><page:argument /><page:argument /><page:argument>12</page:argument></page:arguments></page:part>", "<<MonthCalendar(,,12)>>"),
        ]
        for i in data:
            yield (self.do, ) + i

    def test_parser(self):
        data = [
            (u"<page:page><page:body><page:page><page:body page:class=\"comment dotted\"><page:p>This is a wiki parser.</page:p><page:p>Its visibility gets toggled the same way.</page:p></page:body></page:page></page:body></page:page>","{{{#!wiki comment/dotted\nThis is a wiki parser.\n\nIts visibility gets toggled the same way.\n}}}\n"),
            (u"<page:page><page:body><page:page><page:body page:class=\"red solid\"><page:p>This is wiki markup in a <page:strong>div</page:strong> with <page:span page:text-decoration=\"underline\">css</page:span> <page:code>class=\"red solid\"</page:code>.</page:p></page:body></page:page></page:body></page:page>","{{{#!wiki red/solid\nThis is wiki markup in a \'\'\'div\'\'\' with __css__ `class=\"red solid\"`.\n}}}\n"),
            (u"<page:page><page:body><page:part page:content-type=\"x-moin/format;name=creole\"><page:arguments><page:argument page:name=\"style\">st: er</page:argument><page:argument page:name=\"class\">par: arg para: arga</page:argument></page:arguments><page:body>... **bold** ...</page:body></page:part></page:body></page:page>","{{{#!creole(style=\"st: er\" class=\"par: arg para: arga\")\n... **bold** ...\n}}}\n"),
        ]
        for i in data:
             yield (self.do, ) + i
    def test_p(self):
        data = [
            (u"<page:page><page:body><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:body></page:page>","A\n\nB\n\nC\n\nD\n"),
            (u"<page:page><page:body><page:table><page:table_row><page:table_cell><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:table_cell></page:table_row></page:table></page:body></page:page>","||A<<BR>>B<<BR>>C<<BR>>D||\n"),
            (u"<page:page><page:body><page:table><page:table_row><page:table_cell>Z</page:table_cell><page:table_cell><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:table_cell></page:table_row></page:table></page:body></page:page>", "||Z||A<<BR>>B<<BR>>C<<BR>>D||\n"),
            (u"<page:page><page:body><page:table><page:table_row><page:table_cell>Z</page:table_cell></page:table_row><page:table_row><page:table_cell><page:p>A</page:p><page:p>B</page:p>C<page:p>D</page:p></page:table_cell></page:table_row></page:table></page:body></page:page>","||Z||\n||A<<BR>>B<<BR>>C<<BR>>D||\n"),
            (u"<page:list page:item-label-generate=\"unordered\"><page:list-item><page:list-item-body><page:p>A</page:p><page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>A</page:p>A<page:p>A</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>A</page:p></page:list-item-body></page:list-item></page:list>", " * A<<BR>>A\n * A<<BR>>A<<BR>>A\n * A\n")
        ]
        for i in data:
            yield (self.do, ) + i

    def test_page(self):
        data = [
            (u"""<page:page><page:body><page:p>This page aims to introduce the most important elements of MoinMoin's syntax at a glance, showing first the markup verbatim and then how it is rendered by the wiki engine. Additionally, you'll find links to the relative help pages. Please note that some of the features depend on your configuration.</page:p><page:table-of-content /><page:h page:outline-level="1">Headings and table of contents</page:h><page:p><page:emphasis><page:strong>see:</page:strong> HelpOnHeadlines</page:emphasis></page:p><page:blockcode>Table of contents:
&lt;&lt;TableOfContents()&gt;&gt;

Table of contents (up to 2nd level headings only):
&lt;&lt;TableOfContents(2)&gt;&gt;

= heading 1st level =
== heading 2nd level ==
=== heading 3rd level ===
==== heading 4th level ====
===== heading 5th level =====
====== no heading 6th level ======</page:blockcode><page:page><page:body><page:p>Table of contents:</page:p><page:table-of-content /><page:p>Table of contents (up to 2nd level headings only):</page:p><page:table-of-content page:outline-level="2" /><page:h page:outline-level="1">heading 1st level</page:h><page:h page:outline-level="2">heading 2nd level</page:h><page:h page:outline-level="3">heading 3rd level</page:h><page:h page:outline-level="4">heading 4th level</page:h><page:h page:outline-level="5">heading 5th level</page:h><page:h page:outline-level="6">no heading 6th level</page:h></page:body></page:page><page:h page:outline-level="1">Text Formatting</page:h><page:p><page:emphasis><page:strong>see:</page:strong> HelpOnFormatting</page:emphasis></page:p><page:table><page:table-body><page:table-row><page:table-cell><page:strong>Markup</page:strong></page:table-cell><page:table-cell><page:strong>Result</page:strong></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>''italic''</page:code></page:table-cell><page:table-cell><page:emphasis>italic</page:emphasis></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>'''bold'''</page:code></page:table-cell><page:table-cell><page:strong>bold</page:strong></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>`monospace`</page:code></page:table-cell><page:table-cell><page:code>monospace</page:code></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>{{{code}}}</page:code></page:table-cell><page:table-cell><page:code>code</page:code></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>__underline__</page:code></page:table-cell><page:table-cell><page:span page:text-decoration="underline">underline</page:span></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>^super^script</page:code></page:table-cell><page:table-cell><page:span page:baseline-shift="super">super</page:span>script</page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>,,sub,,script</page:code></page:table-cell><page:table-cell><page:span page:baseline-shift="sub">sub</page:span>script</page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>~-smaller-~</page:code></page:table-cell><page:table-cell><page:span page:font-size="85%">smaller</page:span></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>~+larger+~</page:code></page:table-cell><page:table-cell><page:span page:font-size="120%">larger</page:span></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>--(stroke)--</page:code></page:table-cell><page:table-cell><page:span page:text-decoration="line-through">stroke</page:span></page:table-cell></page:table-row></page:table-body></page:table><page:h page:outline-level="1">Hyperlinks</page:h><page:p><page:emphasis><page:strong>see:</page:strong> HelpOnLinking</page:emphasis></page:p><page:h page:outline-level="2">Internal Links</page:h><page:table><page:table-body><page:table-row><page:table-cell><page:strong>Markup</page:strong></page:table-cell><page:table-cell><page:strong>Result</page:strong></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>FrontPage</page:code></page:table-cell><page:table-cell>FrontPage</page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>[[FrontPage]]</page:code></page:table-cell><page:table-cell><page:a xlink:href="wiki.local:FrontPage">FrontPage</page:a></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>HelpOnEditing/SubPages</page:code></page:table-cell><page:table-cell>HelpOnEditing/SubPages</page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>/SubPage</page:code></page:table-cell><page:table-cell>/SubPage</page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>../SiblingPage</page:code></page:table-cell><page:table-cell>../SiblingPage</page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>[[FrontPage|named link]]</page:code></page:table-cell><page:table-cell><page:a xlink:href="wiki.local:FrontPage">named link</page:a></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>[[#anchorname]]</page:code></page:table-cell><page:table-cell><page:a xlink:href="wiki.local:#anchorname">#anchorname</page:a></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>[[#anchorname|description]]</page:code></page:table-cell><page:table-cell><page:a xlink:href="wiki.local:#anchorname">description</page:a></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>[[PageName#anchorname]]</page:code></page:table-cell><page:table-cell><page:a xlink:href="wiki.local:PageName#anchorname">PageName#anchorname</page:a></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>[[PageName#anchorname|description]]</page:code></page:table-cell><page:table-cell><page:a xlink:href="wiki.local:PageName#anchorname">description</page:a></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>[[attachment:filename.txt]]</page:code></page:table-cell><page:table-cell><page:a xlink:href="wiki.local:attachment:filename.txt">attachment:filename.txt</page:a></page:table-cell></page:table-row></page:table-body></page:table><page:h page:outline-level="2">External Links</page:h><page:table><page:table-body><page:table-row><page:table-cell><page:strong>Markup</page:strong></page:table-cell><page:table-cell><page:strong>Result</page:strong></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>http://moinmo.in/</page:code></page:table-cell><page:table-cell>http://moinmo.in/</page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>[[http://moinmo.in/]]</page:code></page:table-cell><page:table-cell><page:a xlink:href="http://moinmo.in/">http://moinmo.in/</page:a></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>[[http://moinmo.in/|MoinMoin Wiki]]</page:code></page:table-cell><page:table-cell><page:a xlink:href="http://moinmo.in/">MoinMoin Wiki</page:a></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>[[http://static.moinmo.in/logos/moinmoin.png]]</page:code></page:table-cell><page:table-cell><page:a xlink:href="http://static.moinmo.in/logos/moinmoin.png">http://static.moinmo.in/logos/moinmoin.png</page:a></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>{{http://static.moinmo.in/logos/moinmoin.png}}</page:code></page:table-cell><page:table-cell><page:object xlink:href="http://static.moinmo.in/logos/moinmoin.png">http://static.moinmo.in/logos/moinmoin.png</page:object></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>[[http://static.moinmo.in/logos/moinmoin.png|moinmoin.png]]</page:code></page:table-cell><page:table-cell><page:a xlink:href="http://static.moinmo.in/logos/moinmoin.png">moinmoin.png</page:a></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>MeatBall:InterWiki</page:code></page:table-cell><page:table-cell>MeatBall:InterWiki</page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>[MeatBall:InterWiki|InterWiki page on MeatBall]]</page:code></page:table-cell><page:table-cell><page:a xlink:href="wiki.local:MeatBall:InterWiki">InterWiki page on MeatBall</page:a></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>[[file://///server/share/filename%20with%20spaces.txt|link to filename.txt]]</page:code></page:table-cell><page:table-cell><page:a xlink:href="file://///servername/share/full/path/to/file/filename%20with%20spaces.txt">link to file filename with spaces.txt</page:a></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>user@example.com</page:code></page:table-cell><page:table-cell>user@example.com</page:table-cell></page:table-row></page:table-body></page:table><page:h page:outline-level="2">Avoid or Limit Automatic Linking</page:h><page:table><page:table-body><page:table-row><page:table-cell><page:strong>Markup</page:strong></page:table-cell><page:table-cell><page:strong>Result</page:strong></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>Wiki''''''Name</page:code></page:table-cell><page:table-cell>WikiName</page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>Wiki</page:code><page:code>Name</page:code></page:table-cell><page:table-cell>WikiName</page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>!WikiName</page:code></page:table-cell><page:table-cell>!WikiName</page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>WikiName''''''s</page:code></page:table-cell><page:table-cell>WikiNames</page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>WikiName``s</page:code></page:table-cell><page:table-cell>WikiNames</page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>http://www.example.com</page:code></page:table-cell><page:table-cell><page:code>http://www.example.com</page:code></page:table-cell></page:table-row><page:table-row><page:table-cell><page:code>[[http://www.example.com/]]notlinked</page:code></page:table-cell><page:table-cell><page:a xlink:href="http://www.example.com/">http://www.example.com/</page:a>notlinked</page:table-cell></page:table-row></page:table-body></page:table><page:h page:outline-level="1">Drawings</page:h><page:p><page:emphasis><page:strong>see:</page:strong> HelpOnDrawings</page:emphasis></page:p><page:h page:outline-level="2">TWikiDraw</page:h><page:list page:item-label-generate="unordered" page:list-style-type="none"><page:list-item><page:list-item-body><page:p><page:object xlink:href="wiki.local:drawing:myexample?do=get">drawing:myexample</page:object></page:p></page:list-item-body></page:list-item></page:list><page:h page:outline-level="2">AnyWikiDraw</page:h><page:list page:item-label-generate="unordered" page:list-style-type="none"><page:list-item><page:list-item-body><page:p><page:object xlink:href="wiki.local:drawing:myexample.adraw?do=get">drawing:myexample.adraw</page:object></page:p></page:list-item-body></page:list-item></page:list><page:h page:outline-level="1">Blockquotes and Indentations</page:h><page:blockcode> indented text
  text indented to the 2nd level</page:blockcode><page:list page:item-label-generate="unordered" page:list-style-type="none"><page:list-item><page:list-item-body><page:p>indented text</page:p><page:list page:item-label-generate="unordered" page:list-style-type="none"><page:list-item><page:list-item-body><page:p>text indented to the 2nd level</page:p></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list><page:h page:outline-level="1">Lists</page:h><page:p><page:emphasis><page:strong>see:</page:strong> HelpOnLists</page:emphasis></page:p><page:h page:outline-level="2">Unordered Lists</page:h><page:blockcode> * item 1

 * item 2 (preceding white space)
  * item 2.1
   * item 2.1.1
 * item 3
  . item 3.1 (bulletless)
 . item 4 (bulletless)
  * item 4.1
   . item 4.1.1 (bulletless)</page:blockcode><page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body><page:p>item 1</page:p></page:list-item-body></page:list-item></page:list><page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body><page:p>item 2 (preceding white space)</page:p><page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body><page:p>item 2.1</page:p><page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body><page:p>item 2.1.1</page:p></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>item 3</page:p><page:list page:item-label-generate="unordered" page:list-style-type="none"><page:list-item><page:list-item-body><page:p>item 3.1 (bulletless)</page:p></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list><page:list page:item-label-generate="unordered" page:list-style-type="none"><page:list-item><page:list-item-body><page:p>item 4 (bulletless)</page:p><page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body><page:p>item 4.1</page:p><page:list page:item-label-generate="unordered" page:list-style-type="none"><page:list-item><page:list-item-body><page:p>item 4.1.1 (bulletless)</page:p></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item></page:list><page:h page:outline-level="2">Ordered Lists</page:h><page:h page:outline-level="3">with Numbers</page:h><page:blockcode> 1. item 1
   1. item 1.1
   1. item 1.2
 1. item 2</page:blockcode><page:list page:item-label-generate="ordered"><page:list-item><page:list-item-body><page:p>item 1</page:p><page:list page:item-label-generate="ordered"><page:list-item><page:list-item-body><page:p>item 1.1</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>item 1.2</page:p></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>item 2</page:p></page:list-item-body></page:list-item></page:list><page:h page:outline-level="3">with Roman Numbers</page:h><page:blockcode> I. item 1
   i. item 1.1
   i. item 1.2
 I. item 2</page:blockcode><page:list page:item-label-generate="ordered" page:list-style-type="upper-roman"><page:list-item><page:list-item-body><page:p>item 1</page:p><page:list page:item-label-generate="ordered" page:list-style-type="upper-roman"><page:list-item><page:list-item-body><page:p>item 1.1</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>item 1.2</page:p></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>item 2</page:p></page:list-item-body></page:list-item></page:list><page:h page:outline-level="3">with Letters</page:h><page:blockcode> A. item A
   a. item A. a)
   a. item A. b)
 A. item B</page:blockcode><page:list page:item-label-generate="ordered" page:list-style-type="upper-alpha"><page:list-item><page:list-item-body><page:p>item A</page:p><page:list page:item-label-generate="ordered" page:list-style-type="upper-alpha"><page:list-item><page:list-item-body><page:p>item A. a)</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>item A. b)</page:p></page:list-item-body></page:list-item></page:list></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>item B</page:p></page:list-item-body></page:list-item></page:list><page:h page:outline-level="2">Definition Lists</page:h><page:blockcode> term:: definition
 object::
 :: description 1
 :: description 2</page:blockcode><page:list><page:list-item><page:list-item-label>term</page:list-item-label><page:list-item-body><page:p>definition
object::</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>description 1</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p>description 2</page:p></page:list-item-body></page:list-item></page:list><page:h page:outline-level="1">Horizontal Rules</page:h><page:p><page:emphasis><page:strong>see:</page:strong> HelpOnRules</page:emphasis></page:p><page:blockcode>----
-----
------
-------
--------
---------
----------</page:blockcode><page:separator /><page:separator /><page:separator /><page:separator /><page:separator /><page:separator /><page:separator /><page:h page:outline-level="1">Tables</page:h><page:p><page:emphasis><page:strong>see:</page:strong> HelpOnTables</page:emphasis></page:p><page:h page:outline-level="2">Tables</page:h><page:blockcode>||'''A'''||'''B'''||'''C'''||
||1      ||2      ||3      ||</page:blockcode><page:table><page:table-body><page:table-row><page:table-cell><page:strong>A</page:strong></page:table-cell><page:table-cell><page:strong>B</page:strong></page:table-cell><page:table-cell><page:strong>C</page:strong></page:table-cell></page:table-row><page:table-row><page:table-cell>1</page:table-cell><page:table-cell>2</page:table-cell><page:table-cell>3</page:table-cell></page:table-row></page:table-body></page:table><page:h page:outline-level="2">Cell Width</page:h><page:blockcode>||minimal width ||&lt;99%&gt;maximal width ||</page:blockcode><page:table><page:table-body><page:table-row><page:table-cell>minimal width</page:table-cell><page:table-cell>maximal width</page:table-cell></page:table-row></page:table-body></page:table><page:h page:outline-level="2">Spanning Rows and Columns</page:h><page:blockcode>||&lt;|2&gt; cell spanning 2 rows ||cell in the 2nd column ||
||cell in the 2nd column of the 2nd row ||
||&lt;-2&gt; cell spanning 2 columns ||
||||use empty cells as a shorthand ||</page:blockcode><page:table><page:table-body><page:table-row><page:table-cell page:number-rows-spanned="2">cell spanning 2 rows</page:table-cell><page:table-cell>cell in the 2nd column</page:table-cell></page:table-row><page:table-row><page:table-cell>cell in the 2nd column of the 2nd row</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-columns-spanned="2">cell spanning 2 columns</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-columns-spanned="2">use empty cells as a shorthand</page:table-cell></page:table-row></page:table-body></page:table><page:h page:outline-level="2">Alignment of Cell Contents</page:h><page:blockcode>||&lt;^|3&gt; top (combined) ||&lt;:99%&gt; center (combined) ||&lt;v|3&gt; bottom (combined) ||
||&lt;)&gt; right ||
||&lt;(&gt; left ||</page:blockcode><page:table><page:table-body><page:table-row><page:table-cell page:number-rows-spanned="3">top (combined)</page:table-cell><page:table-cell>center (combined)</page:table-cell><page:table-cell page:number-rows-spanned="3">bottom (combined)</page:table-cell></page:table-row><page:table-row><page:table-cell>right</page:table-cell></page:table-row><page:table-row><page:table-cell>left</page:table-cell></page:table-row></page:table-body></page:table><page:h page:outline-level="2">Coloured Table Cells</page:h><page:blockcode>||&lt;#0000FF&gt; blue ||&lt;#00FF00&gt; green    ||&lt;#FF0000&gt; red    ||
||&lt;#00FFFF&gt; cyan ||&lt;#FF00FF&gt; magenta  ||&lt;#FFFF00&gt; yellow ||</page:blockcode><page:table><page:table-body><page:table-row><page:table-cell>blue</page:table-cell><page:table-cell>green</page:table-cell><page:table-cell>red</page:table-cell></page:table-row><page:table-row><page:table-cell>cyan</page:table-cell><page:table-cell>magenta</page:table-cell><page:table-cell>yellow</page:table-cell></page:table-row></page:table-body></page:table><page:h page:outline-level="2">HTML-like Options for Tables</page:h><page:blockcode>||A ||&lt;rowspan="2"&gt; like &lt;|2&gt; ||
||&lt;bgcolor="#00FF00"&gt; like &lt;#00FF00&gt; ||
||&lt;colspan="2"&gt; like &lt;-2&gt;||</page:blockcode><page:table><page:table-body><page:table-row><page:table-cell>A</page:table-cell><page:table-cell page:number-rows-spanned="2">like &lt;|2&gt;</page:table-cell></page:table-row><page:table-row><page:table-cell>like &lt;#00FF00&gt;</page:table-cell></page:table-row><page:table-row><page:table-cell page:number-columns-spanned="2">like &lt;-2&gt;</page:table-cell></page:table-row></page:table-body></page:table><page:h page:outline-level="1">Macros and Variables</page:h><page:h page:outline-level="2">Macros</page:h><page:p><page:emphasis><page:strong>see:</page:strong> HelpOnMacros</page:emphasis></page:p><page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body><page:p><page:inline-part page:alt="&lt;&lt;Anchor(anchorname)&gt;&gt;" page:content-type="x-moin/macro;name=Anchor"><page:arguments><page:argument>anchorname</page:argument></page:arguments></page:inline-part><page:code>&lt;&lt;Anchor(anchorname)&gt;&gt;</page:code> inserts a link anchor <page:code>anchorname</page:code></page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p><page:code>&lt;&lt;BR&gt;&gt;</page:code> inserts a hard line break</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p><page:code>&lt;&lt;FootNote(Note)&gt;&gt;</page:code> inserts a footnote saying <page:code>Note</page:code></page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p><page:code>&lt;&lt;Include(HelpOnMacros/Include)&gt;&gt;</page:code> inserts the contents of the page <page:code>HelpOnMacros/Include</page:code> inline</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p><page:code>&lt;&lt;MailTo(user AT example DOT com)&gt;&gt;</page:code> obfuscates the email address <page:code>user@example.com</page:code> to users not logged in</page:p></page:list-item-body></page:list-item></page:list><page:h page:outline-level="2">Variables</page:h><page:p><page:emphasis><page:strong>see:</page:strong> HelpOnVariables</page:emphasis></page:p><page:list page:item-label-generate="unordered"><page:list-item><page:list-item-body><page:p><page:code>@</page:code><page:code>SIG</page:code><page:code>@</page:code> inserts your login name and timestamp of modification</page:p></page:list-item-body></page:list-item><page:list-item><page:list-item-body><page:p><page:code>@</page:code><page:code>TIME</page:code><page:code>@</page:code> inserts date and time of modification</page:p></page:list-item-body></page:list-item></page:list><page:h page:outline-level="1">Smileys and Icons</page:h><page:p><page:emphasis><page:strong>see:</page:strong> HelpOnSmileys</page:emphasis></page:p><page:part page:alt="&lt;&lt;ShowSmileys&gt;&gt;" page:content-type="x-moin/macro;name=ShowSmileys" /><page:h page:outline-level="1">Parsers</page:h><page:p><page:emphasis><page:strong>see:</page:strong> HelpOnParsers</page:emphasis></page:p><page:h page:outline-level="2">Verbatim Display</page:h><page:blockcode>{{{
def hello():
    print "Hello World!"
}}}</page:blockcode><page:blockcode>def hello():
    print "Hello World!"</page:blockcode><page:h page:outline-level="2">Syntax Highlighting</page:h><page:blockcode>{{{#!highlight python
def hello():
    print "Hello World!"
}}}</page:blockcode><page:part page:content-type="x-moin/format;name=highlight"><page:arguments><page:argument page:name="_old">python</page:argument></page:arguments><page:body>def hello():    print "Hello World!"</page:body></page:part><page:h page:outline-level="2">Using the wiki parser with css classes</page:h><page:blockcode>{{{#!wiki red/solid
This is wiki markup in a '''div''' with __css__ `class="red solid"`.
}}}</page:blockcode><page:page><page:body page:class="red solid"><page:p>This is wiki markup in a <page:strong>div</page:strong> with <page:span page:text-decoration="underline">css</page:span> <page:code>class="red solid"</page:code>.</page:p></page:body></page:page><page:h page:outline-level="1">Admonitions</page:h><page:p><page:emphasis><page:strong>see:</page:strong> HelpOnAdmonitions</page:emphasis></page:p><page:blockcode>{{{#!wiki caution
'''Don't overuse admonitions'''

Admonitions should be used with care. A page riddled with admonitions will look restless and will be harder to follow than a page where admonitions are used sparingly.
}}}</page:blockcode><page:page><page:body page:class="caution"><page:p><page:strong>Don't overuse admonitions</page:strong></page:p><page:p>Admonitions should be used with care. A page riddled with admonitions will look restless and will be harder to follow than a page where admonitions are used sparingly.</page:p></page:body></page:page><page:h page:outline-level="1">Comments</page:h><page:p><page:emphasis><page:strong>see:</page:strong> HelpOnComments</page:emphasis></page:p><page:blockcode>Click on "Comments" in edit bar to toggle the /* comments */ visibility.</page:blockcode><page:p>Click on "Comments" in edit bar to toggle the comments visibility.</page:p><page:blockcode>{{{#!wiki comment/dotted
This is a wiki parser section with class "comment dotted" (see HelpOnParsers).

Its visibility gets toggled the same way.
}}}</page:blockcode><page:page><page:body page:class="comment dotted"><page:p>This is a wiki parser section with class "comment dotted" (see HelpOnParsers).</page:p><page:p>Its visibility gets toggled the same way.</page:p></page:body></page:page></page:body></page:page>""", """ """),
        ]
        for i in data:
            yield (self.do, ) + i

