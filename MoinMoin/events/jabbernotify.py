# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - jabber notification plugin for event system

    This code sends notifications using a separate daemon.

    @copyright: 2007 by Karol Nowak <grywacz@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

import xmlrpclib


from MoinMoin.Page import Page
from MoinMoin.user import User, getUserList
import MoinMoin.events.notification as notification
import MoinMoin.events as ev


def handle(event):
    """An event handler"""

    cfg = event.request.cfg

    # Check for desired event type and if notification bot is configured
    if not cfg.jabber_enabled:
        return

    if isinstance(event, ev.PageChangedEvent):
        return handle_page_changed(event, False)
    elif isinstance(event, ev.TrivialPageChangedEvent):
        return handle_page_changed(event, True)
    elif isinstance(event, ev.JabberIDSetEvent) or isinstance(event, ev.JabberIDUnsetEvent):
        return handle_jid_changed(event)
    elif isinstance(event, ev.FileAttachedEvent):
        return handle_file_attached(event)
    elif isinstance(event, ev.PageDeletedEvent):
        return handle_page_deleted(event)
    elif isinstance(event, ev.PageRenamedEvent):
        return handle_page_renamed(event)
    elif isinstance(event, ev.UserCreatedEvent):
        return handle_user_created(event)


def handle_jid_changed(event):
    """ Handles events sent when user's JID changes """

    request = event.request
    server = request.cfg.notification_server
    _ = request.getText

    try:
        if isinstance(event, ev.JabberIDSetEvent):
            server.addJIDToRoster(request.cfg.secret, event.jid)
        else:
            server.removeJIDFromRoster(request.cfg.secret, event.jid)

    except xmlrpclib.Error, err:
        ev.logger.error(_("XML RPC error: %s"), str(err))
    except Exception, err:
        ev.logger.error(_("Low-level communication error: $s"), str(err))


def handle_file_attached(event):
    """Handles event sent when a file is attached to a page"""

    names = set()
    request = event.request
    page = Page(request, event.pagename)
    event_name = event.__class__.__name__

    subscribers = page.getSubscribers(request, return_users=1)
    notification.filter_subscriber_list(event, subscribers, True)

    for lang in subscribers.keys():
        jids = []
        data = notification.attachment_added(request, event.pagename, event.name, event.size)

        for usr in subscribers[lang]:
            if usr.jid and event_name in usr.jabber_subscribed_events:
                jids.append(usr.jid)
            else:
                continue

            if send_notification(request, jids, data['body'], data['subject']):
                names.update(usr.name)

    return notification.Success(names)


def handle_page_changed(event, trivial):
    """ Handles events related to page changes """
    request = event.request
    page = event.page

    subscribers = page.getSubscribers(request, return_users=1, trivial=trivial)
    notification.filter_subscriber_list(event, subscribers, True)
    return page_change("page_changed", request, page, subscribers, \
                       revisions=page.getRevList(), comment=event.comment)


def handle_page_deleted(event):
    """Handles event sent when a page is deleted"""

    request = event.request
    page = event.page

    subscribers = page.getSubscribers(request, return_users=1)
    notification.filter_subscriber_list(event, subscribers, True)
    return page_change("page_deleted", request, page, subscribers)

def handle_page_renamed(event):
    """Handles event sent when a page is renamed"""

    request = event.request
    page = event.page
    old_name = event.old_page.page_name

    subscribers = page.getSubscribers(request, return_users=1)
    notification.filter_subscriber_list(event, subscribers, True)
    return page_change("page_renamed", request, page, subscribers, oldname=old_name)


def handle_user_created(event):
    """Handles an event sent when a new user is being created"""

    jids = []
    user_ids = getUserList(event.request)
    event_name = event.__class__.__name__

    email = event.user.email or u"NOT SET"
    sitename = event.request.cfg.sitename
    username = event.user.name

    data = notification.user_created_message(event.request, sitename, username, email)

    for id in user_ids:
        usr = User(event.request, id=id)

        # Currently send this only to super users
        if usr.isSuperUser() and usr.jid and event_name in usr.jabber_subscribed_events:
            jids.append(usr.jid)

    send_notification(event.request, jids, data['body'], data['subject'])


def page_change(change_type, request, page, subscribers, **kwargs):
    """Sends notification about page being changed in some way"""
    _ = request.getText

    # send notifications to all subscribers
    if subscribers:
        recipients = set()

        for lang in subscribers:
            jids = [u.jid for u in subscribers[lang] if u.jid]
            names = [u.name for u in subscribers[lang] if u.jid]
            msg = notification.page_change_message(change_type, request, page, lang, **kwargs)
            result = send_notification(request, jids, msg)

            if result:
                recipients.update(names)

        if recipients:
            return notification.Success(recipients)

def send_notification(request, jids, message, subject=""):
    """ Send notifications for a single language.

    @param comment: editor's comment given when saving the page
    @param jids: an iterable of Jabber IDs to send the message to
    """
    _ = request.getText
    server = request.cfg.notification_server

    try:
        server.send_notification(request.cfg.secret, jids, message, subject)
        return True
    except xmlrpclib.Error, err:
        ev.logger.error(_("XML RPC error: %s"), str(err))
    except Exception, err:
        ev.logger.error(_("Low-level communication error: %s"), str(err), )

