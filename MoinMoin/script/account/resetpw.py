# -*- coding: iso-8859-1 -*-
"""
MoinMoin - change a user password

TODO: Currently works on unprotected user backend

@copyright: 2006 MoinMoin:ThomasWaldmann,
            2008 MoinMoin:JohannesBerg,
            2011 MoinMoin:ReimarBauer
@license: GNU GPL, see COPYING for details.
"""
from flask import flaskg
from flask import current_app as app
from flaskext.script import Command, Option
from MoinMoin import user

class Reset_Users_Password(Command):
    description = 'This command allows you to change a user password.'
    option_list = (
        Option('--name', '-n', required=False, dest='name', type=unicode,
               help='Reset password for the user with user name NAME.'),
        Option('--uid', '-u', required=False, dest='uid', type=unicode,
               help='Reset password for the user with user id UID.' ),
        Option('--password', '-p', required=True, dest='password', type=unicode,
               help='New password for this account.')
        )

    def run(self, name, uid, password):
        flaskg.unprotected_storage = app.unprotected_storage
        flags_given = name or uid
        if not flags_given:
            print 'incorrect number of arguments'
            import sys
            sys.exit()

        if uid:
            u = user.User(uid)
        elif name:
            uid = user.getUserId(name)
            u = user.User(uid)

        if not u.exists():
            print 'This user "%s" does not exists!' % u.name
            return

        u.enc_password = user.encodePassword(password)
        u.save()
        print 'Password changed.'
