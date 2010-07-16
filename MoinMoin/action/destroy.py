# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Action to destroy an item (or a revision)

    "destroy" means that the complete item (or a single revision of it)
    will be unrecoverably gone forever. The storage layer checks for the
    'destroy' permission, make sure only highly trusted and responsible
    people have that permission.

    @copyright: 2009 MoinMoin:ThomasWaldmann
                2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.items import Item

def execute(item_name, request):
    item = Item.create(request, item_name, rev_no=request.rev)
    if request.method == 'GET':
        content = item.do_destroy()
        request.theme.render_content(item_name, content)
    elif request.method == 'POST':
        cancelled = 'button_cancel' in request.form
        if not cancelled:
            item.destroy()
        request.http_redirect(request.href(item_name)) # show item

