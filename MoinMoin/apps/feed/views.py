# -*- coding: ascii -*-
"""
    MoinMoin - feed views

    This contains all sort of feeds.

    @copyright: 2010 MoinMoin:ThomasWaldmann
                2010 MoinMoin:DiogenesAugusto
@license: GNU GPL, see COPYING for details.
"""

from datetime import datetime

from flask import request, url_for, Response
from flask import flaskg

from flask import current_app as app

from werkzeug.contrib.atom import AtomFeed

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.apps.feed import feed

from MoinMoin.items import NAME, ACL, MIMETYPE, \
                           EDIT_LOG_ACTION, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME, \
                           EDIT_LOG_USERID, EDIT_LOG_COMMENT
from MoinMoin.theme import get_editor_info
from MoinMoin.items import Item

@feed.route('/atom/<itemname:item_name>')
@feed.route('/atom', defaults=dict(item_name=''))
def atom(item_name):
    # maybe we need different modes:
    # - diffs in html don't look great without stylesheet
    # - full item in html is nice
    # - diffs in textmode are OK, but look very simple
    # - full-item content in textmode is OK, but looks very simple
    title = app.cfg.sitename
    feed = AtomFeed(title=title, feed_url=request.url, url=request.host_url)
    for rev in flaskg.storage.history(item_name=item_name):
        this_rev = rev
        this_revno = rev.revno
        item = rev.item
        name = rev[NAME]
        try:
            hl_item = Item.create(name, rev_no=this_revno)
            previous_revno = this_revno - 1
            if previous_revno >= 0:
                # simple text diff for changes
                previous_rev = item.get_revision(previous_revno)
                content = hl_item._render_data_diff_text(previous_rev, this_rev)
                content = '<div><pre>%s</pre></div>' % content
                content_type = 'xhtml'
            else:
                # full html rendering for new items
                content = hl_item._render_data()
                content_type = 'xhtml'
        except Exception, e:
            logging.exception("content rendering crashed")
            content = u'MoinMoin feels unhappy.'
            content_type = 'text'
        feed.add(title=name, title_type='text',
                 summary=rev.get(EDIT_LOG_COMMENT, ''), summary_type='text',
                 content=content, content_type=content_type,
                 author=get_editor_info(rev, external=True),
                 url=url_for('frontend.show_item', item_name=name, rev=this_revno, _external=True),
                 updated=datetime.utcfromtimestamp(rev.timestamp),
                )
    return Response(feed.to_string(), content_type='application/atom+xml')

