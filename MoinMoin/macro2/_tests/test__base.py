"""
MoinMoin - Tests for MoinMoin.macro2._base

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.macro2._base import *

def test_MacroBase___init__():
    request = object()

    m = MacroBase(request, 'alt', 'context')

    assert m.immutable == False
    assert m.request is request
    assert m.alt == 'alt'
    assert m.context == 'context'

def test_MacroBlockBase___call__():
    item = object()

    class Test(MacroBlockBase):
        def call_macro(self, content):
            return item

    r = Test(None, 'alt', 'block')()
    assert r is item

    r = Test(None, 'alt', 'inline')()
    assert r == 'alt'

def test_MacroInlineBase___call__():
    item = object()

    class Test(MacroInlineBase):
        def call_macro(self, content):
            return item

    r = Test(None, 'alt', 'block')()
    assert r[0] is item

    r = Test(None, 'alt', 'inline')()
    assert r is item

def test_MacroInlineOnlyBase___call__():
    item = object()

    class Test(MacroInlineOnlyBase):
        def call_macro(self, content):
            return item

    r = Test(None, 'alt', 'block')()
    assert r is None

    r = Test(None, 'alt', 'inline')()
    assert r is item

