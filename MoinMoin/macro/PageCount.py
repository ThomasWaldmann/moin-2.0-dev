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

    Return either an exact count (slow!) or fast count including deleted pages.

    TODO: make macro syntax more sane
    """
    request = macro.request
    exists = wikiutil.get_unicode(request, exists, 'exists')
    # Check input
    include_deleted = True
    if exists == u'exists':
        include_deleted = False
    elif exists:
        raise ValueError("Wrong argument: %r" % exists)

    count = request.rootitem.count_items(include_deleted=include_deleted)
    return macro.formatter.text("%d" % count)

