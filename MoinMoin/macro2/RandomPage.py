# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - RandomPage Macro displays one or multiple random page links

    Note: This macro behaves a bit different now as it always returns a span
          with one (or multiple) random page links (separated by commas, if
          needed).
          In moin <= 1.7, the macro either emitted a single (inline) random
          page link, or if multiple random pages were requested, it emitted
          a (block) bullet list of random page links.

    @copyright: 2000 Juergen Hermann <jh@web.de>,
                2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import random
random.seed()

from emeraldtree import ElementTree as ET

from MoinMoin.util import namespaces
from MoinMoin.Page import Page
from MoinMoin.macro2._base import MacroInlineBase

class Macro(MacroInlineBase):
    def macro(self, links=1):
        request = self.request
        links = max(links, 1) # at least 1 link

        # Get full page unfiltered page list - very fast!
        all_pages = request.rootpage.getPageList(user='', exists=0)

        # Now select random page from the full list, and if it exists and we
        # can read it, save.
        pages = []
        found = 0
        while found < links and all_pages:
            # Take one random page from the list
            pagename = random.choice(all_pages)
            all_pages.remove(pagename)

            # Filter out deleted pages or pages the user may not read.
            page = Page(request, pagename)
            if page.exists() and request.user.may.read(pagename):
                pages.append(pagename)
                found += 1

        if not pages:
            return ''

        pages.sort()

        tag_span = ET.QName('span', namespaces.moin_page)
        tag_a = ET.QName('a', namespaces.moin_page)
        attr_href_xlink = ET.QName('href', namespaces.xlink)

        result = ET.Element(tag_span)
        for name in pages:
            result.append(ET.Element(tag_a,
                                     attrib={attr_href_xlink: u'wiki.local:' + name},
                                     children=[name]))
            result.append(", ")

        del result[-1] # kill last comma
        return result


