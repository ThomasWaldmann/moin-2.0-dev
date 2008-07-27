# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - BR Macro

    This very complicated macro produces a line break.

    Note: We still use macro/BR.py because the wiki parser only uses
          that one and BR macro calls are often used in i18n strings.
          After fixing this problem, macro/BR.py can get removed and
          macro2/_BR.py renamed to macro2/BR.py.

    @copyright: 2000 Juergen Hermann <jh@web.de>,
                2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin.util import namespaces

class Macro(object):
    def macro(self):
        """ Creates a linebreak. """
        return ET.Element(ET.QName('line-break', namespaces.moin_page))

