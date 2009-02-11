"""
MoinMoin - Macro and pseudo-macro handling

Base class for wiki parser with macro support.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin import wikiutil
from MoinMoin.util import iri
from MoinMoin.util.tree import moin_page, xinclude

class ConverterMacro(object):
    def __init__(self, request):
        self.request = request

    def _BR_repl(self, args, text, context):
        if context == 'block':
            return
        return moin_page.line_break()

    def _FootNote_repl(self, args, text, context):
        if args is None:
            # TODO: footnote placing
            return

        text = self.macro_text(args)

        elem_body = moin_page.note_body(children=text)
        attrib = {moin_page.note_class: 'footnote'}
        elem = moin_page.note(attrib=attrib, children=[elem_body])

        if context == 'block':
            return moin_page.p(children=[elem])
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
            link = unicode(iri.Iri(scheme='wiki.local', path=pagename))
            attrib[xinclude.href] = link

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
            ns = 'xmlns(page=%s) ' % moin_page.namespace

            attrib[xinclude.xpointer] = ns + ' '.join(xpointer)

        return xinclude.include(attrib=attrib)

    def _Include_repl(self, args, text, context):
        if context == 'inline':
            return text

        return wikiutil.invoke_extension_function(self.request, self._Include_macro, args)

    def _TableOfContents_repl(self, args, text, context):
        if context == 'inline':
            return text

        attrib = {}
        try:
            level = int(args)
        except ValueError:
            pass
        else:
            attrib[moin_page.outline_level] = str(level)

        return moin_page.table_of_content(attrib=attrib)

    def macro(self, name, args, text, context):
        func = getattr(self, '_%s_repl' % name, None)
        if func is not None:
            return func(args, text, context)

        # TODO: other namespace?
        attrib = {
            moin_page.alt: text,
            moin_page.macro_name: name,
            moin_page.macro_args: args,
            moin_page.macro_context: context,
        }
        return moin_page.macro(attrib)

    def macro_text(self, text):
        """
        Should be overriden to format text in some macros according to the
        input type.
        @return Sequence of (ET.Element, unicode)
        """
        return [text]

