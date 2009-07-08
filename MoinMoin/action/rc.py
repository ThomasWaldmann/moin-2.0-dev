# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - rc action

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

def execute(item_name, request):
    history = request.storage.history()
    template = request.theme.env.get_template('rc.html')
    content = template.render(gettext=request.getText,
                              history=history,
                             )
    request.theme.render_content(item_name, content)

