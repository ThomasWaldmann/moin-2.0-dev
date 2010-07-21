# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Filters

    @copyright: 2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""

def shorten_item_name(name, length=25):
    """
    Shorten item names
    
    Shorten very long item names that tend to break the user
    interface. The short name is usually fine, unless really stupid
    long names are used (WYGIWYD).
    
    @param name: item name, unicode
    @param length: maximum length for shortened item names, int
    @rtype: unicode
    @return: shortened version.
    """
    # First use only the sub page name, that might be enough
    if len(name) > length:
        name = name.split('/')[-1]
        # If it's not enough, replace the middle with '...'
        if len(name) > length:
            half, left = divmod(length - 3, 2)
            name = u'%s...%s' % (name[:half + left], name[-half:])
    return name
