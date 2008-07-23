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
        tag = ET.QName('note', namespaces.moin_page)
        tag_body = ET.QName('note-body', namespaces.moin_page)
        tag_class = ET.QName('note-class', namespaces.moin_page)
        elem_body = ET.Element(tag_body, children=[args])
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

        if titlesonly:
            raise NotImplementedError('macro: Include, argument: titlesonly')
        if editlink:
            raise NotImplementedError('macro: Include, argument: editlink')

        tag = ET.QName('include', namespaces.xinclude)
        tag_href = ET.QName('href', namespaces.xinclude)
        tag_xpointer = ET.QName('xpointer', namespaces.xinclude)

        attrib = {}
        xpointer = []

        def add_xpointer(function, *args):
            args = ','.join(args)
            args = args.replace('^', '^^').replace('(', '^(').replace(')', '^)')
            xpointer.append(function + '(' + args + ')')

        if pagename.startswith('^'):
            args = [pagename]
            if sort:
                args.append('sort=%s' % sort[1])
            if items:
                args.append('items=%d' % items)
            if skipitems:
                args.append('skipitems=%d' % skipitems)
            add_xpointer('moin-pages', *args)
        else:
            attrib[tag_href] = 'wiki.local:' + pagename

        if xpointer:
            attrib[tag_xpointer] = ''.join(xpointer)

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

