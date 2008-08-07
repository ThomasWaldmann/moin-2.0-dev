"""
MoinMoin - Generic? URI implementation

Implements the generic URI form defined by RFC 3986.

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

    def __init__(self, input=None,
            scheme=None, authority=None, path=None, query=None, fragment=None):
        self.scheme = scheme
        self.authority = authority
        self.path = path
        self.query = query
        self.fragment = fragment

        if input:
            match = self._re.match(input)

            if match:
                scheme = match.group('scheme')
                if scheme is not None:
                    # Common sense, scheme is lowercase
                    self.scheme = scheme.lower()

                authority = match.group('authority')
                if authority is not None:
                    self.authority = urllib.unquote(authority)

                path = match.group('path')
                if path is not None:
                    self.path = urllib.unquote(path)

                query = match.group('query')
                if query is not None:
                    self.query = urllib.unquote(query)

                fragment = match.group('fragment')
                if fragment is not None:
                    self.fragment = urllib.unquote(fragment)

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
