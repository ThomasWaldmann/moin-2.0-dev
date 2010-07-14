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

    def test_itemname(self):
        item_name, href, link_text, interwiki = self.theme.splitNavilink('ItemName')
        assert link_text == 'ItemName'
        assert interwiki == ''
        
    def test_itemname_with_text(self):
        item_name, href, link_text, interwiki = self.theme.splitNavilink('[[ItemName|LinkText]]')
        assert link_text == 'LinkText'
        assert href == 'ItemName'
        assert interwiki == ''
        
    def test_interwiki(self):
        item_name, url, link_text, interwiki = self.theme.splitNavilink('MoinMoin:ItemName')
        assert link_text == 'ItemName'
        assert url == 'http://moinmo.in/ItemName'
        assert interwiki == 'MoinMoin'

    def test_interwiki_with_text(self):
        item_name, url, link_text, interwiki = self.theme.splitNavilink('[[MoinMoin:ItemName|LinkText]]')
        assert link_text == 'LinkText'
        assert url == 'http://moinmo.in/ItemName'
        assert interwiki == 'MoinMoin'

    def test_wiki_interwiki_with_text(self):
        item_name, url, link_text, interwiki = self.theme.splitNavilink('[[wiki:MoinMoin:ItemName|LinkText]]')
        assert link_text == 'LinkText'
        assert url == 'http://moinmo.in/ItemName'
        assert interwiki == 'MoinMoin'

    def test_external_url(self):
        item_name, url, link_text, interwiki = self.theme.splitNavilink('http://diofeher.net/')
        assert link_text == 'http://diofeher.net/'
        assert url == 'http://diofeher.net/'
        assert interwiki == ''

    def test_external_url_with_title(self):
        item_name, url, link_text, interwiki = self.theme.splitNavilink('[[http://google.com/|Google]]')
        assert link_text == 'Google'
        assert url == 'http://google.com/'
        assert interwiki == ''
