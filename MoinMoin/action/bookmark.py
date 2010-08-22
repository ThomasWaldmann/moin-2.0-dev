# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - set or delete bookmarks (in time) for RecentChanges

    @copyright: 2000-2004 by Juergen Hermann <jh@web.de>,
                2006 by MoinMoin:ThomasWaldmann,
                2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""
import time

from flask import flash, flaskg

from MoinMoin import _, N_
from MoinMoin import wikiutil
from MoinMoin.Page import Page

def execute(pagename, request):
    """ set bookmarks (in time) for RecentChanges or delete them """
    if not flaskg.user.valid:
        actname = __name__.split('.')[-1]
        flash(_("You must login to use this action: %(action)s.") % {"action": actname}, "error")
        return Page(request, pagename).send_page()

    timestamp = request.values.get('time')
    if timestamp is not None:
        if timestamp == 'del':
            tm = None
        else:
            try:
                tm = int(timestamp)
            except StandardError:
                tm = wikiutil.timestamp2version(time.time())
    else:
        tm = wikiutil.timestamp2version(time.time())

    if tm is None:
        flaskg.user.delBookmark()
    else:
        flaskg.user.setBookmark(tm)
    XXX.page.send_page()
