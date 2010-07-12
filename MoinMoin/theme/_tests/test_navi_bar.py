# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Navibar Tests

    @copyright: 2010 MoinMoin:DiogenesAugustoFernandesHerminio
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.theme import ThemeBase

class TestNaviBar(object):
    def setup_method(self, method):
        self.theme = ThemeBase(self.request)

    def test_interwiki(self):
        item_name, url, link_text, title = self.theme.splitNavilink('MoinMoin:ItemName')
        assert link_text == 'ItemName'
        assert url == 'http://moinmo.in/ItemName'
        assert title == 'MoinMoin'
