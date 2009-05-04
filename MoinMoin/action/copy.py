# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Action to copy item

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.items import Manager

def execute(item_name, request):
    item = Manager(request, item_name).get_item()
    if request.method == 'GET':
        request.setContentLanguage(request.lang)
        request.theme.send_title(item_name, pagename=item_name)
        request.write(item.do_copy())
        request.theme.send_footer(item_name)
        request.theme.send_closing_html()
    elif request.method == 'POST':
        cancelled = 'button_cancel' in request.form
        if not cancelled:
            item.copy()
        new_name = request.form.get('target')
        request.http_redirect(request.href(new_name)) # show new item
