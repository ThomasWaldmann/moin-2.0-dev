# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Show Wiki Configuration

    @copyright: 2008 MoinMoin:JohannesBerg,
                2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details
"""

from MoinMoin.config import multiconfig
from MoinMoin.macro2._base import MacroBlockBase
from MoinMoin.util.tree import moin_page

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

        result = moin_page.div()

        result.append(
            moin_page.h(attrib={moin_page.outline_level: '1'}, children=[_("Wiki configuration")]))

        desc = _("This table shows all settings in this wiki that do not have default values. "
              "Settings that the configuration system doesn't know about are shown in ''italic'', "
              "those may be due to third-party extensions needing configuration or settings that "
              "were removed from Moin.", wiki=True, tree=True)
        result.append(moin_page.p(children=[desc]))

        table = moin_page.table()
        result.append(table)

        header = moin_page.table_header()
        table.append(header)

        row = moin_page.table_row()
        header.append(row)
        for text in [_('Variable name'), _('Setting'), ]:
            strong_text = moin_page.strong(children=[text])
            row.append(moin_page.table_cell(children=[strong_text]))

        body = moin_page.table_body()
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
                vname = moin_page.emphasis(children=[vname])
            vtxt = '%r' % (value, )
            row = moin_page.table_row()
            body.append(row)
            row.append(moin_page.table_cell(children=[vname]))
            vtxt_code = moin_page.code(children=[vtxt])
            row.append(moin_page.table_cell(children=[vtxt_code]))
        return result

