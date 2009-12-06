# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - PageSize Macro

    @copyright: 2002 Juergen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

Dependencies = ["pages"]

from MoinMoin.Page import Page

def macro_PageSize(macro):
    request = macro.request
    if request.isSpiderAgent: # reduce bot cpu usage
        return ''

    # get sizes of all pages and sort them
    sizes = [(Page(request, name).size(), name)
             for name in request.rootpage.getPageList()]
    sizes.sort()
    sizes.reverse()

    # format list
    result = []
    result.append(macro.formatter.number_list(1))
    for size, pagename in sizes:
        result.append(macro.formatter.listitem(1))
        result.append(macro.formatter.code(1))
        result.append(("%6d" % size).replace(" ", "&nbsp;") + " ")
        result.append(macro.formatter.code(0))
        result.append(macro.formatter.pagelink(1, pagename, generated=1))
        result.append(macro.formatter.text(pagename))
        result.append(macro.formatter.pagelink(0, pagename))
        result.append(macro.formatter.listitem(0))
    result.append(macro.formatter.number_list(0))

    return ''.join(result)

