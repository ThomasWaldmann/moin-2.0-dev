# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Utility functions for the web-layer

    @copyright: 2003-2008 MoinMoin:ThomasWaldmann,
                2008-2008 MoinMoin:FlorianKrupicka
    @license: GNU GPL, see COPYING for details.
"""

from werkzeug import abort, redirect, Response

from flask import flaskg

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import wikiutil
from MoinMoin.Page import Page


def redirect_last_visited(request):
    pagetrail = flaskg.user.getTrail()
    if pagetrail:
        # Redirect to last page visited
        last_visited = pagetrail[-1]
        wikiname, pagename = wikiutil.split_interwiki(last_visited)
        if wikiname != 'Self':
            wikitag, wikiurl, wikitail, error = wikiutil.resolve_interwiki(request, wikiname, pagename)
            url = wikiurl + wikiutil.quoteWikinameURL(wikitail)
        else:
            url = Page(request, pagename).url(request)
    else:
        # Or to localized FrontPage
        url = wikiutil.getFrontPage(request).url(request)
    url = request.getQualifiedURL(url)
    return abort(redirect(url))


class UniqueIDGenerator(object):
    def __init__(self, pagename=None):
        self.unique_stack = []
        self.include_stack = []
        self.include_id = None
        self.page_ids = {None: {}}
        self.pagename = pagename

    def push(self):
        """
        Used by the TOC macro, this ensures that the ID namespaces
        are reset to the status when the current include started.
        This guarantees that doing the ID enumeration twice results
        in the same results, on any level.
        """
        self.unique_stack.append((self.page_ids, self.include_id))
        self.include_id, pids = self.include_stack[-1]
        self.page_ids = {}
        for namespace in pids:
            self.page_ids[namespace] = pids[namespace].copy()

    def pop(self):
        """
        Used by the TOC macro to reset the ID namespaces after
        having parsed the page for TOC generation and after
        printing the TOC.
        """
        self.page_ids, self.include_id = self.unique_stack.pop()
        return self.page_ids, self.include_id

    def begin(self, base):
        """
        Called by the formatter when a document begins, which means
        that include causing nested documents gives us an include
        stack in self.include_id_stack.
        """
        pids = {}
        for namespace in self.page_ids:
            pids[namespace] = self.page_ids[namespace].copy()
        self.include_stack.append((self.include_id, pids))
        self.include_id = self(base)
        # if it's the page name then set it to None so we don't
        # prepend anything to IDs, but otherwise keep it.
        if self.pagename and self.pagename == self.include_id:
            self.include_id = None

    def end(self):
        """
        Called by the formatter when a document ends, restores
        the current include ID to the previous one and discards
        the page IDs state we kept around for push().
        """
        self.include_id, pids = self.include_stack.pop()

    def __call__(self, base, namespace=None):
        """
        Generates a unique ID using a given base name. Appends a running count to the base.

        Needs to stay deterministic!

        @param base: the base of the id
        @type base: unicode
        @param namespace: the namespace for the ID, used when including pages

        @returns: a unique (relatively to the namespace) ID
        @rtype: unicode
        """
        if not isinstance(base, unicode):
            base = unicode(str(base), 'ascii', 'ignore')
        if not namespace in self.page_ids:
            self.page_ids[namespace] = {}
        count = self.page_ids[namespace].get(base, -1) + 1
        self.page_ids[namespace][base] = count
        if not count:
            return base
        return u'%s-%d' % (base, count)

