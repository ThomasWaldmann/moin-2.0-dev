"""
MoinMoin - Tests for MoinMoin.converter2._args_wiki

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.converter2._args_wiki import *

def test_parse():
    a = parse(ur'both positional both=foo keyword=bar')

    assert a.positional == [u'both', u'positional']
    assert a.keyword == {u'both': u'foo', u'keyword': u'bar'}

    a = parse(ur''''a b\tc\nd',k="a b\tc\nd"''')

    assert a.positional == [u'a b\tc\nd']
    assert a.keyword == {u'k': u'a b\tc\nd'}

def test_unparse():
    positional = [u'both', u'positional']
    keyword = {u'both': u'foo', u'keyword': u'bar'}

    s = unparse(Arguments(positional, keyword))

    assert s == ur'both positional both=foo keyword=bar'

    positional = [u'a b\tc\nd']
    keyword = {u'k': u'a b\tc\nd'}

    s = unparse(Arguments(positional, keyword))

    assert s == ur'''"a b\tc\nd" k="a b\tc\nd"'''
