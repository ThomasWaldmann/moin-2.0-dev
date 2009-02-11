"""
MoinMoin - Tests for MoinMoin.util.iri

@copyright: 2008,2009 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.util.iri import *

def test_Iri_init_1():
    u = Iri(scheme='wiki', path='/StartSeite', query='action=raw')
    assert u.scheme == 'wiki'
    assert u.authority is None
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment is None

def test_Iri_init_override_2():
    i = 'wiki://MoinMoin/StartSeite?action=raw#body'
    u = Iri(i, scheme='newwiki', path='/newStartSeite', query='action=false')
    assert u.scheme == 'newwiki'
    assert u.authority == 'MoinMoin'
    assert u.path == '/newStartSeite'
    assert u.query == 'action=false'
    assert u.fragment == 'body'

def test_Iri_parser():
    i = 'http://moinmo.in/StartSeite?action=raw#body'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert unicode(u) == i

    i = 'http://moinmo.in/StartSeite?action=raw'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment is None
    assert unicode(u) == i

    i = 'http://moinmo.in/StartSeite'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path == '/StartSeite'
    assert u.query is None
    assert u.fragment is None
    assert unicode(u) == i

    i = 'http://moinmo.in'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path is None
    assert u.query is None
    assert u.fragment is None
    assert unicode(u) == i

    i = 'http:///StartSeite?action=raw#body'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == ''
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert unicode(u) == i

    i = 'http:///StartSeite?action=raw'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == ''
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment is None
    assert unicode(u) == i

    i = 'http:///StartSeite'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == ''
    assert u.path == '/StartSeite'
    assert u.query is None
    assert u.fragment is None
    assert unicode(u) == i

    i = 'http://'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == ''
    assert u.path is None
    assert u.query is None
    assert u.fragment is None
    assert unicode(u) == i

    i = 'http:'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority is None
    assert u.path is None
    assert u.query is None
    assert u.fragment is None
    assert unicode(u) == i

    i = 'http://moinmo.in/StartSeite#body'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path == '/StartSeite'
    assert u.query is None
    assert u.fragment == 'body'
    assert unicode(u) == i

    i = 'http://moinmo.in#body'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path is None
    assert u.query is None
    assert u.fragment == 'body'
    assert unicode(u) == i

    i = 'http:#body'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority is None
    assert u.path is None
    assert u.query is None
    assert u.fragment == 'body'
    assert unicode(u) == i

    i = 'http://moinmo.in?action=raw#body'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path is None
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert unicode(u) == i

    i = 'http:?action=raw#body'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority is None
    assert u.path is None
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert unicode(u) == i

    i = 'http:/StartSeite?action=raw#body'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority is None
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert unicode(u) == i

def test_Iri_2():
    i = 'wiki://MoinMoin/StartSeite?action=raw#body'
    u = Iri(i)
    assert u.scheme == 'wiki'
    assert u.authority == 'MoinMoin'
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert unicode(u) == i

    i = 'wiki:///StartSeite?action=raw#body'
    u = Iri(i)
    assert u.scheme == 'wiki'
    assert u.authority == ''
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert unicode(u) == i

def test_Iri_3():
    i = 'wiki.local:StartSeite?action=raw#body'
    u = Iri(i)
    assert u.scheme == 'wiki.local'
    assert u.authority is None
    assert u.path == 'StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert unicode(u) == i

def test_Iri_add_1():
    base = Iri('wiki://moinmo.in/Some/Page?action=raw#body')

    u = base + Iri('http://thinkmo.de/')
    assert u.scheme == 'http'
    assert u.authority == 'thinkmo.de'
    assert u.path == '/'
    assert u.query is None
    assert u.fragment is None

    u = base + Iri('//thinkmo.de/')
    assert u.scheme == 'wiki'
    assert u.authority == 'thinkmo.de'
    assert u.path == '/'
    assert u.query is None
    assert u.fragment is None

    u = base + Iri('/')
    assert u.scheme == 'wiki'
    assert u.authority == 'moinmo.in'
    assert u.path == '/'
    assert u.query is None
    assert u.fragment is None

    u = base + Iri('/?action=edit')
    assert u.scheme == 'wiki'
    assert u.authority == 'moinmo.in'
    assert u.path == '/'
    assert u.query == 'action=edit'
    assert u.fragment is None

    u = base + Iri('..')
    assert u.scheme == 'wiki'
    assert u.authority == 'moinmo.in'
    assert u.path == '/Some'
    assert u.query is None
    assert u.fragment is None

    u = base + Iri('')
    assert u.scheme == 'wiki'
    assert u.authority == 'moinmo.in'
    assert u.path == '/Some/Page'
    assert u.query is None
    assert u.fragment is None

    u = base + Iri('?action=edit')
    assert u.scheme == 'wiki'
    assert u.authority == 'moinmo.in'
    assert u.path == '/Some/Page'
    assert u.query == 'action=edit'
    assert u.fragment is None

    u = base + Iri('#head')
    assert u.scheme == 'wiki'
    assert u.authority == 'moinmo.in'
    assert u.path == '/Some/Page'
    assert u.query == 'action=raw'
    assert u.fragment == 'head'

def test_Iri_quote():
    u = Iri(scheme='wiki', authority='Neu%?#', path='/Neu%?#', query='Neu%?#', fragment='Neu%?#')
    assert u.scheme == 'wiki'
    assert u.authority == 'Neu%?#'
    assert u.authority_fullquoted == 'Neu%25%3F%23'
    assert u.authority_quoted == 'Neu%25?#'
    assert u.path == '/Neu%?#'
    assert u.path_fullquoted == '/Neu%25%3F%23'
    assert u.path_quoted == '/Neu%25?#'
    assert u.query == 'Neu%?#'
    assert u.query_fullquoted == 'Neu%25?%23'
    assert u.query_quoted == 'Neu%25?#'
    assert u.fragment == 'Neu%?#'
    assert u.fragment_fullquoted == 'Neu%25?%23'
    assert u.fragment_quoted == 'Neu%25?#'
    assert unicode(u) == 'wiki://Neu%25%3F%23/Neu%25%3F%23?Neu%25?%23#Neu%25?%23'

def test_IriAuthority_parser_1():
    i = 'moinmo.in'
    u = IriAuthority(i)
    assert u.userinfo is None
    assert u.host == 'moinmo.in'
    assert u.port is None
    assert unicode(u) == i

def test_IriAuthority_parser_2():
    py.test.skip()
    i = '@moinmo.in:'
    u = IriAuthority(i)
    assert u.userinfo == ''
    assert u.host == 'moinmo.in'
    assert u.port == 0
    assert unicode(u) == i

def test_IriAuthority_parser_3():
    i = 'test:test@moinmo.in:1234'
    u = IriAuthority(i)
    assert u.userinfo == 'test:test'
    assert u.host == 'moinmo.in'
    assert u.port == 1234
    assert unicode(u) == i

