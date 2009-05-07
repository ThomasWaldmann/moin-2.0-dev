# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - modify an item (or creating for given mimetype)

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.items import Manager

def execute(item_name, request):
    mimetype = request.values.get('mimetype', 'text/plain')
    # TODO add evaluation of template arg
    item = Manager(request, item_name, mimetype=mimetype).get_item()
    if request.method == 'GET':
        request.setContentLanguage(request.lang)
        request.theme.send_title(item_name, pagename=item_name)
        request.write(item.do_modify())
        request.theme.send_footer(item_name)
        request.theme.send_closing_html()
    elif request.method == 'POST':
        cancelled = 'button_cancel' in request.form
        if not cancelled:
            item.modify()
        request.http_redirect(request.href(item_name)) # show item
