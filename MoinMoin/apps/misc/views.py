# -*- coding: utf-8 -*-
"""
    MoinMoin - miscellaneous views

    Misc. stuff that doesn't fit into another view category.

    @copyright: 2010 MoinMoin:ThomasWaldmann
@license: GNU GPL, see COPYING for details.
"""

import time

from flask import g, render_template, Response

from MoinMoin.apps.misc import misc

from MoinMoin import wikiutil
from MoinMoin.storage.error import NoSuchRevisionError

SITEMAP_HAS_SYSTEM_ITEMS = True

@misc.route('/sitemap')
def sitemap():
    """
    Google (and others) XML sitemap
    """
    def format_timestamp(ts):
        return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(ts))

    request = g.context
    storage = request.storage
    sitemap = []
    for item in storage.iteritems():
        try:
            rev = item.get_revision(-1)
        except NoSuchRevisionError:
            # XXX we currently also get user items, they have no revisions -
            # but in the end, they should not be readable by the user anyways
            continue
        if wikiutil.isSystemPage(request, item.name):
            if not SITEMAP_HAS_SYSTEM_ITEMS:
                continue
            # system items are rather boring
            changefreq = "yearly"
            priority = "0.1"
        else:
            # these are the content items:
            changefreq = "daily"
            priority = "0.5"
        sitemap.append((item.name, format_timestamp(rev.timestamp), changefreq, priority))
    # add an entry for root url
    item = storage.get_item(request.cfg.page_front_page)
    rev = item.get_revision(-1)
    sitemap.append((u'', format_timestamp(rev.timestamp), "hourly", "1.0"))
    sitemap.sort()
    content = render_template('misc/sitemap.xml', sitemap=sitemap)
    return Response(content, mimetype='text/xml')

