"""
MoinMoin - Tests for MoinMoin.converter2.rst_in

@copyright: 2008 MoinMoin:BastianBlank
            2010 MoinMoin:DmitryAndreev
@license: GNU GPL, see COPYING for details.
"""

import py.test
import re

from MoinMoin.converter2.mediawiki_in_parser import *


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
            (u"''italic''",
                ''),
            (u"Text\nTest",
                ''),
            (u'Text\n\nTest',
                ''),
            (u"'''bold'''", ''),
            (u"'''''bold & italic'''''", ''),
            (u"<nowiki>no ''markup''</nowiki>", ''),
            (u'<u>underscore</u>', ''),
            (u'<del>Strikethrough</del>', ''),
            (u"<tt>Fixed width text</tt> or <code>source code</code>", ""),
            (u"test <sup>super</sup> or <sub>sub</sub>", ""),
            (u"text <blockquote> quote quote quote quote quote quote </blockquote> text", ""),
            (u"""=level 1=

== level 2 ==
===level 3===
====level 4====
=====level 5=====
======level 6======
""", ""),
            (u"""* one
* two
* three
** three point one
** three point two
""", ""),
            (u"""# one
# two<br />spanning more lines<br />doesn't break numbering
# three
## three point one
## three point two
""", ""),
            (""";item 1
: definition 1
;item 2
: definition 2-1
: definition 2-2
""", ""),
            (";aaa : bbb", ""),
            (""": Single indent
:: Double indent
::::: Multiple indent
""", ""),
            ("""# one
# two
#* two point one
#* two point two
# three
#; three item one
#: three def one
""", ""),
            (u"aaa<br />bbb", ""),
            (u"""{|
|Orange
|Apple
|-
|Bread
|Pie
|-
|Butter
|Ice cream
|}
""", ""),

        ]
        for i in data:
            yield (self.do, ) + i

    def serialize(self, elem, **options):
        from StringIO import StringIO
        file = StringIO()
        elem.write(file.write, namespaces=self.namespaces, **options)
        return self.output_re.sub(u'', file.getvalue())

    def do(self, input, output, args={}, skip=None):
        out = self.conv(input.split(u'\n'), **args)
        print self.serialize(out) # delete this
        assert self.serialize(out) == output

