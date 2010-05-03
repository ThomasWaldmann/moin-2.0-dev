"""
MoinMoin - Tests for MoinMoin.util.registry

@copyright: 2008,2009 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.util.registry import *

def factory_all(arg):
    return 1

def factory_all2(arg):
    return 3

def factory_none(arg):
    pass

def factory_special(arg):
    if arg == 'a':
        return 2

def test_get():
    r = Registry()

    r.register(factory_none)
    r.register(factory_special)
    assert r.get('a') == 2

    r.register(factory_all)
    assert r.get(None) == 1
    assert r.get('a') == 2

    r.register(factory_all2, r.PRIORITY_FIRST)
    assert r.get(None) == 3
    assert r.get('a') == 3

def test_register():
    r = Registry()
    assert len(r._entries) == 0
    r.register(factory_all)
    assert len(r._entries) == 1
    r.register(factory_none)
    assert len(r._entries) == 2
    r.register(factory_none)
    assert len(r._entries) == 2

def test_unregister():
    r = Registry()
    r.register(factory_all)
    r.register(factory_none)

    assert len(r._entries) == 2
    r.unregister(factory_all)
    assert len(r._entries) == 1
    r.unregister(factory_none)
    assert len(r._entries) == 0
    py.test.raises(ValueError, r.unregister, factory_none)
    assert len(r._entries) == 0

