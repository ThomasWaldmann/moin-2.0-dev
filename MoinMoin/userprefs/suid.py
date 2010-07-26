# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - switch user form

    @copyright: 2001-2004 Juergen Hermann <jh@web.de>,
                2003-2007 MoinMoin:ThomasWaldmann,
                2007      MoinMoin:JohannesBerg,
                2010      MoinMoin:ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import user, util, wikiutil
from MoinMoin.widget import html
from MoinMoin.userprefs import UserPrefBase
from MoinMoin.action.UserBrowser import get_account_infos

class Settings(UserPrefBase):

    def __init__(self, request):
        """ Initialize setuid settings form. """
        UserPrefBase.__init__(self, request)
        self.request = request
        self._ = request.getText
        self.cfg = request.cfg
        _ = self._
        self.title = _("Switch user")
        self.name = 'suid'

    def allowed(self):
        return (self.request.user.auth_method in self.request.cfg.auth_can_logout and
               UserPrefBase.allowed(self) and self.request.user.isSuperUser())

    def handle_form(self):
        _ = self._
        request = self.request
        form = request.form

        if form.has_key('cancel'):
            return

        if request.method != 'POST':
            return

        if not wikiutil.checkTicket(request, form.get('ticket', '')):
            return _('Please use the interactive user interface to use action %(actionname)s!') % {'actionname': 'userprefs.suid'}


        uid = form.get('selected_user', '')
        if not uid:
            return 'error', _("No user selected")
        theuser = user.User(request, uid, auth_method='setuid')
        if not theuser or not theuser.exists():
            return 'error', _("No user selected")
        # set valid to True so superusers can even switch
        # to disable accounts
        theuser.valid = True
        request._setuid_real_user = request.user
        # now continue as the other user
        request.user = theuser
        return  _("You can now change the settings of the selected user account; log out to get back to your account.")

    def create_form(self):
        """ Create the complete HTML form code. """
        user_accounts=get_account_infos(self.request)
        if len(user_accounts) > 1:
            return self.request.theme.render('suid.html',
                                             user_accounts=user_accounts,
                                             ticket=wikiutil.createTicket(self.request))
        return "You are the only user."
