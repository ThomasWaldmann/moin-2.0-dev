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

def test_Iri_init_override_2():
    i = 'text/plain;encoding=utf-8'
    t = Type(i, type='foo', subtype='bar', parameters={'foo': 'bar'})
    assert t.type == 'foo'
    assert t.subtype == 'bar'
    assert t.parameters == {'encoding': 'utf-8', 'foo': 'bar'}

def test_Iri_parser():
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
