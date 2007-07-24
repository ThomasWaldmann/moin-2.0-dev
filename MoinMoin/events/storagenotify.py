# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Notify the storage layer if a user or page changed
    to update the cache.

    @copyright: 2007 by Heinrich Wendel <heinrich.wendel@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

import MoinMoin.events as ev

from MoinMoin.storage.external import ItemCollection

def handle(event):
    """
    An event handler to update the cache when page/user changes.
    """

    if isinstance(event, ev.PageChangedEvent):
        handle_page_changed(event.request, event.page.page_name)
    elif isinstance(event, ev.TrivialPageChangedEvent):
        handle_page_changed(event.request, event.page.page_name)
    elif isinstance(event, ev.PageDeletedEvent):
        handle_page_changed(event.request, event.page.page_name)
    elif isinstance(event, ev.PageRevertedEvent):
        handle_page_changed(event.request, event.pagename)
    elif isinstance(event, ev.PageRenamedEvent):
        handle_page_changed(event.request, event.page.page_name)
        handle_page_changed(event.request, event.old_page.page_name)
    elif isinstance(event, ev.PageCopiedEvent):
        handle_page_changed(event.request, event.page.page_name)
        handle_page_changed(event.request, event.old_page.page_name)
    elif isinstance(event, ev.UserCreatedEvent):
        handle_user_changed(event.request, event.user.id)
    elif isinstance(event, ev.UserChangedEvent):
        handle_user_changed(event.request, event.user.id)


def handle_page_changed(request, pagename):
    """
    Sent an notification to update the cache.
    """
    ItemCollection(request.cfg.page_backend, request).update_cache(pagename)


def handle_user_changed(request, userid):
    """
    Sent an notification to update the cache.
    """
    ItemCollection(request.cfg.user_backend, request).update_cache(userid)
