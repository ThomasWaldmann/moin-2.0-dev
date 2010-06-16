# -*- coding: iso-8859-1 -*-
"""
    MoinMoin GetVal macro - gets a value for a specified key from a dict.

    @copyright: 2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details
"""

from MoinMoin.macro2._base import MacroInlineBase

class Macro(MacroInlineBase):
    def macro(self, page=unicode, key=unicode):
        if page is None or key is None:
            raise ValueError("GetVal: you have to give pagename, key.")
        if not self.request.user.may.read(page):
            raise ValueError("You don't have enough rights on this page")
        d = self.request.dicts.dict(page)
        result = d.get(key, '')
        return result
