# -*- coding: utf-8 -*-
"""
MoinMoin - Tests for MoinMoin.util.mime

@copyright: 2009 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.util.mime import *

def test_Type_init_1():
    t = Type(type='foo', subtype='bar', parameters={'foo': 'bar'})
    assert t.type == 'foo'
    assert t.subtype == 'bar'
    assert t.parameters == {'foo': 'bar'}

def test_Type_init_2():
    i = 'text/plain;encoding=utf-8'
    t = Type(i, type='foo', subtype='bar', parameters={'foo': 'bar'})
    assert t.type == 'foo'
    assert t.subtype == 'bar'
    assert t.parameters == {'encoding': 'utf-8', 'foo': 'bar'}

def test_Type_init_3():
    i = Type(type='foo', subtype='bar')
    t = Type(i)
    assert i is not t
    assert i == t
    assert i.parameters is not t.parameters

def test_Type_parser():
    i = 'text/plain'
    t = Type(i)
    assert t.type == 'text'
    assert t.subtype == 'plain'
    assert t.parameters == {}

    i = 'text/plain;encoding=utf-8;foo="bar"'
    t = Type(i)
    assert t.type == 'text'
    assert t.subtype == 'plain'
    assert t.parameters == {'encoding': 'utf-8', 'foo': 'bar'}

def test_Type_unicode():
    i = 'text/plain;encoding=utf-8;foo=bar'
    t = Type(i)
    assert unicode(t) == i

    i = 'text/plain;encoding=utf-8;foo="["'
    t = Type(i)
    assert unicode(t) == i

def test_Type_compare():
    t1 = Type(type='text', subtype='plain')

    assert t1 == t1
    assert t1.issupertype(t1)

    t2 = Type(type='text')
    assert t1 != t2
    assert t2.issupertype(t1)

    t2 = Type(type='text', subtype='plain', parameters={'encoding': 'iso8859-1'})

    assert t1 != t2
    assert t1.issupertype(t2)

    t2 = Type(type='text', subtype='html')

    assert t1 != t2
    assert not t1.issupertype(t2)

