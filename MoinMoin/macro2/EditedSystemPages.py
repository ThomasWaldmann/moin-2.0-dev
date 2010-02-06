# -*- coding: iso-8859-1 -*-
"""
    EditedSystemPages - list system pages that has been edited in this wiki.

    @copyright: 2004 Nir Soffer <nirs@freeshell.org>,
                2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.Page import Page
from MoinMoin.macro2._base import MacroPageLinkListBase

class Macro(MacroPageLinkListBase):
    def macro(self):
        if self.request.isSpiderAgent: # reduce bot cpu usage
            return ''

        from MoinMoin.Page import Page
        from MoinMoin.items import IS_SYSPAGE

        # Get page list for current user (use this as admin), filter
        # pages that are syspages
        def filterfn(name):
            item = self.request.storage.get_item(name)
            try:
                return item.get_revision(-1)[IS_SYSPAGE]
            except KeyError:
                return False

        # Get page filtered page list. We don't need to filter by
        # exists, because our filter check this already.
        pagenames = list(self.request.rootpage.getPageList(filter=filterfn, exists=0))

        # Format as numbered list, sorted by page name
        pagenames.sort()

        return self.create_pagelink_list(pagenames, ordered=True)

