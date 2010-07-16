# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - modify an item (or creating for given mimetype)

    @copyright: 2009 MoinMoin:ThomasWaldmann,
                2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.items import Item

def execute(item_name, request):
    mimetype = request.values.get('mimetype', 'text/plain')
    template_name = request.values.get('template')
    item = Item.create(request, item_name, mimetype=mimetype)
    if request.method == 'GET':
        content = item.do_modify(template_name)
        return content
    elif request.method == 'POST':
        cancelled = 'button_cancel' in request.form
        if not cancelled:
            item.modify()
        if not mimetype in ('application/x-twikidraw', 'application/x-anywikidraw'):
            # TwikiDraw and AnyWikiDraw can send more than one request
            # the follwowing line breaks it
            request.http_redirect(request.href(item_name)) # show item
