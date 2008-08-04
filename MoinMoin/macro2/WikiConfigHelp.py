# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Show Wiki Configuration Help

    @copyright: 2008 MoinMoin:JohannesBerg,
                2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details
"""

from emeraldtree import ElementTree as ET

from MoinMoin.config import multiconfig
from MoinMoin.macro2._base import MacroBlockBase
from MoinMoin.util import namespaces

class Macro(MacroBlockBase):
    def macro(self):
        request = self.request
        _ = request.getText

        groups = []
        for groupname in multiconfig.options:
            groups.append((groupname, True, multiconfig.options))
        for groupname in multiconfig.options_no_group_name:
            groups.append((groupname, False, multiconfig.options_no_group_name))
        groups.sort()

        tag_div = ET.QName('div', namespaces.moin_page)

        tag_heading = ET.QName('h', namespaces.moin_page)
        attr_level = ET.QName('outline-level', namespaces.moin_page)

        tag_span = ET.QName('span', namespaces.moin_page)
        attr_title = ET.QName('title', namespaces.moin_page)

        tag_p = ET.QName('p', namespaces.moin_page)
        tag_code = ET.QName('code', namespaces.moin_page)
        tag_strong = ET.QName('strong', namespaces.moin_page)

        tag_table = ET.QName('table', namespaces.moin_page)
        tag_table_header = ET.QName('table-header', namespaces.moin_page)
        tag_table_body = ET.QName('table-body', namespaces.moin_page)
        tag_table_row = ET.QName('table-row', namespaces.moin_page)
        tag_table_cell = ET.QName('table-cell', namespaces.moin_page)

        result = ET.Element(tag_div)

        for groupname, addgroup, optsdict in groups:
            heading, desc, opts = optsdict[groupname]
            result.append(
                ET.Element(tag_heading, attrib={attr_level: '1'}, children=[heading]))
            if desc:
                result.append(
                    ET.Element(tag_p, children=[desc]))
            table = ET.Element(tag_table)
            result.append(table)

            header = ET.Element(tag_table_header)
            table.append(header)

            row = ET.Element(tag_table_row)
            header.append(row)
            for text in [_('Variable name'), _('Default'), _('Description'), ]:
                strong_text = ET.Element(tag_strong, children=[text])
                row.append(ET.Element(tag_table_cell, children=[strong_text]))

            body = ET.Element(tag_table_body)
            table.append(body)

            opts = list(opts)
            opts.sort()
            for name, default, description in opts:
                if addgroup:
                    name = groupname + '_' + name
                if isinstance(default, multiconfig.DefaultExpression):
                    default_txt = default.text
                else:
                    default_txt = '%r' % (default, )
                    if len(default_txt) > 30:
                        default_txt = ET.Element(tag_span,
                                                 attrib={attr_title: default_txt},
                                                 children=['...'])
                    description = _(description or '', wiki=True, tree=True)
                row = ET.Element(tag_table_row)
                body.append(row)
                row.append(ET.Element(tag_table_cell, children=[name]))
                default = ET.Element(tag_code, children=[default_txt])
                row.append(ET.Element(tag_table_cell, children=[default]))
                row.append(ET.Element(tag_table_cell, children=[description]))
        return result

