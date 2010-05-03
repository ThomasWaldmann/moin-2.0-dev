# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Show Wiki Configuration Help

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

        groups = []
        for groupname in multiconfig.options:
            groups.append((groupname, True, multiconfig.options))
        for groupname in multiconfig.options_no_group_name:
            groups.append((groupname, False, multiconfig.options_no_group_name))
        groups.sort()

        result = moin_page.div()

        for groupname, addgroup, optsdict in groups:
            heading, desc, opts = optsdict[groupname]
            result.append(
                moin_page.h(attrib={moin_page.outline_level: '1'}, children=[heading]))
            if desc:
                result.append(moin_page.p(children=[desc]))
            table = moin_page.table()
            result.append(table)

            header = moin_page.table_header()
            table.append(header)

            row = moin_page.table_row()
            header.append(row)
            for text in [_('Variable name'), _('Default'), _('Description'), ]:
                strong_text = moin_page.strong(children=[text])
                row.append(moin_page.table_cell(children=[strong_text]))

            body = moin_page.table_body()
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
                        default_txt = moin_page.span(
                            attrib={moin_page.title: default_txt},
                            children=['...'])
                    description = _(description or '', wiki=True, tree=True)
                row = moin_page.table_row()
                body.append(row)
                row.append(moin_page.table_cell(children=[name]))
                default = moin_page.code(children=[default_txt])
                row.append(moin_page.table_cell(children=[default]))
                row.append(moin_page.table_cell(children=[description]))
        return result

