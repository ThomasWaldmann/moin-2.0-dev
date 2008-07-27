# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - PageSize Macro displays an ordered list with page sizes and names

    @copyright: 2002 Juergen Hermann <jh@web.de>,
                2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin.util import namespaces
from MoinMoin.macro2._base import MacroBlockBase

class Macro(MacroBlockBase):
    def macro(self):
        if self.request.isSpiderAgent: # reduce bot cpu usage
            return ''

        # get list of pages and their objects
        pages = self.request.rootpage.getPageDict()

        # get sizes and sort them
        sizes = []
        for name, page in pages.items():
            sizes.append((page.size(), page))
        sizes.sort()
        sizes.reverse()

        tag_l = ET.QName('list', namespaces.moin_page)
        attr_generate = ET.QName('item-label-generate', namespaces.moin_page)
        tag_li = ET.QName('list-item', namespaces.moin_page)
        tag_li_body = ET.QName('list-item-body', namespaces.moin_page)
        tag_code = ET.QName('code', namespaces.moin_page)
        tag_a = ET.QName('a', namespaces.moin_page)
        attr_href_xlink = ET.QName('href', namespaces.xlink)

        pagesize_list = ET.Element(tag_l, attrib={attr_generate: 'ordered'})
        for size, page in sizes:
            pagesize = ET.Element(tag_code, children=["%6d " % size])
            url = u'wiki.local:' + page.page_name # XXX do a hint that this link is generated or pagelinks cache
                                                  # will have all pages, leading to problems with OrphanedPages!
            pagelink = ET.Element(tag_a, attrib={attr_href_xlink: url}, children=[page.page_name])
            item_body = ET.Element(tag_li_body, children=[pagesize, pagelink])
            item = ET.Element(tag_li, children=[item_body])
            pagesize_list.append(item)

        return pagesize_list


