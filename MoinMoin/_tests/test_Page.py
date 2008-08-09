# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MoinMoin.Page Tests

    @copyright: 2007 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import py

from MoinMoin.Page import Page

class TestPage:
    def testMeta(self):
        page = Page(self.request, u'FrontPage')
        meta = page.meta
        for k, v in meta.iteritems():
            if k == u'format':
                assert v == u'wiki'
            elif k == u'language':
                assert v == u'en'

    def testBody(self):
        page = Page(self.request, u'FrontPage')
        body = page.body
        assert type(body) is unicode
        assert 'MoinMoin' in body
        assert body.endswith('\n')
        assert '\r' not in body

    def testExists(self):
        assert Page(self.request, 'FrontPage').exists()
        assert not Page(self.request, 'ThisPageDoesNotExist').exists()
        assert not Page(self.request, '').exists()

    def testLastEdit(self):
        page = Page(self.request, u'FrontPage')
        last_edit = page.last_edit()
        assert 'editor' in last_edit
        assert 'timestamp' in last_edit

    def testSplitTitle(self):
        page = Page(self.request, u"FrontPage")
        assert page.split_title(force=True) == u'Front Page'

    def testGetRevList(self):
        page = Page(self.request, u"FrontPage")
        assert 1 in page.getRevList()

    def testGetPageLinks(self):
        page = Page(self.request, u"FrontPage")
        assert u'WikiSandBox' in page.getPageLinks(self.request)

    def testSendPage(self):
        page = Page(self.request, u"FrontPage")
        import StringIO
        out = StringIO.StringIO()
        self.request.redirect(out)
        page.send_page(msg=u'Done', emit_headers=False)
        result = out.getvalue()
        self.request.redirect()
        del out
        assert result.strip().endswith('</html>')
        assert result.strip().startswith('<!DOCTYPE HTML PUBLIC')

class TestRootPage:
    def testPageList(self):
        rootpage = self.request.rootpage
        pagelist = rootpage.getPageList()
        cnt = 0
        for pg in pagelist:
            cnt += 1
            if cnt > 100:
                break
        assert cnt > 100
        assert u'FrontPage' in pagelist
        assert u'' not in pagelist


coverage_modules = ['MoinMoin.Page']

