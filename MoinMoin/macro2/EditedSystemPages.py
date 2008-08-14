# -*- coding: iso-8859-1 -*-
"""
    EditedSystemPages - list system pages that has been edited in this wiki.

    @copyright: 2004 Nir Soffer <nirs@freeshell.org>,
                2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.Page import Page
from MoinMoin.util import namespaces
from MoinMoin.macro2._base import MacroPageLinkListBase

class Macro(MacroPageLinkListBase):
    def macro(self):
        if self.request.isSpiderAgent: # reduce bot cpu usage
            return ''

        # Get page list for current user (use this as admin), filter
        # pages that are both underlay and standard pages.
        def filterfn(name):
            page = Page(self.request, name)
            return (page.isStandardPage(includeDeleted=0) and
                    page.isUnderlayPage(includeDeleted=0))

        # Get page filtered page list. We don't need to filter by
        # exists, because our filter check this already.
        pagenames = self.request.rootpage.getPageList(filter=filterfn, exists=0)

        # Format as numbered list, sorted by page name
        pagenames.sort()

        return self.create_pagelink_list(pagenames, ordered=True)

