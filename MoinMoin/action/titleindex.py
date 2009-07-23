# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - "titleindex" action

    This action generates a plain list of pages, so that other wikis
    can implement http://www.usemod.com/cgi-bin/mb.pl?MetaWiki more
    easily.

    @copyright: 2001 Juergen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import config, util


def execute(pagename, request):
    mimetype = request.values.get('mimetype', "text/plain")
    request.mimetype = mimetype

    item_names = [i.name for i in request.rootitem.list_items()]
    item_names.sort()

    if mimetype == "text/xml":
        request.write('<?xml version="1.0" encoding="%s"?>\r\n' % (config.charset, ))
        request.write('<TitleIndex>\r\n')
        for name in item_names:
            request.write('  <Title>%s</Title>\r\n' % (util.TranslateCDATA(name), ))
        request.write('</TitleIndex>\r\n')
    else:
        for name in item_names:
            request.write(name + '\r\n')

