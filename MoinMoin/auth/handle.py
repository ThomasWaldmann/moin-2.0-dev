"""
    MoinMoin - Auth handlers

    Contains fuctions for handling auth requests
    (moin login, logout)
"""

from MoinMoin import auth
from flask import flaskg 

def handle_moin_login(form):
    """ Handles a moin type login request

    @param form: the values sent by the POST method
    @param type: dict
    """
    userobj = flaskg.user
    # init some stuff for auth processing:
    flaskg._login_multistage = None
    flaskg._login_multistage_name = None
    flaskg._login_messages = []

    params = {
        'username': form.get('login_username'),
        'password': form.get('login_password'),
        'attended': True,
        'stage': form.get('stage')
    }
    userobj = auth.handle_login(userobj, **params)
    flaskg.user = userobj


def handle_logout(userobj):
    """ 
    Handles a logout request

    @param userobj: the user to logout
    @type userobj: user object
    """
    userobj = auth.handle_logout(userobj)

