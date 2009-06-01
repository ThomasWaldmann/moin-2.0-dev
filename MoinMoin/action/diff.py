# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - show diff between 2 item revisions

    TODO: acl checks were removed, have to be done on storage layer

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""
from MoinMoin.items import Item, MIMETYPE

def execute(item_name, request):
    try:
        date = int(request.values.get('date'))
    except StandardError:
        date = None

    # get (absolute) current revision number
    item = request.cfg.data_backend.get_item(item_name)
    current_revno = item.get_revision(-1).revno

    if date is None:
        try:
            revno1 = int(request.values.get('rev1', -2))
        except StandardError:
            revno1 = -2  # -2 means second latest rev
        try:
            revno2 = int(request.values.get('rev2', -1))
        except StandardError:
            revno2 = -1  # -1 means latest rev

    else:
        # this is how we get called from "recent changes"
        # try to find the latest rev1 before bookmark <date>
        revnos = item.list_revisions()
        revnos.reverse()  # begin with latest rev
        for revno in revnos:
            revision = item.get_revision(revno)
            if revision.timestamp <= date:
                revno1 = revision.revno
                break
        else:
            revno1 = revno  # if we didn't find a rev, we just take oldest rev we have
        revno2 = -1  # and compare it with latest we have

    # now we can calculate the absolute revnos if we don't have them yet
    if revno1 < 0:
        revno1 += current_revno + 1
    if revno2 < 0:
        revno2 += current_revno + 1

    if revno1 > revno2:
        oldrevno, newrevno = revno2, revno1
    else:
        oldrevno, newrevno = revno1, revno2

    oldrev = item.get_revision(oldrevno)
    newrev = item.get_revision(newrevno)

    oldmt = oldrev.get(MIMETYPE)
    newmt = newrev.get(MIMETYPE)

    if oldmt == newmt:
        # easy, exactly the same mimetype, call do_diff for it
        commonmt = newmt
    else:
        oldmajor = oldmt.split('/')[0]
        newmajor = newmt.split('/')[0]
        if oldmajor == newmajor:
            # at least same major mimetype, use common base item class
            commonmt = newmajor + '/'
        else:
            # nothing in common
            commonmt = ''

    item = Item.create(request, item_name, mimetype=commonmt, rev_no=newrevno)
    content = item.do_diff(oldrev, newrev)
    request.theme.render_content(item_name, content)

