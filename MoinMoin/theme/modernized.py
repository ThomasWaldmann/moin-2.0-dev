# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - modernized theme (just a small wrapper, everything else
    is in ThemeBase now.

    @copyright: 2008 Radomir Dopieralski,
                2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.theme import ThemeBase

class Theme(ThemeBase):
    name = "modernized"


def execute(request):
    """
    Generate and return a theme object

    @param request: the request object
    @rtype: MoinTheme
    @return: Theme object
    """
    return Theme(request)

