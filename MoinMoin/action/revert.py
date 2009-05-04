# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Action to revert an item to a previous revision

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.items import Manager

def execute(item_name, request):
    if request.rev is None:
        rev_no = -1
    else:
        rev_no = request.rev
    item = Manager(request, item_name, rev_no=rev_no).get_item()
    if request.method == 'GET':
        request.setContentLanguage(request.lang)
        request.theme.send_title(item_name, pagename=item_name)
        request.write(item.do_revert())
        request.theme.send_footer(item_name)
        request.theme.send_closing_html()
    elif request.method == 'POST':
        cancelled = 'button_cancel' in request.form
        if not cancelled:
            item.revert()
        request.http_redirect(request.href(item_name)) # show item

