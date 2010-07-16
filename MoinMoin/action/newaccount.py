# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - create account action

    @copyright: 2007 MoinMoin:JohannesBerg,
                2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import user, wikiutil
from MoinMoin.security.textcha import TextCha
from MoinMoin.auth import MoinAuth


def _create_user(request):
    _ = request.getText
    form = request.form

    if request.method != 'POST':
        return

    if not wikiutil.checkTicket(request, form.get('ticket', '')):
        return _('Please use the interactive user interface to use action %(actionname)s!') % {'actionname': 'newaccount'}

    if not TextCha(request).check_answer_from_form():
        return _('TextCha: Wrong answer! Go back and try again...')

    # Create user profile
    theuser = user.User(request, auth_method="new-user")

    # Require non-empty name
    try:
        theuser.name = form['name']
    except KeyError:
        return _("Empty user name. Please enter a user name.")

    # Don't allow creating users with invalid names
    if not user.isValidName(request, theuser.name):
        return _("""Invalid user name '%s'.
Name may contain any Unicode alpha numeric character, with optional one
space between words. Group page name is not allowed.""") % wikiutil.escape(theuser.name)

    # Name required to be unique. Check if name belong to another user.
    if user.getUserId(request, theuser.name):
        return _("This user name already belongs to somebody else.")

    # try to get the password and pw repeat
    password = form.get('password1', '')
    password2 = form.get('password2', '')

    # Check if password is given and matches with password repeat
    if password != password2:
        return _("Passwords don't match!")
    if not password:
        return _("Please specify a password!")

    pw_checker = request.cfg.password_checker
    if pw_checker:
        pw_error = pw_checker(request, theuser.name, password)
        if pw_error:
            return _("Password not acceptable: %s") % wikiutil.escape(pw_error)

    # Encode password
    if password and not password.startswith('{SHA}'):
        try:
            theuser.enc_password = user.encodePassword(password)
        except UnicodeError, err:
            # Should never happen
            return "Can't encode password: %s" % wikiutil.escape(str(err))

    # try to get the email, for new users it is required
    email = wikiutil.clean_input(form.get('email', ''))
    theuser.email = email.strip()
    if not theuser.email and 'email' not in request.cfg.user_form_remove:
        return _("Please provide your email address. If you lose your"
                 " login information, you can get it by email.")

    # Email should be unique - see also MoinMoin/script/accounts/moin_usercheck.py
    if theuser.email and request.cfg.user_email_unique:
        if user.get_by_email_address(request, theuser.email):
            return _("This email already belongs to somebody else.")

    # save data
    theuser.save()

    result = _("User account created! You can use this account to login now...")
    return result


def execute(item_name, request):
    _ = request.getText

    found = False
    for auth in request.cfg.auth:
        if isinstance(auth, MoinAuth):
            found = True
            break

    if not found:
        # we will not have linked, so forbid access
        request.makeForbidden(403, 'No MoinAuth in auth list')
        return

    title = _("Create Account")
    if request.method == 'GET':
        textcha = TextCha(request)
        if textcha.is_enabled():
            textcha = textcha and textcha.render()
        else:
            textcha = None
        content = request.theme.render('newaccount.html',
                                        title=title,
                                        textcha=textcha,
                                        ticket=wikiutil.createTicket(request),
                                        )
    elif request.method == 'POST':
        if 'create' in request.form:
            request.theme.add_msg(_create_user(request), "dialog")
        content = request.theme.render('content.html', title=title)
    return content

