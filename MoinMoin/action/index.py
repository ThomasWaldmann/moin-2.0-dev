# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - index action

    TODO: acl checks were removed, have to be done on storage layer

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""
from MoinMoin.items import Item

def execute(item_name, request):
    item = Item.create(request, item_name)
    content = item.do_index()
    request.theme.render_content(item_name, content)

