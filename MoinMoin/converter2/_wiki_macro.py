# -*- coding: iso-8859-1 -*-
"""
MoinMoin - Macro and pseudo-macro handling

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree

from MoinMoin.util import namespaces

class ConverterMacro(object):
    def _BR_repl(self, args, text, type):
        return ElementTree.Element(ElementTree.QName('line-break', namespaces.moin_page))

    def macro(self, name, args, text, type):
        func = getattr(self, '_%s_repl' % name, None)
        if func is not None:
            return func(args, text, type)

        # TODO: other namespace?
        tag = ElementTree.QName('macro', namespaces.moin_page)
        tag_name = ElementTree.QName('macro-name', namespaces.moin_page)
        tag_args = ElementTree.QName('macro-args', namespaces.moin_page)
        tag_type = ElementTree.QName('macro-type', namespaces.moin_page)
        tag_alt = ElementTree.QName('alt', namespaces.moin_page)
        attrib = {tag_name: name, tag_args: args, tag_type: type, tag_alt: text}
        return ElementTree.Element(tag, attrib)
