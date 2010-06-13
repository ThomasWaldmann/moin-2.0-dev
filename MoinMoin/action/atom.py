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

def execute(item_name, request):
    cfg = request.cfg
    # XXX we want to be able to get global recent changes when visiting
    # hostname/?do=rc, but we get item_name = cfg.page_front_page for this
    if item_name == cfg.page_front_page:
        item_name = u''
    title = cfg.sitename
    feed = AtomFeed(title=title, feed_url=request.url, url=request.host_url)
    for rev in request.storage.history(item_name=item_name):
        name = rev[NAME]
        url = request.abs_href(name)
        author = user.get_editor(request,
                      rev[EDIT_LOG_USERID], rev[EDIT_LOG_ADDR], rev[EDIT_LOG_HOSTNAME])
        updated = datetime.utcfromtimestamp(rev.timestamp)
        feed.add(title=name, title_type='text',
                 summary=rev[EDIT_LOG_COMMENT], summary_type='text',
                 #content=content, content_type='text',
                 author=str(author),
                 url=url,
                 updated=updated)
    request.write(feed.to_string())

