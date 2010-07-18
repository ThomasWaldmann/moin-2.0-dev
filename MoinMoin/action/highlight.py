# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Action to save item content to a file download

    @copyright: 2009 MoinMoin:ThomasWaldmann,
                2010 MoinMoin:ReimarBauer,
                2010 MoinMoin:DiogenesAugusto

    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.items import Item

def execute(item_name, request):
    if request.rev is None:
        rev_no = -1
    else:
        rev_no = request.rev
    item = Item.create(request, item_name, rev_no=rev_no)
    content = item.do_highlight()
    return content
