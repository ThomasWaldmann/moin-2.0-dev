"""
MoinMoin - Macro and pseudo-macro handling

Base class for wiki parser with macro support.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin import wikiutil
from MoinMoin.util import namespaces

class ConverterMacro(object):
    def __init__(self, request):
        self.request = request

    def _BR_repl(self, args, text, context):
        if context == 'block':
            return
        return ET.Element(ET.QName('line-break', namespaces.moin_page))

    def _FootNote_repl(self, args, text, context):
        if args is None:
            # TODO: footnote placing
            return

        text = self.macro_text(args)

        tag = ET.QName('note', namespaces.moin_page)
        tag_body = ET.QName('note-body', namespaces.moin_page)
        tag_class = ET.QName('note-class', namespaces.moin_page)
        elem_body = ET.Element(tag_body, children=text)
        elem = ET.Element(tag, attrib={tag_class: 'footnote'}, children=[elem_body])

        if context == 'block':
            tag = ET.QName('p', namespaces.moin_page)
            return ET.Element(tag, children=[elem])
        return elem

    def _Include_macro(self,
            pagename=wikiutil.required_arg(unicode),
            heading=unicode,
            level=int,
            sort=wikiutil.UnitArgument(None, str, ('ascending', 'descending')),
            items=int,
            skipitems=int,
            titlesonly=bool,
            editlink=bool):

        tag = ET.QName('include', namespaces.xinclude)
        tag_href = ET.QName('href', namespaces.xinclude)
        tag_xpointer = ET.QName('xpointer', namespaces.xinclude)

        attrib = {}
        xpointer = []
        xpointer_moin = []

        def add_moin_xpointer(function, args):
            args = unicode(args).replace('^', '^^').replace('(', '^(').replace(')', '^)')
            xpointer_moin.append(function + '(' + args + ')')

        moin_args = []

        if pagename.startswith('^'):
            add_moin_xpointer('pages', pagename)
            if sort:
                add_moin_xpointer('sort', sort[1])
            if items:
                add_moin_xpointer('items', items)
            if skipitems:
                add_moin_xpointer('skipitems', skipitems)
        else:
            attrib[tag_href] = 'wiki.local:' + pagename

        if heading == 'heading':
            heading = ''
        if heading is not None:
            add_moin_xpointer('heading', heading)
        if level:
            add_moin_xpointer('level', str(level))
        if titlesonly:
            add_moin_xpointer('titlesonly')
        if editlink:
            add_moin_xpointer('editlink')

        if xpointer_moin:
            xpointer.append('page:include(%s)' % ' '.join(xpointer_moin))

        if xpointer:
            # TODO: Namespace?
            ns = 'xmlns(page=%s) ' % namespaces.moin_page

            attrib[tag_xpointer] = ns + ' '.join(xpointer)

        return ET.Element(tag, attrib=attrib)

    def _Include_repl(self, args, text, context):
        if context == 'inline':
            return text

        return wikiutil.invoke_extension_function(self.request, self._Include_macro, args)

    def _TableOfContents_repl(self, args, text, context):
        if context == 'inline':
            return text

        tag = ET.QName('table-of-content', namespaces.moin_page)
        attrib = {}
        try:
            level = int(args)
        except ValueError:
            pass
        else:
            attrib[ET.QName('outline-level', namespaces.moin_page)] = str(level)

        return ET.Element(tag, attrib=attrib)

    def macro(self, name, args, text, context):
        func = getattr(self, '_%s_repl' % name, None)
        if func is not None:
            return func(args, text, context)

        # TODO: other namespace?
        tag = ET.QName('macro', namespaces.moin_page)
        tag_name = ET.QName('macro-name', namespaces.moin_page)
        tag_args = ET.QName('macro-args', namespaces.moin_page)
        tag_context = ET.QName('macro-context', namespaces.moin_page)
        tag_alt = ET.QName('alt', namespaces.moin_page)
        attrib = {tag_name: name, tag_args: args, tag_context: context, tag_alt: text}
        return ET.Element(tag, attrib)

    def macro_text(self, text):
        """
        Should be overriden to format text in some macros according to the
        input type.
        @return Sequence of (ET.Element, unicode)
        """
        return [text]

