# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Anchor Macro to put an anchor at the place where it is used.

    @copyright: 2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin.util import namespaces
from MoinMoin.macro2._base import MacroInlineBase

class Macro(MacroInlineBase):
    def macro(self, anchor=unicode):
        if not anchor:
            raise ValueError("Anchor: you need to give an anchor name.")

        tag_span = ET.QName('span', namespaces.moin_page)
        attr_id = ET.QName('id', namespaces.moin_page)
        return ET.Element(tag_span, attrib={attr_id: anchor})

