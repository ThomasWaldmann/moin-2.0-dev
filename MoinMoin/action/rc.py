# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - rc action

    TODO: acl checks were removed, have to be done on storage layer

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

def execute(item_name, request):
    history = request.cfg.data_backend.history()
    template = request.theme.env.get_template('rc.html')
    content = template.render(gettext=request.getText,
                              history=history,
                             )
    request.theme.render_content(item_name, content)

