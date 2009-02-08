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

    quote_authority_rules = (
        # Not correct, but we have anything in authority
        (ord('@'), ord('@')),
        (ord(':'), ord(':')),
    ) + quote_rules

    quote_path_rules = (
        (ord('@'), ord('@')),
        (ord(':'), ord(':')),
        (ord('/'), ord('/')),
    ) + quote_rules

    quote_query_rules = (
        (ord('@'), ord('@')),
        (ord(':'), ord(':')),
        (ord('/'), ord('/')),
        (ord('?'), ord('?')),
    ) + quote_rules + (
        (  0xE000,   0xF8FF),
        ( 0xF0000,  0xFFFFD),
        (0x100000, 0x10FFFD),
    )

    quote_fragment_rules = (
        (ord('@'), ord('@')),
        (ord(':'), ord(':')),
        (ord('/'), ord('/')),
        (ord('?'), ord('?')),
    ) + quote_rules

    unquote_rules = r"(%[0-9a-fA-F]{2})+"

    _overall_re = re.compile(overall_rules, re.X)
    _unquote_re = re.compile(unquote_rules)

    def __init__(self, iri=None,
            scheme=None, authority=None, path=None, query=None, fragment=None):
        """
        @param iri A full IRI in unicode
        @param scheme Scheme part of the IRI, overrides the same part of the IRI.
        @param authority Authority part of the IRI, overrides the same part of the IRI.
        @param path Path part of the IRI, overrides the same part of the IRI.
        @param query Query part of the IRI, overrides the same part of the IRI.
        @param fragment Fragment part of the IRI, overrides the same part of the IRI.
        """

        self.scheme = self.authority = self.path = self.query = self.fragment = None

        if iri:
            self._parse(iri)

        if scheme is not None:
            self.scheme = scheme
        if authority is not None:
            self.authority = authority
        if path is not None:
            self.path = path
        if query is not None:
            self.query = query
        if fragment is not None:
            self.fragment = fragment

    def __unicode__(self):
        ret = []

        if self.scheme:
            ret.extend((self.scheme, u':'))

        authority = self.authority_fullquoted
        if authority is not None:
            ret.extend((u'//', authority))

        path = self.path_fullquoted
        if path is not None:
            ret.append(path)

        query = self.query_fullquoted
        if query is not None:
            ret.extend((u'?', query))

        fragment = self.fragment_fullquoted
        if fragment is not None:
            ret.extend((u'#', fragment))

        return u''.join(ret)

    def _parse(self, iri):
        match = self._overall_re.match(unicode(iri))

        if not match:
            raise ValueError('Input does not look like an IRI')

        scheme = match.group('scheme')
        if scheme is not None:
            self.scheme = scheme.lower()

        authority = match.group('authority')
        if authority is not None:
            self._authority = self._unquote(authority)

        path = match.group('path')
        if path is not None:
            self._path = self._unquote(path)

        query = match.group('query')
        if query is not None:
            self._query = self._unquote(query)

        fragment = match.group('fragment')
        if fragment is not None:
            self._fragment = self._unquote(fragment)

    def _quote(self, s, rules, requote=False):
        ret = []

        for i in s:
            c = ord(i)

            for rule in rules:
                if c >= rule[0] and c <= rule[1] or requote and i == u'%':
                    ret.append(i)
                    break
            else:
                ret.extend((u'%%%02X' % ord(a) for a in i.encode('utf-8')))

        return u''.join(ret)

    def _unquote(self, s):
        """
        Unquotes percent-encoded strings.

        @param s Input string
        @return Tuple of full decoded and minimal quoted string
        """
        ret1 = []
        ret2 = []
        pos = 0
        for match in self._unquote_re.finditer(s):
            # Handle leading text
            t = s[pos:match.start()]
            ret1.append(t)
            ret2.append(t)
            pos = match.end()

            part = []
            for item in match.group().split(u'%')[1:]:
                part.append(chr(int(item, 16)))
            ret1.append(''.join(part).decode('utf-8', 'replace'))
            # TODO: Reencode % and illegal sequences
            ret2.append(''.join(part).decode('utf-8'))

        # Handle trailing text
        t = s[pos:]
        ret1.append(t)
        ret2.append(t)
        return u''.join(ret1), u''.join(ret2)

    def __get_all_fullquoted(self, value, rules):
        """
        Provide full quoted form of the value.

        @param value Internal value
        @return Full quoted form of the value
        """
        if value[1] is not None:
            return self._quote(value[1], rules, True)
        if value[0] is not None:
            return self._quote(value[0], rules)

    def __get_all_quoted(self, value):
        """
        Provide minimal quoted form of the value.

        @param value Internal value
        @return Minimal quoted form of the value
        """
        if value[1] is not None:
            return value[1]
        if value[0] is not None:
            return value[0].replace(u'%', u'%25')

    def __del_authority(self):
        del self._authority
    def __get_authority(self):
        return self._authority[0]
    def __set_authority(self, value):
        self._authority = value, None
    authority = property(__get_authority, __set_authority, __del_authority,
            "Unquoted form of the authority part of the IRI.")

    @property
    def authority_fullquoted(self):
        "Full quoted form of the authority part of the IRI."
        return self.__get_all_fullquoted(self._authority, self.quote_authority_rules)

    @property
    def authority_quoted(self):
        "Minimal quoted form of the authority part of the IRI."
        return self.__get_all_quoted(self._authority)

    def __del_path(self):
        del self._path
    def __get_path(self):
        return self._path[0]
    def __set_path(self, value):
        self._path = value, None
    path = property(__get_path, __set_path, __del_path,
            "Unquoted form of the path part of the IRI.")

    @property
    def path_fullquoted(self):
        "Full quoted form of the path part of the IRI."
        return self.__get_all_fullquoted(self._path, self.quote_path_rules)

    @property
    def path_quoted(self):
        "Minimal quoted form of the path part of the IRI."
        return self.__get_all_quoted(self._path)

    def __del_query(self):
        del self._query
    def __get_query(self):
        return self._query[0]
    def __set_query(self, value):
        self._query = value, None
    query = property(__get_query, __set_query, __del_query,
            "Unquoted form of the query part of the IRI.")

    @property
    def query_fullquoted(self):
        "Full quoted form of the query part of the IRI."
        return self.__get_all_fullquoted(self._query, self.quote_query_rules)

    @property
    def query_quoted(self):
        "Minimal quoted form of the query part of the IRI."
        return self.__get_all_quoted(self._query)

    def __del_fragment(self):
        del self._fragment
    def __get_fragment(self):
        return self._fragment[0]
    def __set_fragment(self, value):
        self._fragment = value, None
    fragment = property(__get_fragment, __set_fragment, __del_fragment,
            "Unquoted form of the fragment part of the IRI.")

    @property
    def fragment_fullquoted(self):
        "Full quoted form of the fragment part of the IRI."
        return self.__get_all_fullquoted(self._fragment, self.quote_fragment_rules)

    @property
    def fragment_quoted(self):
        "Minimal quoted form of the fragment part of the IRI."
        return self.__get_all_quoted(self._fragment)
