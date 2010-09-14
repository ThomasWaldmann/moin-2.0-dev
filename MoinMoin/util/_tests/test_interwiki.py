# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MoinMoin.util.interwiki Tests

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.util.interwiki import resolve_interwiki, split_interwiki, join_wiki
from MoinMoin._tests import wikiconfig


class TestInterWiki(object):
    class Config(wikiconfig.Config):
        interwiki_map = dict(MoinMoin='http://moinmo.in/', )

    def testSplitWiki(self):
        tests = [('SomePage', ('Self', 'SomePage')),
                 ('OtherWiki:OtherPage', ('OtherWiki', 'OtherPage')),
                 (':OtherPage', ('', 'OtherPage')),
                 # broken ('/OtherPage', ('Self', '/OtherPage')),
                 # wrong interpretation ('MainPage/OtherPage', ('Self', 'MainPage/OtherPage')),
                ]
        for markup, (wikiname, pagename) in tests:
            assert split_interwiki(markup) == (wikiname, pagename)

    def testJoinWiki(self):
        tests = [(('http://example.org/', u'SomePage'), 'http://example.org/SomePage'),
                 (('http://example.org/?page=$PAGE&action=show', u'SomePage'), 'http://example.org/?page=SomePage&action=show'),
                 (('http://example.org/', u'Aktuelle\xc4nderungen'), 'http://example.org/Aktuelle%C3%84nderungen'),
                 (('http://example.org/$PAGE/show', u'Aktuelle\xc4nderungen'), 'http://example.org/Aktuelle%C3%84nderungen/show'),
                ]
        for (baseurl, pagename), url in tests:
            assert join_wiki(baseurl, pagename) == url

    def testResolveInterWiki(self):
        result = resolve_interwiki('MoinMoin', 'SomePage')
        assert result == ('MoinMoin', u'http://moinmo.in/', 'SomePage', False)
        result = resolve_interwiki('Self', 'SomePage')
        assert result == ('Self', u'/', 'SomePage', False)


coverage_modules = ['MoinMoin.util.interwiki']

