# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - 'What links here' action
    
    This action is used to get page_name and do
    a search using this parameter.

    @copyright: 2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.Page import Page
from MoinMoin import wikiutil


def execute(page_name, request):
    url_query = {'do': 'fullsearch',
                 'context': '180',
                 'value': 'linkto:"%s"' % page_name,
                }
    url = Page(request, page_name).url(request, querystr=url_query)
    request.http_redirect(url, code=302)
    
