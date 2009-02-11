# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - PageSize Macro displays an ordered list with page sizes and names

    @copyright: 2002 Juergen Hermann <jh@web.de>,
                2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.macro2._base import MacroNumberPageLinkListBase

class Macro(MacroNumberPageLinkListBase):
    def macro(self):
        if self.request.isSpiderAgent: # reduce bot cpu usage
            return ''

        # get list of pages and their objects
        pages = self.request.rootpage.getPageDict()

        # get sizes and sort them
        sizes_pagenames = [(page.size(), name) for name, page in pages.items()]
        sizes_pagenames.sort()
        sizes_pagenames.reverse()

        return self.create_number_pagelink_list(sizes_pagenames)

