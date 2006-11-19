"""
    MoinMoin - WSGI application

    @copyright: 2005 by Anakim Border <akborder@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.request import WSGI

def moinmoinApp(environ, start_response):
    request = WSGI.Request(environ)
    request.run()
    start_response(request.status, request.headers)
    return [request.output()]
