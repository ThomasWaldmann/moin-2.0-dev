# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Navibar Tests

    @copyright: 2010 MoinMoin:DiogenesAugusto,
                2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin._tests import wikiconfig
from MoinMoin.theme import ThemeBase


class TestNaviBar(object):
    class Config(wikiconfig.Config):
        interwiki_map = dict(MoinMoin='http://moinmo.in/', )

    def setup_method(self, method):
        self.theme = ThemeBase()

    def test_split_navilink(self):
        tests = [
            #(navilink, (href, text, interwiki)),
            ('ItemName', ('/ItemName', 'ItemName', '')),
            ('[[ItemName|LinkText]]', ('/ItemName', 'LinkText', '')),
            ('MoinMoin:ItemName', ('http://moinmo.in/ItemName', 'ItemName', 'MoinMoin')),
            ('[[MoinMoin:ItemName|LinkText]]', ('http://moinmo.in/ItemName', 'LinkText', 'MoinMoin')),
            ('[[wiki:MoinMoin:ItemName|LinkText]]', ('http://moinmo.in/ItemName', 'LinkText', 'MoinMoin')),
            ('http://example.org/', ('http://example.org/', 'http://example.org/', '')),
            ('[[http://example.org/|LinkText]]', ('http://example.org/', 'LinkText', '')),
        ]
        for navilink, expected in tests:
            result = self.theme.split_navilink(navilink)
            assert result == expected

