# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - rc action

    TODO: acl checks were removed, have to be done on storage layer

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""
from MoinMoin.items import Manager

def execute(item_name, request):
    # Use user interface language for this generated page
    request.setContentLanguage(request.lang)
    request.theme.send_title(item_name, pagename=item_name)

    # just get some binary, non-existing item, so we have one:
    item = Manager(request, '$$$rc$$$', mimetype='rc').get_item()
    history = request.cfg.data_backend.history()
    template = item.env.get_template('rc.html')
    content = template.render(gettext=request.getText,
                              item_name=item.item_name,
                              history=history,
                             )
    request.write(content)
    request.theme.send_footer(item_name)
    request.theme.send_closing_html()



