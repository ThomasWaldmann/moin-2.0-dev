# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - index action

    @copyright: 2009 MoinMoin:ThomasWaldmann,
                2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""
from MoinMoin.items import Item

def execute(item_name, request):
    item = Item.create(request, item_name)
    content = item.do_index()
    return content
