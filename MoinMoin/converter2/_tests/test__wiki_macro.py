"""
MoinMoin - Tests for MoinMoin.converter2._wiki_macro

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree.ElementTree import ElementTree
import py.test

from MoinMoin.converter2._args import Arguments

from MoinMoin.converter2._wiki_macro import *

namespaces_string = 'xmlns="%s"' % moin_page.namespace
namespaces_string_xinclude = 'xmlns:xi="%s"' % xinclude.namespace
namespaces_xpstring = 'xmlns(page=%s)' % moin_page.namespace

namespaces_list = {
    moin_page.namespace: '',
    xinclude.namespace: 'xi',
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

    def test_macro(self):
        data = [
            ('Macro', None, 'text',
                '<page alt="text" content-type="x-moin/macro;name=Macro" %s />' % namespaces_string,
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro" %s />' % namespaces_string),
            ('Macro', Arguments([u'arg1']), 'text',
                '<page alt="text" content-type="x-moin/macro;name=Macro" %s><arguments><argument>arg1</argument></arguments></page>' % namespaces_string,
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro" %s><arguments><argument>arg1</argument></arguments></inline-part>' % namespaces_string),
        ]
        for name, args, text, output_block, output_inline in data:
            yield (self._do, name, args, text, True, output_block)
            yield (self._do, name, args, text, False, output_inline)

    def test_macro_arguments(self):
        data = [
            ('Macro', None, 'text',
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro" %s />' % namespaces_string),
            ('Macro', Arguments([u'arg1', u'arg2']), 'text',
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro" %s><arguments><argument>arg1</argument><argument>arg2</argument></arguments></inline-part>' % namespaces_string),
            ('Macro', Arguments([], {'key': 'value'}), 'text',
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro" %s><arguments><argument name="key">value</argument></arguments></inline-part>' % namespaces_string),
            ('Macro', Arguments([u'arg1', u'arg2'], {'key': 'value'}), 'text',
                '<inline-part alt="text" content-type="x-moin/macro;name=Macro" %s><arguments><argument>arg1</argument><argument>arg2</argument><argument name="key">value</argument></arguments></inline-part>' % namespaces_string),
        ]
        for name, args, text, output in data:
            yield (self._do, name, args, text, False, output)

    def test_pseudomacro(self):
        data = [
            ('BR', None, 'text',
                None,
                '<line-break %s />' % namespaces_string),
            ('FootNote', Arguments([u'note']), 'text',
                '<p %s><note note-class="footnote"><note-body>note</note-body></note></p>' % namespaces_string,
                '<note note-class="footnote" %s><note-body>note</note-body></note>' % namespaces_string),
            ('TableOfContents', None, 'text',
                '<table-of-content %s />' % namespaces_string,
                'text'),
            ('Include', Arguments([u'page']), 'text',
                '<xi:include xi:href="wiki.local:page" %s />' % namespaces_string_xinclude,
                'text'),
            ('Include', Arguments([u'^page']), 'text',
                '<xi:include xi:xpointer="%s page:include(pages(^^page))" %s />' % (namespaces_xpstring, namespaces_string_xinclude),
                'text'),
            ('Include', Arguments([u'^page'], {u'sort': u'ascending'}), 'text',
                '<xi:include xi:xpointer="%s page:include(pages(^^page) sort(ascending))" %s />' % (namespaces_xpstring, namespaces_string_xinclude),
                'text'),
            ('Include', Arguments([u'^page'], {u'sort': u'descending'}), 'text',
                '<xi:include xi:xpointer="%s page:include(pages(^^page) sort(descending))" %s />' % (namespaces_xpstring, namespaces_string_xinclude),
                'text'),
            ('Include', Arguments([u'^page'], {u'items': u'5'}), 'text',
                '<xi:include xi:xpointer="%s page:include(pages(^^page) items(5))" %s />' % (namespaces_xpstring, namespaces_string_xinclude),
                'text'),
            ('Include', Arguments([u'^page'], {u'skipitems': u'5'}), 'text',
                '<xi:include xi:xpointer="%s page:include(pages(^^page) skipitems(5))" %s />' % (namespaces_xpstring, namespaces_string_xinclude),
                'text'),
        ]
        for name, args, text, output_block, output_inline in data:
            yield (self._do, name, args, text, True, output_block)
            yield (self._do, name, args, text, False, output_inline)

    def _do(self, name, args, text, context_block, output):
        result = self.conv.macro(name, args, text, context_block)
        if output is not None or result is not None:
            if isinstance(result, basestring):
                assert result == output
            else:
                assert serialize(result) == output

