"""
MoinMoin - Generic? IRI implementation

Implements the generic IRI form as defined by RFC 3987.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import re
import urllib

class Iri(object):
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

    def __init__(self, iri=None,
            scheme=None, authority=None, path=None, query=None, fragment=None):

        if iri:
            match = self._re.match(iri)

            if match:
                if scheme is None:
                    scheme = match.group('scheme')
                    if scheme is not None:
                        scheme = scheme.lower()

                if authority is None:
                    authority = match.group('authority')
                    if authority is not None:
                        authority = urllib.unquote(authority)

                if path is None:
                    path = match.group('path')
                    if path is not None:
                        path = urllib.unquote(path)

                if query is None:
                    query = match.group('query')
                    if query is not None:
                        query = urllib.unquote(query)

                if fragment is None:
                    fragment = match.group('fragment')
                    if fragment is not None:
                        fragment = urllib.unquote(fragment)

        self.scheme = scheme
        self.authority = authority
        self.path = path
        self.query = query
        self.fragment = fragment
