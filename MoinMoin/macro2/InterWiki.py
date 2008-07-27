# -*- coding: iso-8859-1 -*-
"""
    Outputs the interwiki map.

    @copyright: 2007-2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details
"""

from emeraldtree import ElementTree as ET

from MoinMoin.util import namespaces
from MoinMoin import wikiutil
from MoinMoin.macro2._base import MacroBlockBase

class Macro(MacroBlockBase):
    def macro(self):
        interwiki_list = wikiutil.load_wikimap(self.request)
        iwlist = interwiki_list.items() # this is where we cached it
        iwlist.sort()

        tag_l = ET.QName('list', namespaces.moin_page)
        tag_li = ET.QName('list-item', namespaces.moin_page)
        tag_li_label = ET.QName('list-item-label', namespaces.moin_page)
        tag_li_body = ET.QName('list-item-body', namespaces.moin_page)
        tag_code = ET.QName('code', namespaces.moin_page)
        tag_a = ET.QName('a', namespaces.moin_page)
        attr_href_xlink = ET.QName('href', namespaces.xlink)

        iw_list = ET.Element(tag_l)
        for tag, url in iwlist:
            href = wikiutil.join_wiki(url, 'RecentChanges')
            link = ET.Element(tag_a, attrib={attr_href_xlink: href}, children=[tag])
            label = ET.Element(tag_code, children=[link])
            iw_item_label = ET.Element(tag_li_label, children=[label])

            if '$PAGE' not in url:
                link = ET.Element(tag_a, attrib={attr_href_xlink: url}, children=[url])
            else:
                link = url
            body = ET.Element(tag_code, children=[link])
            iw_item_body = ET.Element(tag_li_body, children=[body])

            iw_item = ET.Element(tag_li, children=[iw_item_label, iw_item_body])
            iw_list.append(iw_item)

        return iw_list

