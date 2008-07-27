# -*- coding: iso-8859-1 -*-
"""
    EditedSystemPages - list system pages that has been edited in this wiki.

    @copyright: 2004 Nir Soffer <nirs@freeshell.org>,
                2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin.Page import Page
from MoinMoin.util import namespaces
from MoinMoin.macro2._base import MacroBlockBase

class Macro(MacroBlockBase):
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

        tag_l = ET.QName('list', namespaces.moin_page)
        attr_generate = ET.QName('item-label-generate', namespaces.moin_page)
        tag_li = ET.QName('list-item', namespaces.moin_page)
        tag_li_body = ET.QName('list-item-body', namespaces.moin_page)
        tag_a = ET.QName('a', namespaces.moin_page)
        attr_href_xlink = ET.QName('href', namespaces.xlink)

        editedpages_list = ET.Element(tag_l, attrib={attr_generate: 'ordered'})
        for pagename in pagenames:
            url = u'wiki.local:' + pagename # XXX do a hint that this link is generated or pagelinks cache
                                            # will have all pages, leading to problems with OrphanedPages!
            pagelink = ET.Element(tag_a, attrib={attr_href_xlink: url}, children=[pagename])
            item_body = ET.Element(tag_li_body, children=[pagelink])
            item = ET.Element(tag_li, children=[item_body])
            editedpages_list.append(item)

        return editedpages_list

