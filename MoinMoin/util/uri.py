"""
MoinMoin - Generic? URI implementation

Implements the generic URI form defined by RFC 3986.

TODO: Invent a unicode-aware class for wiki links

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import re
import urllib

class Uri(object):
    rules = r"""
    ^
    (
        (?P<scheme>
            [^:/?\#]+
        )
        :
    )?
    (
        //
        (?P<authority>
            [^/?\#]*
        )
    )?
    (?P<path>
        [^?\#]+
    )?
    (
        \?
        (?P<query>
            [^\#]*
        )
    )?
    (
        \#
        (?P<fragment>
            .*
        )
    )?
    """
    _re = re.compile(rules, re.X)

    def __init__(self, uri=None,
            scheme=None, authority=None, path=None, query=None, fragment=None):

        uri_scheme = uri_authority = uri_path = uri_query = uri_fragment = None

        if uri:
            match = self._re.match(uri)

            if match:
                uri_scheme = match.group('scheme')
                if uri_scheme is not None:
                    # Common sense, scheme is lowercase
                    uri_scheme = uri_scheme.lower()

                uri_authority = match.group('authority')
                if uri_authority is not None:
                    uri_authority = urllib.unquote(uri_authority)

                uri_path = match.group('path')
                if uri_path is not None:
                    uri_path = urllib.unquote(uri_path)

                uri_query = match.group('query')
                if uri_query is not None:
                    uri_query = urllib.unquote(uri_query)

                uri_fragment = match.group('fragment')
                if uri_fragment is not None:
                    uri_fragment = urllib.unquote(uri_fragment)

        self.scheme = scheme or uri_scheme
        self.authority = authority or uri_authority
        self.path = path or uri_path
        self.query = query or uri_query
        self.fragment = fragment or uri_fragment

    def __setattr__(self, key, value):
        if key in ('scheme', 'authority', 'path', 'query', 'fragment'):
            if value is not None:
                value = str(value)
        super(Uri, self).__setattr__(key, value)

    def __str__(self):
        ret = []
        if self.scheme:
            ret.extend((self.scheme, ':'))
        if self.authority is not None:
            ret.extend(('//', urllib.quote(self.authority, "!$&'()@*+,;=:")))
        if self.path is not None:
            ret.append(urllib.quote(self.path, "!$&'()@*+,;=:/"))
        if self.query is not None:
            ret.extend(('?', urllib.quote(self.query, "!$&'()@*+,;=:/?")))
        if self.fragment is not None:
            ret.extend(('#', urllib.quote(self.fragment, "!$&'()@*+,;=:/?")))
        return ''.join(ret)
