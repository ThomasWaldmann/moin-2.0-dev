# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - New slimmed down WSGI Request.

    @copyright: 2008-2008 MoinMoin:FlorianKrupicka
    @license: GNU GPL, see COPYING for details.
"""

from werkzeug import Request as RequestBase
from werkzeug import BaseResponse, ETagResponseMixin, \
                     CommonResponseDescriptorsMixin, WWWAuthenticateMixin
from werkzeug import Headers, Href

from MoinMoin import config


class ResponseBase(BaseResponse, ETagResponseMixin,
                   CommonResponseDescriptorsMixin,
                   WWWAuthenticateMixin):
    """
    similar to werkzeug.Response, but with ModifiedResponseStreamMixin
    """

class Request(ResponseBase, RequestBase):
    """ A full featured Request/Response object.

    To better distinguish incoming and outgoing data/headers,
    incoming versions are prefixed with 'in_' in contrast to
    original Werkzeug implementation.
    """
    default_mimetype = 'text/html'

    # get rid of some inherited descriptors
    headers = None

    def __init__(self, environ, populate_request=True, shallow=False):
        ResponseBase.__init__(self)
        RequestBase.__init__(self, environ, populate_request, shallow)
        def sort_key(item):
            """
            sort the query string key/values in the way we want:

            First: do=...
            Last:  target=...

            @param item: tuple (key, value)
            @return: sort key
            """
            return {
                'do': 0, # nice to have this first (but not technically required)
                'member': 99, # TWikiDraw searches a "file extension" at URL end
            }.get(item[0], 50) # 50 -> other stuff is somewhere in the middle
        self.href = Href(self.script_root or '/', config.charset, sort=True, key=sort_key)
        self.abs_href = Href(self.url_root, config.charset, sort=True, key=sort_key)
        self.headers = Headers([('Content-Type', 'text/html')])
        self.response = []
        self.status_code = 200

    # Note: we inherit a .stream attribute from RequestBase and this needs
    # to refer to the input stream because inherited functionality of werkzeug
    # base classes will access it as .stream.
    # TODO keep request and response separate, don't mix them together

