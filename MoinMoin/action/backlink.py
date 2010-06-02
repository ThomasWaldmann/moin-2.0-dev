# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - backurl - removing backling magic from Themebase.title() and moving to actions

    @copyright: 2010 MoinMoin:DiogenesAugustoFernandesHerminio
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.Page import Page
from MoinMoin import wikiutil

def execute(page_name, request):
    print 'linkto:%s' % page_name
    url_query = {'do': 'fullsearch',
               'context': '180',
               'value': 'linkto:"%s"' % page_name,
    }
    # TODO: Fix convertion of " to %3A
    url = Page(request, page_name).url(request, querystr=url_query)
    #request.http_redirect(url, code=301)
    return
    