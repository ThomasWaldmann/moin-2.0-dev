# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - jabber notification plugin for event system

    This code sends notifications using a separate daemon.

    @copyright: 2007 by Karol Nowak <grywacz@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

import xmlrpclib

from MoinMoin import error
from MoinMoin.Page import Page
from MoinMoin.user import User, getUserList
from MoinMoin.support.python_compatibility import set
from MoinMoin.action.AttachFile import getAttachUrl

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
    event_name = event.name
    subscribers = page.getSubscribers(request, return_users=1)
    notification.filter_subscriber_list(event, subscribers, True)
    recipients = []

    for lang in subscribers:
        recipients.extend(subscribers[lang])

    attachlink = request.getBaseURL() + getAttachUrl(event.pagename, event.filename, request)
    pagelink = request.getQualifiedURL(page.url(request, {}, relative=False))

    for lang in subscribers.keys():
        _ = lambda text: request.getText(text, lang=lang, formatted=False)
        data = notification.attachment_added(request, _, event.pagename, event.filename, event.size)
        links = [{'url': attachlink, 'description': _("Attachment link")},
                  {'url': pagelink, 'description': _("Page link")}]

        jids = [usr.jid for usr in subscribers[lang]]
        data['url_list'] = links
        data['action'] = "file_attached"

        if send_notification(request, jids, data):
            names.update(recipients)

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

    # Change request's page so that we filter subscribers of the OLD page
    request.page = event.old_page
    notification.filter_subscriber_list(event, subscribers, True)
    request.page = page
    return page_change("page_renamed", request, page, subscribers, old_name=old_name)


def handle_user_created(event):
    """Handles an event sent when a new user is being created"""

    jids = []
    user_ids = getUserList(event.request)
    event_name = event.name

    email = event.user.email or u"NOT SET"
    sitename = event.request.cfg.sitename
    username = event.user.name

    msg = notification.user_created_message(event.request, sitename, username, email)

    for id in user_ids:
        usr = User(event.request, id=id)

        # Currently send this only to super users
        if usr.isSuperUser() and usr.jid and event_name in usr.jabber_subscribed_events:
            jids.append(usr.jid)

    data = {'action': "user_created", 'subject': msg['subject'], 'text': msg['body'],
            'url_list': []}

    send_notification(event.request, jids, data)


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
            page_url = request.getQualifiedURL(page.url(request, relative=False))
            url = {'url': page_url, 'description': _("Changed page")}
            data = {'action': change_type, 'subject': _('Page changed'),
                            'url_list': [url], 'text': msg['text'], 'diff': msg.get('diff', ''),
                            'comment': msg.get('comment', ''), 'editor': msg['editor'],
                            'old_name': msg.get('old_name', ''), 'page_name': msg.get('page_name', ''),
                            'revision': msg.get('revision', '')}

            result = send_notification(request, jids, data)

            if result:
                recipients.update(names)

        if recipients:
            return notification.Success(recipients)

def send_notification(request, jids, notification):
    """ Send notifications for a single language.

    @param jids: an iterable of Jabber IDs to send the message to
    @param message: message text
    @param subject: subject of the message, makes little sense for chats
    @param url_list: a list of dicts containing URLs and their descriptions
    @type url_list: list

    """
    _ = request.getText
    server = request.cfg.notification_server

    if type(notification) != dict:
        raise ValueError("notification must be of type dict!")

    if type(notification['url_list']) != list:
        raise ValueError("url_list must be of type list!")

    try:
        server.send_notification(request.cfg.secret, jids, notification)
        return True
    except xmlrpclib.Error, err:
        ev.logger.error(_("XML RPC error: %s"), str(err))
    except Exception, err:
        ev.logger.error(_("Low-level communication error: %s"), str(err), )

