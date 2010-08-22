# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - RandomQuote Macro

    Selects a random quote from FortuneCookies or a given page.

    Usage:
        <<RandomQuote()>>
        <<RandomQuote(WikiTips)>>

    Comments:
        It will look for list delimiters on the page in question.
        It will ignore anything that is not in an "*" list.

    @copyright: 2002-2004 Juergen Hermann <jh@web.de>,
                2002-2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import random

from flask import flaskg

from MoinMoin.Page import Page
from MoinMoin.macro2._base import MacroInlineBase

class Macro(MacroInlineBase):
    def macro(self, pagename=u'FortuneCookies'):
        request = self.request

        if flaskg.user.may.read(pagename):
            page = Page(request, pagename)
            raw = page.get_raw_body()
        else:
            raw = u""

        # this selects lines looking like a 1st level list item
        quotes = [quote[3:].strip() for quote in raw.splitlines() if quote.startswith(' * ')]
        if quotes:
            from MoinMoin.converter2.moinwiki_in import Converter
            quote = random.choice(quotes)
            return Converter(request)([quote])

        return u'' # no quotes found
