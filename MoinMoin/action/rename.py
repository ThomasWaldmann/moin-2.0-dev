# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Action to rename item

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.items import Item

def execute(item_name, request):
    item = Item.create(request, item_name)
    if request.method == 'GET':
        content = item.do_rename()
        request.theme.render_content(item_name, content)
    elif request.method == 'POST':
        cancelled = 'button_cancel' in request.form
        if not cancelled:
            item.rename()
        new_name = request.form.get('target')
        request.http_redirect(request.href(new_name)) # show new item
