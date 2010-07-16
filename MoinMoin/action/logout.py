# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - logout action

    The real logout is done in MoinMoin.request.
    Here is just some stuff to notify the user.

    @copyright: 2005-2006 Radomirs Cirskis <nad2000@gmail.com>,
                2009 MoinMoin:ThomasWaldmann,
                2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""

def execute(item_name, request):
    _ = request.getText
    title = _("Logout")
    # if the user really was logged out say so,
    # but if the user manually added ?do=logout
    # and that isn't really supported, then don't
    if not request.user.valid:
        msg = _("You are now logged out."), "info"
    else:
        # something went wrong
        msg = _("You are still logged in."), "warning"
    request.theme.add_msg(*msg)
    content = request.theme.render('content.html', title=title)
    return content
