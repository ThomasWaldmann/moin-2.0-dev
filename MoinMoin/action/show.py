# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - show action

    TODO: acl checks were removed, have to be done on storage layer

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""
from MoinMoin.items import Manager

def execute(item_name, request):
    if request.rev is None:
        rev_no = -1
    else:
        rev_no = request.rev
    mimetype = request.values.get('mimetype')

    # Use user interface language for this generated page
    request.setContentLanguage(request.lang)
    request.theme.send_title(item_name, pagename=item_name)

    item = Manager(request, item_name, mimetype=mimetype, rev_no=rev_no).get_item()
    request.write(item.do_show())

    request.theme.send_footer(item_name)
    request.theme.send_closing_html()
