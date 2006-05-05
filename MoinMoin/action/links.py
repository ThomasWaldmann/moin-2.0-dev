# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - "links" action

    Generate a link database like MeatBall:LinkDatabase.

    @copyright: 2001 by J�rgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import config, wikiutil
from MoinMoin.util import MoinMoinNoFooter


def execute(pagename, request):
    _ = request.getText
    form = request.form

    # get the MIME type
    if form.has_key('mimetype'):
        mimetype = form['mimetype'][0]
    else:
        mimetype = "text/html"

    request.http_headers(["Content-Type: %s; charset=%s" % (mimetype,config.charset)])

    if mimetype == "text/html":
        request.theme.send_title(_('Full Link List for "%s"') % request.cfg.sitename)
        request.write('<pre>')

    # Get page dict readable by current user
    pages = request.rootpage.getPageDict()
    pagelist = pages.keys()
    pagelist.sort()

    for name in pagelist:
        if mimetype == "text/html":
            request.write(pages[name].link_to(request))
        else:
            _emit(request, name)
        for link in pages[name].getPageLinks(request):
            request.write(" ")
            if mimetype == "text/html":
                if link in pages:
                    request.write(pages[link].link_to(request))
                else:
                    _emit(request, link)
            else:
                _emit(request, link)
        request.write('\n')

    if mimetype == "text/html":
        request.write('</pre>')
        request.theme.send_footer(pagename)
    else:
        raise MoinMoinNoFooter

def _emit(request, pagename):
    """ Send pagename, encode it if it contains spaces
    """
    request.write(wikiutil.quoteWikinameURL(pagename))

