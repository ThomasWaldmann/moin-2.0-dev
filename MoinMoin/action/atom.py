"""
    MoinMoin - Atom Feed

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from datetime import datetime

from werkzeug.contrib.atom import AtomFeed

from MoinMoin import user
from MoinMoin.items import NAME, ACL, MIMETYPE, \
                           EDIT_LOG_ACTION, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME, \
                           EDIT_LOG_USERID, EDIT_LOG_COMMENT
from MoinMoin.items import Item

def execute(item_name, request):
    cfg = request.cfg
    # XXX we want to be able to get global recent changes when visiting
    # hostname/?do=rc, but we get item_name = cfg.page_front_page for this
    if item_name == cfg.page_front_page:
        item_name = u''
    title = cfg.sitename
    feed = AtomFeed(title=title, feed_url=request.url, url=request.host_url)
    for rev in request.storage.history(item_name=item_name):
        this_rev = rev
        this_revno = rev.revno
        item = rev.item
        name = rev[NAME]
        author = user.get_printable_editor(request,
                      rev.get(EDIT_LOG_USERID), rev.get(EDIT_LOG_ADDR), rev.get(EDIT_LOG_HOSTNAME))
        updated = datetime.utcfromtimestamp(rev.timestamp)
        hl_item = Item.create(request, name, rev_no=this_revno)
        previous_revno = this_revno - 1
        if previous_revno >= 0:
            previous_rev = item.get_revision(previous_revno)
            # XXX use the normal diff display for now, should be a specialized
            # method and maybe a template with inline style
            content = hl_item.do_diff(previous_rev, this_rev)
        else:
            # XXX use the normal show display for now, should be a specialized
            # method and maybe a template with inline style
            content = hl_item.do_show()
        url = hl_item.rev_url(_absolute=True)
        feed.add(title=name, title_type='text',
                 summary=rev.get(EDIT_LOG_COMMENT, ''), summary_type='text',
                 content=content, content_type='html',
                 author=author,
                 url=url,
                 updated=updated)
    request.write(feed.to_string())

