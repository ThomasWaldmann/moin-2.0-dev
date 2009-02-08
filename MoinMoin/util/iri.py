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

    _overall_re = re.compile(overall_rules, re.X)

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

        self.scheme = self._authority = self._path = self._query = self._fragment = None

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

        authority = self.authority
        if authority is not None:
            ret.extend((u'//', authority.fullquoted))

        path = self.path
        if path is not None:
            ret.append(path.fullquoted)

        query = self.query
        if query is not None:
            ret.extend((u'?', query.fullquoted))

        fragment = self.fragment
        if fragment is not None:
            ret.extend((u'#', fragment.fullquoted))

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
            self._authority = IriAuthority(authority, True)

        path = match.group('path')
        if path is not None:
            self._path = IriPath(path, True)

        query = match.group('query')
        if query is not None:
            self._query = IriQuery(query, True)

        fragment = match.group('fragment')
        if fragment is not None:
            self._fragment = IriFragment(fragment, True)

    def __del_authority(self):
        self._authority = None
    def __get_authority(self):
        return self._authority
    def __set_authority(self, value):
        self._authority = IriAuthority(value)
    authority = property(__get_authority, __set_authority, __del_authority,
            """
            Authority part of the IRI.

            Complete unquoted unicode string. It may include replacement
            characters.
            """)

    @property
    def authority_fullquoted(self):
        """
        Full quoted form of the authority part of the IRI.

        All characters which are illegal in the authority part are encoded.
        Used to generate the full URI.
        """
        if self._authority is not None:
            return self._authority.fullquoted

    @property
    def authority_quoted(self):
        """
        Minimal quoted form of the authority part of the IRI.

        Only '%' and illegal UTF-8 sequences are encoded. Primarily used to
        have a one-to-one mapping with non-UTF-8 URIs.
        """
        if self._authority is not None:
            return self._authority.quoted

    def __del_path(self):
        self._path = None
    def __get_path(self):
        return self._path
    def __set_path(self, value):
        self._path = IriPath(value)
    path = property(__get_path, __set_path, __del_path,
            """
            Path part of the IRI.

            Complete unquoted unicode string. It may include replacement
            characters.
            """)

    @property
    def path_fullquoted(self):
        """
        Full quoted form of the path part of the IRI.

        All characters which are illegal in the path part are encoded.
        Used to generate the full URI.
        """
        if self._path is not None:
            return self._path.fullquoted

    @property
    def path_quoted(self):
        """
        Minimal quoted form of the path part of the IRI.

        Only '%' and illegal UTF-8 sequences are encoded. Primarily used to
        have a one-to-one mapping with non-UTF-8 URIs.
        """
        if self._path is not None:
            return self._path.quoted

    def __del_query(self):
        self._query = None
    def __get_query(self):
        return self._query
    def __set_query(self, value):
        self._query = IriQuery(value)
    query = property(__get_query, __set_query, __del_query,
            """
            Query part of the IRI.

            Complete unquoted unicode string. It may include replacement
            characters.
            """)

    @property
    def query_fullquoted(self):
        """
        Full quoted form of the query part of the IRI.

        All characters which are illegal in the query part are encoded.
        Used to generate the full URI.
        """
        if self._query is not None:
            return self._query.fullquoted

    @property
    def query_quoted(self):
        """
        Minimal quoted form of the query part of the IRI.

        Only '%' and illegal UTF-8 sequences are encoded. Primarily used to
        have a one-to-one mapping with non-UTF-8 URIs.
        """
        if self._query is not None:
            return self._query.quoted

    def __del_fragment(self):
        self._fragment = None
    def __get_fragment(self):
        return self._fragment
    def __set_fragment(self, value):
        self._fragment = IriFragment(value)
    fragment = property(__get_fragment, __set_fragment, __del_fragment,
            """
            Fragment part of the IRI.

            Complete unquoted unicode string. It may include replacement
            characters.
            """)

    @property
    def fragment_fullquoted(self):
        """
        Full quoted form of the fragment part of the IRI.

        All characters which are illegal in the fragment part are encoded.
        Used to generate the full URI.
        """
        if self._fragment is not None:
            return self._fragment.fullquoted

    @property
    def fragment_quoted(self):
        """
        Minimal quoted form of the fragment part of the IRI.

        Only '%' and illegal UTF-8 sequences are encoded. Primarily used to
        have a one-to-one mapping with non-UTF-8 URIs.
        """
        if self._fragment is not None:
            return self._fragment.quoted

class _Value(unicode):
    __slots__ = '_quoted'

    # Rules for quoting parts of the IRI.
    # Each entry represents a range of unicode code points.
    quote_rules = (
        (ord(u'0'), ord(u'9')),
        (ord(u'A'), ord(u'Z')),
        (ord(u'a'), ord(u'z')),
        (ord(u'-'), ord(u'-')),
        (ord(u'.'), ord(u'.')),
        (ord(u'_'), ord(u'_')),
        (ord(u'~'), ord(u'~')),
        (ord(u'!'), ord(u'!')),
        (ord(u'$'), ord(u'$')),
        (ord(u'&'), ord(u'&')),
        (ord(u"'"), ord(u"'")),
        (ord(u'('), ord(u'(')),
        (ord(u')'), ord(u')')),
        (ord(u'*'), ord(u'*')),
        (ord(u'+'), ord(u'+')),
        (ord(u','), ord(u',')),
        (ord(u';'), ord(u';')),
        (ord(u'='), ord(u'=')),
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

    # Matches consecutive percent-encoded values
    unquote_rules = r"(%[0-9a-fA-F]{2})+"
    _unquote_re = re.compile(unquote_rules)

    def __new__(cls, input, quoted=False):
        if isinstance(input, cls):
            input_quoted = input._quoted
        elif quoted:
            input, input_quoted = cls._unquote(input)
        else:
            input_quoted = None

        ret = unicode.__new__(cls, input)
        unicode.__setattr__(ret, '_quoted', input_quoted)
        return ret

    @classmethod
    def _quote(cls, input, requote=False):
        """
        Quote all illegal characters.

        @param rules: List of unicode ranges
        @param requote: Input string is already quoted
        @return: Quoted string
        """
        ret = []

        for i in input:
            # Check if we have an already quoted string.
            if requote and i == u'%':
                ret.append(i)
                continue

            # Check if the current character matches any of the given ranges
            c = ord(i)
            for rule in cls.quote_rules:
                if c >= rule[0] and c <= rule[1]:
                    ret.append(i)
                    break

            else:
                # Percent-encode illegal characters
                ret.extend((u'%%%02X' % ord(a) for a in i.encode('utf-8')))

        return u''.join(ret)

    @classmethod
    def _unquote(cls, s):
        """
        Unquotes percent-encoded strings.

        @param s: Input string
        @return: Tuple of full decoded and minimal quoted string
        """
        ret1 = []
        ret2 = []
        pos = 0

        for match in cls._unquote_re.finditer(s):
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

    @property
    def fullquoted(self):
        if self._quoted is not None:
            return self._quote(self._quoted, True)
        return self._quote(self)

    @property
    def quoted(self):
        if self._quoted is not None:
            return self._quoted
        return self.replace(u'%', u'%25')

class IriAuthority(_Value):
    quote_rules = (
        # Not correct, but we have anything in authority
        (ord(u'@'), ord(u'@')),
        (ord(u':'), ord(u':')),
    ) + _Value.quote_rules

class IriPath(_Value):
    quote_rules = (
        (ord(u'@'), ord(u'@')),
        (ord(u':'), ord(u':')),
        (ord(u'/'), ord(u'/')),
    ) + _Value.quote_rules

class IriQuery(_Value):
    quote_rules = (
        (ord(u'@'), ord(u'@')),
        (ord(u':'), ord(u':')),
        (ord(u'/'), ord(u'/')),
        (ord(u'?'), ord(u'?')),
    ) + _Value.quote_rules + (
        (  0xE000,   0xF8FF),
        ( 0xF0000,  0xFFFFD),
        (0x100000, 0x10FFFD),
    )

class IriFragment(_Value):
    quote_rules = (
        (ord(u'@'), ord(u'@')),
        (ord(u':'), ord(u':')),
        (ord(u'/'), ord(u'/')),
        (ord(u'?'), ord(u'?')),
    ) + _Value.quote_rules
