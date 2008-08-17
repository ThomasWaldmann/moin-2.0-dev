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

    def __init__(self, url=None,
            scheme=None, authority=None, path=None, query=None, fragment=None):

        if url:
            match = self._re.match(url)

            if match:
                scheme = match.group('scheme')
                if scheme is not None:
                    # Common sense, scheme is lowercase
                    scheme = scheme.lower()

                authority = match.group('authority')
                if authority is not None:
                    authority = urllib.unquote(authority)

                path = match.group('path')
                if path is not None:
                    path = urllib.unquote(path)

                query = match.group('query')
                if query is not None:
                    query = urllib.unquote(query)

                fragment = match.group('fragment')
                if fragment is not None:
                    fragment = urllib.unquote(fragment)

        self.scheme = scheme
        self.authority = authority
        self.path = path
        self.query = query
        self.fragment = fragment

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
