"""
MoinMoin - Tests for MoinMoin.util.iri

@copyright: 2008,2009 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.util.iri import *

def test_Iri_1():
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

def test_Iri_4():
    u = Iri(scheme='wiki', path='Neu?', query='Neu?')
    assert u.scheme == 'wiki'
    assert u.path == 'Neu?'
    assert u.query == 'Neu?'
    assert unicode(u) == 'wiki:Neu%3F?Neu?'

def test_Iri_5():
    i = 'wiki://MoinMoin/StartSeite?action=raw#body'
    u = Iri(i, scheme='newwiki', path='/newStartSeite', query='action=false')
    assert u.scheme == 'newwiki'
    assert u.authority == 'MoinMoin'
    assert u.path == '/newStartSeite'
    assert u.query == 'action=false'
    assert u.fragment == 'body'
