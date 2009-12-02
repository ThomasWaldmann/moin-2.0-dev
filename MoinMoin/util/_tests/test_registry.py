"""
MoinMoin - Tests for MoinMoin.util.registry

@copyright: 2008,2009 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.util.registry import *

def factory_all(request, input, output):
    return 1

def factory_all2(request, input, output):
    return 3

def factory_none(request, input, output):
    pass

def factory_special(request, input, output):
    if input == 'a':
        return 2

def test_get():
    r = Registry()

    r.register(factory_none)
    r.register(factory_special)
    assert r.get(object(), 'a', None) == 2
    py.test.raises(TypeError, r.get, None, None)

    r.register(factory_all)
    assert r.get(object(), None, None) == 1
    assert r.get(object(), 'a', None) == 2

    r.register(factory_all2, r.PRIORITY_FIRST)
    assert r.get(object(), None, None) == 3
    assert r.get(object(), 'a', None) == 3

def test_register():
    r = Registry()
    assert len(r._converters) == 0
    r.register(factory_all)
    assert len(r._converters) == 1
    r.register(factory_none)
    assert len(r._converters) == 2
    r.register(factory_none)
    assert len(r._converters) == 2

def test_unregister():
    r = Registry()
    r.register(factory_all)
    r.register(factory_none)

    assert len(r._converters) == 2
    r.unregister(factory_all)
    assert len(r._converters) == 1
    r.unregister(factory_none)
    assert len(r._converters) == 0
    py.test.raises(ValueError, r.unregister, factory_none)
    assert len(r._converters) == 0

