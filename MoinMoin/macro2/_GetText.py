# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Load I18N Text

    This macro has the main purpose of supporting Help* page authors
    to insert the texts that a user actually sees on his screen into
    the description of the related features (which otherwise could
    get very confusing).

    Note: We still use macro/GetText.py because the wiki parser only uses
          that one and Verbatim macro calls are often used in i18n strings,
          e.g. in the editor quickhelp.
          After fixing this problem, macro/GetText.py can get removed and
          macro2/_GetText.py renamed to macro2/GetText.py.

    @copyright: 2001 Juergen Hermann <jh@web.de>,
                2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.macro2._base import MacroInlineBase

class Macro(MacroInlineBase):
    """ Return a translation of args, or args as is """
    def macro(self, text=u''):
        translation = self.request.getText(text)
        return translation

