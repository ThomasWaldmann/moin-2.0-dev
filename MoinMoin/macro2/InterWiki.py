# -*- coding: iso-8859-1 -*-
"""
    Outputs the interwiki map.

    @copyright: 2007-2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details
"""

from MoinMoin.util.tree import moin_page, xlink
from MoinMoin import wikiutil
from MoinMoin.macro2._base import MacroBlockBase

class Macro(MacroBlockBase):
    def macro(self):
        interwiki_list = wikiutil.load_wikimap(self.request)
        iwlist = interwiki_list.items() # this is where we cached it
        iwlist.sort()

        iw_list = moin_page.list()
        for tag, url in iwlist:
            href = wikiutil.join_wiki(url, 'RecentChanges')
            link = moin_page.a(attrib={xlink.href: href}, children=[tag])
            label = moin_page.code(children=[link])
            iw_item_label = moin_page.list_item_label(children=[label])
            if '$PAGE' not in url:
                link = moin_page.a(attrib={xlink.href: url}, children=[url])
            else:
                link = url
            body = moin_page.code(children=[link])
            iw_item_body = moin_page.list_item_body(children=[body])
            iw_item = moin_page.list_item(children=[iw_item_label, iw_item_body])
            iw_list.append(iw_item)
        return iw_list

