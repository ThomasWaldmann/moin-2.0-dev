"""
MoinMoin - Tests for MoinMoin.converter2._wiki_macro

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree.ElementTree import ElementTree
import py.test

from MoinMoin.converter2._wiki_macro import *

namespaces_string = 'xmlns="%s"' % namespaces.moin_page
namespaces_string_xinclude = 'xmlns:xi="%s"' % namespaces.xinclude
namespaces_xpstring = 'xmlns(page=%s)' % namespaces.moin_page

namespaces_list = {
    namespaces.moin_page: '',
    namespaces.xinclude: 'xi',
}

def serialize(elem, **options):
    from cStringIO import StringIO
    file = StringIO()
    tree = ElementTree(elem)
    tree.write(file, namespaces=namespaces_list, **options)
    return file.getvalue()

class TestConverter(object):
    def setup_class(self):
        self.conv = ConverterMacro(self.request)

    def test(self):
        pairs = [
            ('BR', None, 'text',
                None,
                '<line-break %s />' % namespaces_string),
            ('FootNote', 'note', 'text',
                '<p %s><note note-class="footnote"><note-body>note</note-body></note></p>' % namespaces_string,
                '<note note-class="footnote" %s><note-body>note</note-body></note>' % namespaces_string),
            ('TableOfContents', '', 'text',
                '<table-of-content %s />' % namespaces_string,
                'text'),
            ('Include', u'page', 'text',
                '<xi:include xi:href="wiki.local:page" %s />' % namespaces_string_xinclude,
                'text'),
            ('Include', u'^page', 'text',
                '<xi:include xi:xpointer="%s page:include(pages(^^page))" %s />' % (namespaces_xpstring, namespaces_string_xinclude),
                'text'),
            ('Include', u'^page, sort=ascending', 'text',
                '<xi:include xi:xpointer="%s page:include(pages(^^page) sort(ascending))" %s />' % (namespaces_xpstring, namespaces_string_xinclude),
                'text'),
            ('Include', u'^page, sort=descending', 'text',
                '<xi:include xi:xpointer="%s page:include(pages(^^page) sort(descending))" %s />' % (namespaces_xpstring, namespaces_string_xinclude),
                'text'),
            ('Include', u'^page, items=5', 'text',
                '<xi:include xi:xpointer="%s page:include(pages(^^page) items(5))" %s />' % (namespaces_xpstring, namespaces_string_xinclude),
                'text'),
            ('Include', u'^page, skipitems=5', 'text',
                '<xi:include xi:xpointer="%s page:include(pages(^^page) skipitems(5))" %s />' % (namespaces_xpstring, namespaces_string_xinclude),
                'text'),
        ]
        for name, args, text, output_block, output_inline in pairs:
            yield (self._do, name, args, text, 'block', output_block)
            yield (self._do, name, args, text, 'inline', output_inline)

    def _do(self, name, args, text, context, output):
        result = self.conv.macro(name, args, text, context)
        if output is not None or result is not None:
            if isinstance(result, basestring):
                assert result == output
            else:
                assert serialize(result) == output

