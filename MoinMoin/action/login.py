# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - login action

    The real login is done in MoinMoin.request.
    Here is only some user notification in case something went wrong.

    TODO: re-add multistage login (see moin/1.9-storage).

    @copyright: 2005-2006 Radomirs Cirskis <nad2000@gmail.com>,
                2006,2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

def execute(item_name, request):
    _ = request.getText
    title = _("Login")
    if request.method == 'GET':
        login_hints = []
        for authmethod in request.cfg.auth:
            hint = authmethod.login_hint(request)
            if hint:
                login_hints.append(hint)
        template = request.theme.env.get_template('login.html')
        content = template.render(gettext=request.getText,
                                  login_hints=login_hints,
                                  login_inputs=request.cfg.auth_login_inputs,
                                 )
        request.theme.render_content(item_name, content, title=title)
    elif request.method == 'POST':
        if 'login' in request.form:
            if hasattr(request, '_login_messages'):
                for msg in request._login_messages:
                    request.theme.add_msg(msg, "error")
        request.theme.render_content(item_name, title=title)

