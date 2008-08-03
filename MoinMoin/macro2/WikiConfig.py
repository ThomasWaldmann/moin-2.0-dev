# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Show Wiki Configuration

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

        if not request.user or not request.user.isSuperUser():
            return ''

        settings = {}
        for groupname in multiconfig.options:
            heading, desc, opts = multiconfig.options[groupname]
            for name, default, description in opts:
                name = groupname + '_' + name
                if isinstance(default, multiconfig.DefaultExpression):
                    default = default.value
                settings[name] = default
        for groupname in multiconfig.options_no_group_name:
            heading, desc, opts = multiconfig.options_no_group_name[groupname]
            for name, default, description in opts:
                if isinstance(default, multiconfig.DefaultExpression):
                    default = default.value
                settings[name] = default

        tag_div = ET.QName('div', namespaces.moin_page)

        tag_heading = ET.QName('h', namespaces.moin_page)
        attr_level = ET.QName('outline-level', namespaces.moin_page)

        tag_span = ET.QName('span', namespaces.moin_page)
        attr_title = ET.QName('title', namespaces.moin_page)

        tag_p = ET.QName('p', namespaces.moin_page)
        tag_code = ET.QName('code', namespaces.moin_page)
        tag_strong = ET.QName('strong', namespaces.moin_page)
        tag_emphasis = ET.QName('emphasis', namespaces.moin_page)

        tag_table = ET.QName('table', namespaces.moin_page)
        tag_table_header = ET.QName('table-header', namespaces.moin_page)
        tag_table_body = ET.QName('table-body', namespaces.moin_page)
        tag_table_row = ET.QName('table-row', namespaces.moin_page)
        tag_table_cell = ET.QName('table-cell', namespaces.moin_page)

        result = ET.Element(tag_div)

        result.append(
            ET.Element(tag_heading, attrib={attr_level: '1'}, children=[_("Wiki configuration")]))

        desc = _("This table shows all settings in this wiki that do not have default values. "
              "Settings that the configuration system doesn't know about are shown in ''italic'', "
              "those may be due to third-party extensions needing configuration or settings that "
              "were removed from Moin.") # XXX , wiki=True)  --> html shown in paragraph
        result.append(
            ET.Element(tag_p, children=[desc]))

        table = ET.Element(tag_table)
        result.append(table)

        header = ET.Element(tag_table_header)
        table.append(header)

        row = ET.Element(tag_table_row)
        header.append(row)
        for text in [_('Variable name'), _('Setting'), ]:
            strong_text = ET.Element(tag_strong, children=[text])
            row.append(ET.Element(tag_table_cell, children=[strong_text]))

        body = ET.Element(tag_table_body)
        table.append(body)

        def iter_vnames(cfg):
            dedup = {}
            for name in cfg.__dict__:
                dedup[name] = True
                yield name, cfg.__dict__[name]
            for cls in cfg.__class__.mro():
                if cls == multiconfig.ConfigFunctionality:
                    break
                for name in cls.__dict__:
                    if not name in dedup:
                        dedup[name] = True
                        yield name, cls.__dict__[name]

        found = []
        for vname, value in iter_vnames(request.cfg):
            if hasattr(multiconfig.ConfigFunctionality, vname):
                continue
            if vname in settings and settings[vname] == value:
                continue
            found.append((vname, value))
        found.sort()
        for vname, value in found:
            if not vname in settings:
                vname = ET.Element(tag_emphasis, children=[vname])
            vtxt = '%r' % (value, )
            row = ET.Element(tag_table_row)
            body.append(row)
            row.append(ET.Element(tag_table_cell, children=[vname]))
            vtxt_code = ET.Element(tag_code, children=[vtxt])
            row.append(ET.Element(tag_table_cell, children=[vtxt_code]))
        return result

