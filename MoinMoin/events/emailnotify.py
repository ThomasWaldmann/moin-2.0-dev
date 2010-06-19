# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - email notification plugin from event system

    This code sends email notifications about page changes.
    TODO: refactor it to handle separate events for page changes, creations, etc

    @copyright: 2007 by Karol Nowak <grywacz@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import user
from MoinMoin.Page import Page
from MoinMoin.mail import sendmail
from MoinMoin.support.python_compatibility import set
from MoinMoin.user import User, getUserList

import MoinMoin.events as ev
import MoinMoin.events.notification as notification


def prep_page_changed_mail(request, page, comment, email_lang, revisions, trivial):
    """ Prepare information required for email notification about page change

    @param page: the modified page instance
    @param comment: editor's comment given when saving the page
    @param email_lang: language of email
    @param revisions: revisions of this page (newest first!)
    @param trivial: the change is marked as trivial
    @return: dict with email title and body
    @rtype: dict

    """
    change = notification.page_change_message("page_changed", request, page, email_lang, comment=comment, revisions=revisions)
    _ = lambda text: request.getText(text, lang=email_lang)

    if len(revisions) >= 2:
        querystr = {'do': 'diff',
                    'rev2': str(revisions[0]),
                    'rev1': str(revisions[1])}
    else:
        querystr = {}

    pagelink = "%(link)s\n\n" % {'link': notification.page_link(request, page, querystr)}

    subject = _('[%(sitename)s] %(trivial)sUpdate of "%(pagename)s" by %(username)s') % {
            'trivial': (trivial and _("Trivial ")) or "",
            'sitename': page.cfg.sitename or "Wiki",
            'pagename': page.page_name,
            'username': page.last_editor(),
        }

    if change.has_key('comment'):
        comment = _("Comment:") + "\n" + change['comment'] + "\n\n"
    else:
        comment = ''

    return {'subject': subject, 'text': change['text'] + pagelink + comment + change['diff']}


def send_notification(request, from_address, emails, data):
    """ Send notification email

    @param emails: list of email addresses
    @return: sendmail result
    @rtype int

    """
    return sendmail.sendmail(request, emails, data['subject'], data['text'], mail_from=from_address)


def handle_page_change(event):
    """ Send email to all subscribers of given page.

    @param event: event to notify about
    @rtype: string
    @return: message, indicating success or errors.

    """
    comment = event.comment
    page = event.page
    request = event.request
    trivial = isinstance(event, ev.TrivialPageChangedEvent)
    subscribers = page.getSubscribers(request, return_users=1)
    mail_from = page.cfg.mail_from

    if subscribers:
        recipients = set()

        # get a list of old revisions, and append a diff
        revisions = page.getRevList()

        # send email to all subscribers
        for lang in subscribers:
            users = [u for u in subscribers[lang]
                     if event.name in u.email_subscribed_events]
            emails = [u.email for u in users]
            names = [u.name for u in users]
            data = prep_page_changed_mail(request, page, comment, lang, revisions, trivial)

            if send_notification(request, mail_from, emails, data):
                recipients.update(names)

        if recipients:
            return notification.Success(recipients)


def handle_user_created(event):
    """Sends an email to super users that have subscribed to this event type"""

    request = event.request
    sitename = request.cfg.sitename
    from_address = request.cfg.mail_from
    event_name = event.name
    email = event.user.email or u"NOT SET"
    username = event.user.name

    user_ids = getUserList(request)
    for usr_id in user_ids:
        usr = User(request, id=usr_id)
        # Currently send this only to super users
        if usr.isSuperUser() and event_name in usr.email_subscribed_events:
            _ = lambda text: request.getText(text, lang=usr.language or 'en')
            data = notification.user_created_message(request, _, sitename, username, email)
            send_notification(request, from_address, [usr.email], data)


def handle(event):
    """An event handler"""

    if not event.request.cfg.mail_enabled:
        return

    if isinstance(event, (ev.PageChangedEvent, ev.TrivialPageChangedEvent)):
        return handle_page_change(event)
    elif isinstance(event, ev.UserCreatedEvent):
        return handle_user_created(event)

