# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Action to revert an item to a previous revision

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.items import Item

def execute(item_name, request):
    if request.rev is None:
        rev_no = -1
    else:
        rev_no = request.rev
    item = Item.create(request, item_name, rev_no=rev_no)
    if request.method == 'GET':
        content = item.do_revert()
        request.theme.render_content(item_name, content)
    elif request.method == 'POST':
        cancelled = 'button_cancel' in request.form
        if not cancelled:
            item.revert()
        request.http_redirect(request.href(item_name)) # show item

