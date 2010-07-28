# -*- coding: ascii -*-
"""
    MoinMoin - miscellaneous views

    Misc. stuff that doesn't fit into another view category.

    @copyright: 2010 MoinMoin:ThomasWaldmann
@license: GNU GPL, see COPYING for details.
"""

from MoinMoin.apps.misc import misc

@misc.route('/sitemap')
def sitemap():
    """
    Google (and others) XML sitemap
    """
    return "NotImplemented"
