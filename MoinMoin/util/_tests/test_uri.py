"""
MoinMoin - Tests for MoinMoin.util.uri

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.util.uri import *

def test_Uri_1():
    i = 'http://moinmo.in/StartSeite?action=raw#body'
    u = Uri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert str(u) == i

    i = 'http://moinmo.in/StartSeite?action=raw'
    u = Uri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment is None
    assert str(u) == i

    i = 'http://moinmo.in/StartSeite'
    u = Uri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path == '/StartSeite'
    assert u.query is None
    assert u.fragment is None
    assert str(u) == i

    i = 'http://moinmo.in'
    u = Uri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path is None
    assert u.query is None
    assert u.fragment is None
    assert str(u) == i

    i = 'http:'
    u = Uri(i)
    assert u.scheme == 'http'
    assert u.authority is None
    assert u.path is None
    assert u.query is None
    assert u.fragment is None
    assert str(u) == i

    i = 'http://moinmo.in/StartSeite#body'
    u = Uri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path == '/StartSeite'
    assert u.query is None
    assert u.fragment == 'body'
    assert str(u) == i

    i = 'http://moinmo.in#body'
    u = Uri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path is None
    assert u.query is None
    assert u.fragment == 'body'
    assert str(u) == i

    i = 'http:#body'
    u = Uri(i)
    assert u.scheme == 'http'
    assert u.authority is None
    assert u.path is None
    assert u.query is None
    assert u.fragment == 'body'
    assert str(u) == i

    i = 'http://moinmo.in?action=raw#body'
    u = Uri(i)
    assert u.scheme == 'http'
    assert u.authority == 'moinmo.in'
    assert u.path is None
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert str(u) == i

    i = 'http:?action=raw#body'
    u = Uri(i)
    assert u.scheme == 'http'
    assert u.authority is None
    assert u.path is None
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert str(u) == i

    i = 'http:/StartSeite?action=raw#body'
    u = Uri(i)
    assert u.scheme == 'http'
    assert u.authority is None
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert str(u) == i

def test_Uri_2():
    i = 'wiki://MoinMoin/StartSeite?action=raw#body'
    u = Uri(i)
    assert u.scheme == 'wiki'
    assert u.authority == 'MoinMoin'
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert str(u) == i

    i = 'wiki:///StartSeite?action=raw#body'
    u = Uri(i)
    assert u.scheme == 'wiki'
    assert u.authority == ''
    assert u.path == '/StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert str(u) == i

def test_Uri_3():
    i = 'wiki.local:StartSeite?action=raw#body'
    u = Uri(i)
    assert u.scheme == 'wiki.local'
    assert u.authority is None
    assert u.path == 'StartSeite'
    assert u.query == 'action=raw'
    assert u.fragment == 'body'
    assert str(u) == i

def test_Uri_4():
    u = Uri(scheme='wiki', path='Neu?', query='Neu?')
    assert u.scheme == 'wiki'
    assert u.path == 'Neu?'
    assert u.query == 'Neu?'
    assert str(u) == 'wiki:Neu%3F?Neu?'

def test_Uri_5():
    i = 'wiki://MoinMoin/StartSeite?action=raw#body'
    u = Uri(i, scheme='newwiki', path='/newStartSeite', query='action=false')
    assert u.scheme == 'newwiki'
    assert u.authority == 'MoinMoin'
    assert u.path == '/newStartSeite'
    assert u.query == 'action=false'
    assert u.fragment == 'body'
