# -*- coding: utf-8 -*-
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

    i = 'http:///'
    u = Iri(i)
    assert u.scheme == 'http'
    assert u.authority == ''
    assert u.path == '/'
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

    u = base + Iri('')
    assert u.scheme == 'wiki'
    assert u.authority == 'moinmo.in'
    assert u.path == '/Some/Page'
    assert u.query == 'action=raw'
    assert u.fragment is None

    u = base + Iri('.')
    assert u.scheme == 'wiki'
    assert u.authority == 'moinmo.in'
    assert u.path == '/Some/'
    assert u.query is None
    assert u.fragment is None

    u = base + Iri('..')
    print unicode(u)
    assert u.scheme == 'wiki'
    assert u.authority == 'moinmo.in'
    assert u.path == '/'
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
    u = Iri(scheme=u'wiki', authority=u'Näu%?#', path=u'/Näu%?#', query=u'Näu%?#', fragment=u'Näu%?#')
    assert u.scheme == u'wiki'
    assert u.authority == u'Näu%?#'
    assert u.authority.fullquoted == u'Näu%25%3F%23'
    assert u.authority.quoted == u'Näu%25?#'
    assert u.authority.urlquoted == u'N%C3%A4u%25%3F%23'
    assert u.path == u'/Näu%?#'
    assert u.path.fullquoted == u'/Näu%25%3F%23'
    assert u.path.quoted == u'/Näu%25?#'
    assert u.path.urlquoted == u'/N%C3%A4u%25%3F%23'
    assert u.query == u'Näu%?#'
    assert u.query.fullquoted == u'Näu%25?%23'
    assert u.query.quoted == u'Näu%25?#'
    assert u.query.urlquoted == u'N%C3%A4u%25?%23'
    assert u.fragment == u'Näu%?#'
    assert u.fragment.fullquoted == u'Näu%25?%23'
    assert u.fragment.quoted == u'Näu%25?#'
    assert u.fragment.urlquoted == u'N%C3%A4u%25?%23'
    assert u == u'wiki://Näu%25%3F%23/Näu%25%3F%23?Näu%25?%23#Näu%25?%23'

def test_IriAuthority_parser_1():
    i = 'moinmo.in'
    u = IriAuthority(i)
    assert u.userinfo is None
    assert u.host == 'moinmo.in'
    assert u.port is None
    assert unicode(u) == i

def test_IriAuthority_parser_2():
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

def test_IriPath_1():
    i = '/'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == ''
    assert unicode(u) == i

def test_IriPath_2():
    i = '/.'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == ''
    assert unicode(u) == '/'

    i = '/./'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == ''
    assert unicode(u) == '/'

def test_IriPath_3():
    i = '/..'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == ''
    assert unicode(u) == '/'

    i = '/../'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == ''
    assert unicode(u) == '/'

def test_IriPath_4():
    i = '/test'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == 'test'
    assert unicode(u) == i

    i = '/test/'
    u = IriPath(i)
    assert len(u) == 3
    assert u[0] == ''
    assert u[1] == 'test'
    assert u[2] == ''
    assert unicode(u) == i

    i = '/test/..'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == ''
    assert unicode(u) == '/'

    i = '/test/../'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == ''
    assert unicode(u) == '/'

def test_IriPath_5():
    i = '/test/test1/../../test2'
    u = IriPath(i)
    assert len(u) == 2
    assert u[0] == ''
    assert u[1] == 'test2'
    assert unicode(u) == '/test2'


