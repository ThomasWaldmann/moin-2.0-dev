# -*- coding: utf-8 -*-
"""
    MoinMoin - basic tests for frontend

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

class TestFrontend(object):
    def test_root(self):
        with self.app.test_client() as c:
            rv = c.get('/') # / redirects to front page
            assert rv.status == '302 FOUND'

    def test_robots(self):
        with self.app.test_client() as c:
            rv = c.get('/robots.txt')
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'text/plain; charset=utf-8'
            assert 'Disallow:' in rv.data

    def test_favicon(self):
        with self.app.test_client() as c:
            rv = c.get('/favicon.ico')
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'image/x-icon'
            assert rv.data.startswith('\x00\x00') # "reserved word, should always be 0"

    def test_404(self):
        with self.app.test_client() as c:
            rv = c.get('/DoesntExist')
            assert rv.status == '404 NOT FOUND'
            assert rv.headers['Content-Type'] == 'text/html; charset=utf-8'
            assert '<html>' in rv.data
            assert '</html>' in rv.data

    def test_global_index(self):
        with self.app.test_client() as c:
            rv = c.get('/+index')
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'text/html; charset=utf-8'
            assert '<html>' in rv.data
            assert '</html>' in rv.data


