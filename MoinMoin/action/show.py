# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - show action

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""
from MoinMoin.items import Item

def execute(item_name, request):
    mimetype = request.values.get('mimetype')
    item = Item.create(request, item_name, mimetype=mimetype, rev_no=request.rev)
    content = item.do_show()
    request.headers.add('Content-Type', 'text/html; charset=utf-8')
    # Have to do this because Item renders itself show.html
    return content

