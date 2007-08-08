# -*- coding: iso-8859-1 -*-
"""
    Outputs the page count of the wiki.

    @copyright: 2007 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details
"""

Dependencies = ['namespace']

from MoinMoin import wikiutil

def macro_PageCount(macro, exists=None):
    """ Return number of pages readable by current user

    Return either an exact count or a count including deleted pages.
    """
    request = macro.request
    exists = wikiutil.get_unicode(request, exists, 'exists')

    try:
        bvalue = wikiutil.get_bool(request, exists)
    except ValueError:
        bvalue = False

    if exists == u'exists' or bvalue:
        only_existing = True
    else:
        only_existing = False

    count = request.rootpage.getPageCount(exists=only_existing)
    return macro.formatter.text("%d" % count)
