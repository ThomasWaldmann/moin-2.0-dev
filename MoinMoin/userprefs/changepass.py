# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Password change preferences plugin

    @copyright: 2001-2004 Juergen Hermann <jh@web.de>,
                2003-2007 MoinMoin:ThomasWaldmann
                2007      MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

from flask import current_app as app

from flask import flaskg

from MoinMoin import _, N_
from MoinMoin import user, wikiutil
from MoinMoin.widget import html
from MoinMoin.userprefs import UserPrefBase
from flask import render_template

class Settings(UserPrefBase):
    def __init__(self, request):
        """ Initialize password change form. """
        UserPrefBase.__init__(self, request)
        self.request = request
        self.cfg = app.cfg
        self.title = _("Change password")
        self.name = 'changepass'


    def allowed(self):
        return (not 'password' in self.cfg.user_form_remove and
                not 'password' in self.cfg.user_form_disable and
                UserPrefBase.allowed(self) and
                not 'password' in flaskg.user.auth_attribs)


    def handle_form(self):
        _ = self._
        request = self.request
        form = request.form

        if form.has_key('cancel'):
            return

        if request.method != 'POST':
            return

        if not wikiutil.checkTicket(request, form.get('ticket', '')):
            return _('Please use the interactive user interface to use action %(actionname)s!') % {'actionname': 'userprefs.changepass'}

        password = form.get('password1', '')
        password2 = form.get('password2', '')

        # Check if password is given and matches with password repeat
        if password != password2:
            return 'error', _("Passwords don't match!")
        if not password:
            return 'error', _("Please specify a password!")

        pw_checker = app.cfg.password_checker
        if pw_checker:
            pw_error = pw_checker(request, flaskg.user.name, password)
            if pw_error:
                return 'error', _("Password not acceptable: %s") % pw_error

        try:
            flaskg.user.enc_password = user.encodePassword(password)
            flaskg.user.save()
            return 'info', _("Your password has been changed.")
        except UnicodeError, err:
            # Should never happen
            return "Can't encode password: %s" % str(err)


    def create_form(self, create_only=False, recover_only=False):
        """ Create the complete HTML form code. """
        return render_template('changepass.html',
                                          ticket=wikiutil.createTicket(self.request))
