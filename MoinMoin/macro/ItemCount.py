# -*- coding: iso-8859-1 -*-
"""
    Outputs the item count of the wiki.

    @copyright: 2007,2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details
"""

Dependencies = ['namespace']

def macro_ItemCount(macro):
    """
    Return number of items readable by current user.
    """
    count = macro.request.rootitem.count_items()
    return macro.formatter.text("%d" % count)

