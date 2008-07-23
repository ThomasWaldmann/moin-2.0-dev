"""
MoinMoin - GoTo macro

Provides a goto box.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details
"""

from emeraldtree import ElementTree as ET

from MoinMoin.macro2._base import MacroBlockBase
from MoinMoin.util import namespaces

class Macro(MacroBlockBase):
    def macro(self):
        _ = self.request.getText

        tag_form = ET.QName('form', namespaces.html)
        tag_input = ET.QName('input', namespaces.html)
        tag_name = ET.QName('name', namespaces.html)
        tag_p = ET.QName('p', namespaces.html)
        tag_size = ET.QName('size', namespaces.html)
        tag_type = ET.QName('type', namespaces.html)
        tag_value = ET.QName('value', namespaces.html)

        attrib = {tag_type: 'text', tag_name: 'target', tag_size: '30'}
        input1 = ET.Element(tag_input, attrib=attrib)
        attrib = {tag_type: 'submit', tag_value: _("Go To Page")}
        input2 = ET.Element(tag_input, attrib=attrib)

        p = ET.Element(tag_p, children=[input1, ' ', input2])

        attrib = {tag_type: 'hidden', tag_name: 'action', tag_value: 'goto'}
        input = ET.Element(tag_input, attrib=attrib)
        form = ET.Element(tag_form, children=[input, p])

        return form

