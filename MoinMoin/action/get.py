# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Action to save item content to a file download

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.items import Item

def execute(item_name, request):
    item = Item.create(request, item_name, rev_no=request.rev)
    item.do_get()
