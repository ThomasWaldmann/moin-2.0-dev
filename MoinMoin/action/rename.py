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
        request.headers.add('Content-Type', 'text/html; charset=utf-8')
        request.write(content)
    elif request.method == 'POST':
        cancelled = 'button_cancel' in request.form
        if not cancelled:
            target = request.form.get('target')
            comment = request.form.get('comment')
            item.rename(target, comment)
            redirect_to = target
        else:
            redirect_to = item_name
        request.http_redirect(request.href(redirect_to))

