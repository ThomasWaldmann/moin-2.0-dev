# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Action to delete an item (trashbin-like deletion)

    "delete" means that the complete item will be moved to the trashbin part
    of the wiki namespace (trashbin action lets you view and manage the
    trashbin).

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
        content = item.do_delete()
        request.theme.render_content(item_name, content)
    elif request.method == 'POST':
        cancelled = 'button_cancel' in request.form
        if not cancelled:
            comment = request.form.get('comment')
            item.delete(comment)
        request.http_redirect(request.href(item_name))

