# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - show action

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""
from MoinMoin.items import Item

def execute(item_name, request):
    rev_no = request.rev or -1
    mimetype = request.values.get('mimetype')

    item = Item.create(request, item_name, mimetype=mimetype, rev_no=rev_no)
    content = item.do_show()
    request.theme.render_content(item_name, content)
