# -*- coding: iso-8859-1 -*-
"""
    Outputs the text verbatimly.

    Note: We still use macro/Verbatim.py because the wiki parser only uses
          that one and Verbatim macro calls are often used in i18n strings,
          e.g. in the editor quickhelp.
          After fixing this problem, macro/Verbatim.py can get removed and
          macro2/_Verbatim.py renamed to macro2/Verbatim.py.

    @copyright: 2005-2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details
"""

from MoinMoin.macro2._base import MacroInlineBase

class Macro(MacroInlineBase):
    def macro(self, text=u''):
        return text

