# -*- coding: utf-8 -*-
"""
    MoinMoin - basic tests for misc views

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

class TestMisc(object):
    def test_global_sitemap(self):
        with self.app.test_client() as c:
            rv = c.get('/+misc/sitemap')
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'text/xml'
            assert rv.data.startswith('<?xml')
            assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in rv.data
            assert '</urlset>' in rv.data

