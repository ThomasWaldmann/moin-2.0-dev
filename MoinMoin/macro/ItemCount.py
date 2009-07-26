# -*- coding: iso-8859-1 -*-
"""
    Outputs the item count of the wiki.

    @copyright: 2007,2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details
"""

Dependencies = ['namespace']

def macro_ItemCount(macro, include_deleted=False):
    """ Return number of items readable by current user

    Return either an exact count (slow!) or fast count including deleted items.
    """
    count = macro.request.rootitem.count_items(include_deleted=include_deleted)
    return macro.formatter.text("%d" % count)

