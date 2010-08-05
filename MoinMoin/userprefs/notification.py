# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Notification preferences

    @copyright: 2001-2004 Juergen Hermann <jh@web.de>,
                2003-2007 MoinMoin:ThomasWaldmann
                2007      MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import events, wikiutil
from MoinMoin.widget import html
from MoinMoin.userprefs import UserPrefBase
from flask import render_template

def get_notify_info(request):
    _ = request.getText
    types = []
    if request.cfg.mail_enabled and request.user.email:
        types.append(('email', _("Email")))
    isSuperUser = request.user.isSuperUser()
    notify_infos = []
    event_list = events.get_subscribable_events()
    allowed = []
    for key in event_list.keys():
        if not event_list[key]['superuser'] or isSuperUser:
            allowed.append((key, event_list[key]['desc']))

    for evname, evdescr in allowed:
        for notiftype, notifdescr in types:
            checked = ""
            if evname in getattr(request.user,
                                 '%s_subscribed_events' % notiftype):
                checked = "checked"
            notify_infos.append(dict(name='subscribe:%s:%s' % (notiftype, evname),
                                     checked=checked,
                                     text=html.Raw(request.getText(evdescr)))
                      )
    return notify_infos


class Settings(UserPrefBase):
    def __init__(self, request):
        """ Initialize user settings form. """
        UserPrefBase.__init__(self, request)
        self.request = request
        self._ = request.getText
        self.cfg = request.cfg
        self.title = self._("Notification")
        self.name = 'notification'

    def _decode_pagelist(self, key):
        """ Decode list of pages from form input

        Each line is a page name, empty lines ignored.

        @param key: the form key to get
        @rtype: list of unicode strings
        @return: list of normalized names
        """
        text = self.request.form.get(key, '')
        text = text.replace('\r', '')
        items = []
        for item in text.split('\n'):
            item = item.strip()
            if not item:
                continue
            items.append(item)
        return items

    def _save_notification_settings(self):
        _ = self._
        form = self.request.form

        theuser = self.request.user
        if not theuser:
            return

        # subscription for page change notification
        theuser.subscribed_items = self._decode_pagelist('subscribed_items')

        # subscription to various events
        available = events.get_subscribable_events()
        theuser.email_subscribed_events = []
        types = {
            'email': theuser.email_subscribed_events,
        }
        for tp in types:
            for evt in available:
                fieldname = 'subscribe:%s:%s' % (tp, evt)
                if fieldname in form:
                    types[tp].append(evt)
        # save data
        theuser.save()

        return 'info', _("Notification settings saved!")


    def handle_form(self):
        _ = self._
        request = self.request
        form = request.form

        if form.has_key('cancel'):
            return

        if request.method != 'POST':
            return

        if not wikiutil.checkTicket(request, form.get('ticket', '')):
            return _('Please use the interactive user interface to use action %(actionname)s!') % {'actionname': 'userprefs.notification'}


        if form.has_key('save'): # Save user profile
            return self._save_notification_settings()


    def create_form(self):
        """ Create the complete HTML form code. """
        return render_template('notification.html',
                                          notify=get_notify_info(self.request),
                                          ticket=wikiutil.createTicket(self.request))

    def allowed(self):
        return UserPrefBase.allowed(self) and self.cfg.mail_enabled
