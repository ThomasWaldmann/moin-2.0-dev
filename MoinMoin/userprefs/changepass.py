# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Password change preferences plugin

    @copyright: 2001-2004 Juergen Hermann <jh@web.de>,
                2003-2007 MoinMoin:ThomasWaldmann
                2007      MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

import time
from MoinMoin import user, wikiutil
from MoinMoin.widget import html
from MoinMoin.userprefs import UserPrefBase


class Settings(UserPrefBase):
    def __init__(self, request):
        """ Initialize password change form. """
        UserPrefBase.__init__(self, request)
        self.request = request
        self._ = request.getText
        _ = request.getText
        self.cfg = request.cfg
        self.title = _("Change password", formatted=False)
        self.name = 'changepass'


    def allowed(self):
        return (not 'password' in self.cfg.user_form_remove and
                not 'password' in self.cfg.user_form_disable and
                UserPrefBase.allowed(self) and
                not 'password' in self.request.user.auth_attribs)


    def handle_form(self):
        _ = self._
        request = self.request
        form = request.form

        if form.has_key('cancel'):
            return

        if request.request_method != 'POST':
            return

        password = form.get('password', [''])[0]
        password2 = form.get('password2', [''])[0]

        # Check if password is given and matches with password repeat
        if password != password2:
            return _("Passwords don't match!")

        pw_checker = request.cfg.password_checker
        if pw_checker:
            pw_error = pw_checker(request.user.name, password)
            if pw_error:
                return _("Password not acceptable: %s") % pw_error

        try:
            self.request.user.enc_password = user.encodePassword(password)
            self.request.user.save()
            return _("Your password has been changed.")
        except UnicodeError, err:
            # Should never happen
            return "Can't encode password: %s" % str(err)


    def create_form(self, create_only=False, recover_only=False):
        """ Create the complete HTML form code. """
        _ = self._
        form = self.make_form(html.Text(_("To change your password, "
                                          "enter a new password twice.")))

        self.make_row(_('Password'),
                      [html.INPUT(type="password", size=36, name="password")])
        self.make_row(_('Password repeat'),
                      [html.INPUT(type="password", size=36, name="password2")])

        # Add buttons
        self.make_row('', [
                html.INPUT(type="submit", name='save', value=_("Change password")),
                ' ',
                html.INPUT(type="submit", name='cancel', value=_("Cancel")),
              ])

        return unicode(form)