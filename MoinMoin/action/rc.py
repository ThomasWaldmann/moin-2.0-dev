# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - rc action

    @copyright: 2009 MoinMoin:ThomasWaldmann,
                2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""

def execute(item_name, request):
    # XXX we want to be able to get global recent changes when visiting
    # hostname/?do=rc, but we get item_name = cfg.page_front_page for this
    if item_name == request.cfg.page_front_page:
        item_name = u''
    # TODO: No fake-metadata anymore, fix this
    history = request.storage.history(item_name=item_name)
    return request.theme.render('rc.html', 
                                history=history,
                                )
