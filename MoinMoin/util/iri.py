"""
MoinMoin - Generic? IRI implementation

Implements the generic IRI form as defined in RFC 3987.

@copyright: 2008,2009 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import codecs
import re


def _iriquote_replace(exc):
    if not isinstance(exc, UnicodeDecodeError):
        raise exc

    text = ''.join((u'%%%02X' % ord(a) for a in exc.object[exc.start:exc.end]))
    return text, exc.end

codecs.register_error('iriquote', _iriquote_replace)


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

    def __init__(self, iri=None, quoted=True,
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
            self._parse(iri, quoted)

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

    def __eq__(self, other):
        if isinstance(other, basestring):
            return unicode(self) == other

        if isinstance(other, Iri):
            if self.scheme != other.scheme: return False
            if self._authority != other._authority: return False
            if self._path != other._path: return False
            if self._query != other._query: return False
            if self._fragment != other._fragment: return False
            return True

        return NotImplemented

    def __ne__(self, other):
        ret = self.__eq__(other)
        if ret is NotImplemented:
            return ret
        return not ret

    def __unicode__(self):
        ret = []

        if self.scheme:
            ret.extend((self.scheme, u':'))

        authority = self._authority
        if authority is not None:
            ret.extend((u'//', authority.fullquoted))

        path = self._path
        if path is not None:
            ret.append(path.fullquoted)

        query = self._query
        if query is not None:
            ret.extend((u'?', query.fullquoted))

        fragment = self._fragment
        if fragment is not None:
            ret.extend((u'#', fragment.fullquoted))

        return u''.join(ret)

    def __add__(self, other):
        if isinstance(other, basestring):
            return self + Iri(other, False)

        if isinstance(other, Iri):
            if other.scheme is not None:
                scheme = other.scheme
                authority = other.authority
                path = other.path
                query = other.query
            else:
                if other.authority is not None:
                    authority = other.authority
                    path = other.path
                    query = other.query
                else:
                    if not other.path:
                        path = self.path
                        query = other.query or self.query
                    else:
                        path = self.path + other.path
                        query = other.query
                    authority = self.authority
                scheme = self.scheme

            return Iri(scheme=scheme, authority=authority, path=path,
                    query=query, fragment=other.fragment)

        return NotImplemented

    def _parse(self, iri, quoted):
        match = self._overall_re.match(unicode(iri))

        if not match:
            raise ValueError('Input does not look like an IRI')

        scheme = match.group('scheme')
        if scheme is not None:
            self.scheme = scheme.lower()

        authority = match.group('authority')
        if authority is not None:
            self._authority = IriAuthority(authority, quoted)

        path = match.group('path')
        if path is not None:
            self._path = IriPath(path, quoted)

        query = match.group('query')
        if query is not None:
            self._query = IriQuery(query, quoted)

        fragment = match.group('fragment')
        if fragment is not None:
            self._fragment = IriFragment(fragment, quoted)

    def __del_authority(self):
        self._authority = None
    def __get_authority(self):
        return self._authority
    def __set_authority(self, value):
        self._authority = IriAuthority(value, False)
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
        self._path = IriPath(value, False)
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
        self._query = IriQuery(value, False)
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
        self._fragment = IriFragment(value, False)
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

    # Rules for quoting parts of the IRI, also applies to URI.
    # Each entry represents a range of unicode code points.
    quote_rules_ascii = (
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
    )

    # Rules for quoting parts of the IRI.
    # Each entry represents a range of unicode code points.
    quote_rules_unicode = (
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

    def __new__(cls, input, quoted=True):
        # This object is immutable, no need to copy it
        if isinstance(input, cls):
            return input

        if quoted:
            input, input_quoted = cls._unquote(input)
        else:
            input_quoted = None

        ret = unicode.__new__(cls, input)
        unicode.__setattr__(ret, '_quoted', input_quoted)
        return ret

    @classmethod
    def _quote(cls, input, url=False, requote=False):
        """
        Quote all illegal characters.

        @param rules: List of unicode ranges
        @param requote: Input string is already quoted
        @return: Quoted string
        """
        ret = []

        rules = cls.quote_rules_ascii
        if not url:
            rules = rules + cls.quote_rules_unicode

        for i in input:
            # Check if we have an already quoted string.
            if requote and i == u'%':
                ret.append(i)
                continue

            # Check if the current character matches any of the given ranges
            c = ord(i)
            for rule in rules:
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
            ret2.append(''.join(part).replace('%', '%25').decode('utf-8', 'iriquote'))

        # Handle trailing text
        t = s[pos:]
        ret1.append(t)
        ret2.append(t)
        return u''.join(ret1), u''.join(ret2)

    @property
    def fullquoted(self):
        if self._quoted is not None:
            return self._quote(self._quoted, requote=True)
        return self._quote(self)

    @property
    def quoted(self):
        if self._quoted is not None:
            return self._quoted
        return self.replace(u'%', u'%25')

    @property
    def urlquoted(self):
        if self._quoted is not None:
            return self._quote(self._quoted, url=True, requote=True)
        return self._quote(self, url=True)

class _ValueAuthority(_Value):
    quote_rules_ascii = _Value.quote_rules_ascii + (
        # Not correct, but we have anything in authority
        (ord(u'@'), ord(u'@')),
        (ord(u':'), ord(u':')),
    )

class IriAuthority(object):
    authority_rules = r"""
    ^
    (
        (?P<userinfo>
            [^@]*
        )
        @
    )?
    (?P<host>
        .*?
    )
    (
        :
        (?P<port>
            \d*
        )
    )?
    $
    """

    _authority_re = re.compile(authority_rules, re.X)

    def __init__(self, iri_authority=None, quoted=True,
            userinfo=None, host=None, port=None):
        self._userinfo = self._host = self.port = None

        if iri_authority:
            if isinstance(iri_authority, IriAuthority):
                self._userinfo = iri_authority._userinfo
                self._host = iri_authority._host
                self.port = iri_authority.port
            else:
                self._parse(iri_authority, quoted)

        if userinfo is not None:
            self.userinfo = userinfo
        if host is not None:
            self.host = host
        if userinfo is not None:
            self.port = port

    def __eq__(self, other):
        if isinstance(other, basestring):
            return unicode(self) == other
        if isinstance(other, IriAuthority):
            return self._userinfo == other._userinfo and \
                    self._host == other._host and \
                    self.port == other.port
        return NotImplemented

    def __ne__(self, other):
        ret = self.__eq__(other)
        if ret is NotImplemented:
            return ret
        return not ret

    def __nonzero__(self):
        if self._userinfo or self._host or self.port:
            return True
        return False

    def __unicode__(self):
        return self.__get(self._userinfo, self._host)

    def __get(self, userinfo, host):
        ret = []

        if userinfo is not None:
            ret.extend((userinfo, u'@'))
        if host is not None:
            ret.append(host)
        if self.port is not None:
            ret.append(u':')
            if self.port:
                ret.append(unicode(self.port))

        return u''.join(ret)

    def _parse(self, iri_authority, quoted):
        match = self._authority_re.match(iri_authority)

        if not match:
            raise ValueError('Input does not look like an IRI authority')

        userinfo = match.group('userinfo')
        if userinfo is not None:
            self._userinfo = IriAuthorityUserinfo(userinfo, quoted)

        host = match.group('host')
        if host is not None:
            self._host = IriAuthorityHost(host, quoted)

        port = match.group('port')
        if port is not None:
            if port:
                self.port = int(port)
            else:
                self.port = 0

    @property
    def fullquoted(self):
        userinfo = self._userinfo and self._userinfo.fullquoted
        host = self._host and self._host.fullquoted
        return self.__get(userinfo, host)

    @property
    def quoted(self):
        userinfo = self._userinfo and self._userinfo.quoted
        host = self._host and self._host.quoted
        return self.__get(userinfo, host)

    @property
    def urlquoted(self):
        userinfo = self._userinfo and self._userinfo.urlquoted
        host = self._host and self._host.urlquoted
        return self.__get(userinfo, host)

    def __del_userinfo(self):
        self._userinfo = None
    def __get_userinfo(self):
        return self._userinfo
    def __set_userinfo(self, value):
        self._userinfo = IriAuthorityUserinfo(value, False)
    userinfo = property(__get_userinfo, __set_userinfo, __del_userinfo)

    @property
    def userinfo_fullquoted(self):
        if self._userinfo is not None:
            return self._userinfo.fullquoted

    @property
    def userinfo_quoted(self):
        if self._userinfo is not None:
            return self._userinfo.quoted

    def __del_host(self):
        self._host = None
    def __get_host(self):
        return self._host
    def __set_host(self, value):
        self._host = IriAuthorityHost(value, False)
    host = property(__get_host, __set_host, __del_host)

    @property
    def host_fullquoted(self):
        if self._host is not None:
            return self._host.fullquoted

    @property
    def host_quoted(self):
        if self._host is not None:
            return self._host.quoted

class IriAuthorityUserinfo(_ValueAuthority):
    pass

class IriAuthorityHost(_ValueAuthority):
    pass

class IriPath(object):
    __slots__ = '_list'

    def __init__(self, iri_path=None, quoted=True):
        self._list = []

        if iri_path:
            if isinstance(iri_path, IriPath):
                self._list = iri_path._list[:]
            elif isinstance(iri_path, (tuple, list)):
                self._list = [IriPathSegment(i, False) for i in iri_path]
            else:
                l = [IriPathSegment(i, quoted) for i in iri_path.split(u'/')]
                self._list = self._remove_dots(l)

    def __eq__(self, other):
        if isinstance(other, basestring):
            return unicode(self) == other
        if isinstance(other, IriPath):
            return self._list == other._list
        return NotImplemented

    def __ne__(self, other):
        ret = self.__eq__(other)
        if ret is NotImplemented:
            return ret
        return not ret

    def __getitem__(self, key):
        ret = self._list[key]
        if isinstance(key, slice):
            return self.__class__(ret)
        return ret

    def __len__(self):
        return len(self._list)

    def __nonzero__(self):
        return bool(self._list)

    def __add__(self, other):
        if isinstance(other, (basestring, list, tuple)):
            return self + IriPath(other, False)

        if isinstance(other, IriPath):
            if other._list and other._list[0] == '':
                segments = other._list
            else:
                segments = self._list[:-1] + other._list
            return IriPath(self._remove_dots(segments))

        return NotImplemented

    def __unicode__(self):
        return u'/'.join(self._list)

    def _remove_dots(self, segments):
        if not segments or segments[0] != '':
            return segments

        empty = segments[0]

        output = []
        remove = 0

        # Get reversed list with first (empty) element removed
        for i in segments[:0:-1]:
            if i == '.':
                if not output:
                    output.insert(0, empty)
            elif i == '..':
                if not output:
                    output.insert(0, empty)
                remove += 1
            else:
                if remove:
                    remove -= 1
                else:
                    output.insert(0, i)

        output.insert(0, empty)
        return output

    def extend(self, value):
        self._list.extend((IriPathSegment(i) for i in value))

    @property
    def fullquoted(self):
        return u'/'.join((i.fullquoted for i in self._list))

    @property
    def quoted(self):
        return u'/'.join((i.quoted for i in self._list))

    @property
    def urlquoted(self):
        return u'/'.join((i.urlquoted for i in self._list))

class IriPathSegment(_Value):
    quote_rules_ascii = _Value.quote_rules_ascii + (
        (ord(u'@'), ord(u'@')),
        (ord(u':'), ord(u':')),
        (ord(u'/'), ord(u'/')),
    )

class IriQuery(_Value):
    quote_rules_ascii = _Value.quote_rules_ascii + (
        (ord(u'@'), ord(u'@')),
        (ord(u':'), ord(u':')),
        (ord(u'/'), ord(u'/')),
        (ord(u'?'), ord(u'?')),
    )
    
    quote_rules_unicode = _Value.quote_rules_unicode + (
        (  0xE000,   0xF8FF),
        ( 0xF0000,  0xFFFFD),
        (0x100000, 0x10FFFD),
    )

class IriFragment(_Value):
    quote_rules_ascii = _Value.quote_rules_ascii + (
        (ord(u'@'), ord(u'@')),
        (ord(u':'), ord(u':')),
        (ord(u'/'), ord(u'/')),
        (ord(u'?'), ord(u'?')),
    )
