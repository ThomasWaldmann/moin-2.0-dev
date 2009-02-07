"""
MoinMoin - Generic? IRI implementation

Implements the generic IRI form as defined in RFC 3987.

@copyright: 2008,2009 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import re

class Iri(object):
    overall_rules = r"""
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

    quote_rules = (
        (ord('0'), ord('9')),
        (ord('A'), ord('Z')),
        (ord('a'), ord('z')),
        (ord('-'), ord('-')),
        (ord('.'), ord('.')),
        (ord('_'), ord('_')),
        (ord('~'), ord('~')),
        (ord('!'), ord('!')),
        (ord('$'), ord('$')),
        (ord('&'), ord('&')),
        (ord("'"), ord("'")),
        (ord('('), ord('(')),
        (ord(')'), ord(')')),
        (ord('*'), ord('*')),
        (ord('+'), ord('+')),
        (ord(','), ord(',')),
        (ord(';'), ord(';')),
        (ord('='), ord('=')),
        (   0xA0,  0xD7FF),
        ( 0xF900,  0xFDCF),
        ( 0xFDF0,  0xFFEF),
        (0x10000, 0x1FFFD),
        (0x20000, 0x2FFFD),
        (0x30000, 0x3FFFD),
        (0x40000, 0x4FFFD),
        (0x50000, 0x5FFFD),
        (0x60000, 0x6FFFD),
        (0x70000, 0x7FFFD),
        (0x80000, 0x8FFFD),
        (0x90000, 0x9FFFD),
        (0xA0000, 0xAFFFD),
        (0xB0000, 0xBFFFD),
        (0xC0000, 0xCFFFD),
        (0xD0000, 0xDFFFD),
        (0xE1000, 0xEFFFD),
    )

    quote_authority_rules = quote_rules + (
        # Not correct, but we have anything in authority
        (ord('@'), ord('@')),
        (ord(':'), ord(':')),
    )

    quote_path_rules = quote_rules + (
        (ord('@'), ord('@')),
        (ord(':'), ord(':')),
        (ord('/'), ord('/')),
    )

    quote_query_rules = quote_rules + (
        (ord('@'), ord('@')),
        (ord(':'), ord(':')),
        (ord('/'), ord('/')),
        (ord('?'), ord('?')),
        (  0xE000,   0xF8FF),
        ( 0xF0000,  0xFFFFD),
        (0x100000, 0x10FFFD),
    )

    quote_fragment_rules = quote_rules + (
        (ord('@'), ord('@')),
        (ord(':'), ord(':')),
        (ord('/'), ord('/')),
        (ord('?'), ord('?')),
    )

    unquote_rules = r"(%[0-9a-fA-F]{2})+"

    _overall_re = re.compile(overall_rules, re.X)
    _unquote_re = re.compile(unquote_rules)

    def __init__(self, iri=None,
            scheme=None, authority=None, path=None, query=None, fragment=None):

        if iri:
            match = self._overall_re.match(unicode(iri))

            if match:
                if scheme is None:
                    scheme = match.group('scheme')
                    if scheme is not None:
                        scheme = scheme.lower()

                if authority is None:
                    authority = match.group('authority')
                    if authority is not None:
                        authority, authority_q = self._unquote(authority)

                if path is None:
                    path = match.group('path')
                    if path is not None:
                        path, path_q = self._unquote(path)

                if query is None:
                    query = match.group('query')
                    if query is not None:
                        query, query_q = self._unquote(query)

                if fragment is None:
                    fragment = match.group('fragment')
                    if fragment is not None:
                        fragment, fragment_q = self._unquote(fragment)

        self.scheme = scheme
        self.authority = authority
        self.path = path
        self.query = query
        self.fragment = fragment

    def __unicode__(self):
        ret = []
        if self.scheme:
            ret.extend((self.scheme, ':'))
        if self.authority is not None:
            ret.extend(('//', self._quote_authority(self.authority)))
        if self.path is not None:
            ret.append(self._quote_path(self.path))
        if self.query is not None:
            ret.extend(('?', self._quote_query(self.query)))
        if self.fragment is not None:
            ret.extend(('#', self._quote_fragment(self.fragment)))
        return ''.join(ret)

    def _quote(self, s, rules):
        ret = []

        for i in s:
            c = ord(i)

            for rule in rules:
                if c >= rule[0] and c <= rule[1]:
                    ret.append(i)
                    break
            else:
                ret.extend(('%%%02X' % ord(a) for a in i.encode('utf-8')))

        return u''.join(ret)

    def _quote_authority(self, s):
        return self._quote(s, self.quote_authority_rules)

    def _quote_path(self, s):
        return self._quote(s, self.quote_path_rules)

    def _quote_query(self, s):
        return self._quote(s, self.quote_query_rules)

    def _quote_fragment(self, s):
        return self._quote(s, self.quote_fragment_rules)

    def _unquote_full_repl(self, match):
        ret = []
        for item in s.split('%')[1:]:
            ret.append(chr(int(item, 16)))
        return ''.join(ret).decode('utf-8')

    def _unquote_minimal_repl(self, match):
        ret = []
        for item in s.split('%')[1:]:
            ret.append(chr(int(item, 16)))
        # TODO: Reencode % and illegal sequences
        return ''.join(ret).decode('utf-8')

    def _unquote(self, s):
        # TODO: call re only once (using split?)
        r1 = self._unquote_re.sub(self._unquote_full_repl, s)
        r2 = self._unquote_re.sub(self._unquote_minimal_repl, s)
        return r1, r2
