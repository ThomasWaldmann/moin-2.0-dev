# -*- coding: iso-8859-1 -*-
"""
MoinMoin - Macro and pseudo-macro handling

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin.util import namespaces

class ConverterMacro(object):
    def _BR_repl(self, args, text, type):
        if type == 'block':
            return
        return ET.Element(ET.QName('line-break', namespaces.moin_page))

    def _FootNote_repl(self, args, text, type):
        tag = ET.QName('note', namespaces.moin_page)
        tag_body = ET.QName('note-body', namespaces.moin_page)
        tag_class = ET.QName('note-class', namespaces.moin_page)
        elem_body = ET.Element(tag_body, children=[args])
        elem = ET.Element(tag, attrib={tag_class: 'footnote'}, children=[elem_body])

        if type == 'block':
            tag = ET.QName('p', namespaces.moin_page)
            return ET.Element(tag, children=[elem])
        return elem

    def _Include_repl(self, args, text, type):
        if type == 'inline':
            return text
        # TODO
        return ''

    def _TableOfContents_repl(self, args, text, type):
        if type == 'inline':
            return text
        # TODO
        return ''

    def macro(self, name, args, text, type):
        func = getattr(self, '_%s_repl' % name, None)
        if func is not None:
            return func(args, text, type)

        # TODO: other namespace?
        tag = ET.QName('macro', namespaces.moin_page)
        tag_name = ET.QName('macro-name', namespaces.moin_page)
        tag_args = ET.QName('macro-args', namespaces.moin_page)
        tag_type = ET.QName('macro-type', namespaces.moin_page)
        tag_alt = ET.QName('alt', namespaces.moin_page)
        attrib = {tag_name: name, tag_args: args, tag_type: type, tag_alt: text}
        return ET.Element(tag, attrib)

