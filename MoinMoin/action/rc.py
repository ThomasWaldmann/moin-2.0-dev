# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - rc action

    TODO: acl checks were removed, have to be done on storage layer

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""
from MoinMoin.items import Item

def execute(item_name, request):
    # just get some binary, non-existing item, so we have one:
    item = Item.create(request, '$$$rc$$$', mimetype='rc')
    history = request.cfg.data_backend.history()
    template = item.env.get_template('rc.html')
    content = template.render(gettext=request.getText,
                              item_name=item.item_name,
                              history=history,
                             )
    request.theme.render_content(item_name, content)

