# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Hits Macro

    This macro is used to show the cumulative hits of the wikipage where the Macro is called from.
    Optionally you could count how much this page or all pages were changed or viewed.

    <<Hits([all=(0,1)],[event_type=(VIEWPAGE,SAVEPAGE)>>

        all: if set to 1/True/yes then a cumulative hit count for all wiki pages is returned.
             Default is 0/False/no.
        filter: if set to SAVEPAGE then the saved pages are counted. Default is VIEWPAGE.

   @copyright: 2004-2008 MoinMoin:ReimarBauer,
               2005 BenjaminVrolijk,
               2008 MoinMoin:ThomasWaldmann
   @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.stats import hitcounts
from MoinMoin.macro2._base import MacroInlineBase

class Macro(MacroInlineBase):
    def macro(self, all=False, event_type=(u'VIEWPAGE', u'SAVEPAGE')):
        thispage = self.page_name
        filterpage = not all and thispage or None
        cache_days, cache_views, cache_edits = hitcounts.get_data(thispage, self.request, filterpage=filterpage)

        if event_type == u'VIEWPAGE':
            hits = sum(cache_views)
        else:
            hits = sum(cache_edits)
        return u'%d' % hits

