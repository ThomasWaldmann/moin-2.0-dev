# -*- coding: utf-8 -*-
"""
    MoinMoin - MoinMoin.wsgiapp Tests

    @copyright: 2008 MoinMoin:FlorianKrupicka
    @license: GNU GPL, see COPYING for details.
"""
from os.path import join, abspath, dirname
from StringIO import StringIO

from MoinMoin import wsgiapp
from MoinMoin._tests import wikiconfig
from MoinMoin.storage.backends.memory import MemoryBackend

DOC_TYPE = '<!DOCTYPE html>'

class TestApplication:
    # self.client is made by conftest

    # These should exist
    PAGES = ('FrontPage', 'HelpOnLinking', 'HelpOnMoinWikiSyntax', )
    # ... and these should not
    NO_PAGES = ('FooBar', 'TheNone/ExistantPage/', '%33Strange%74Codes')

    class Config(wikiconfig.Config):
        preloaded_xml = join(abspath(dirname(__file__)), 'testitems.xml')

    def testWSGIAppExisting(self):
        for page in self.PAGES:
            def _test_(page=page):
                appiter, status, headers = self.client.get('/%s' % page)
                output = ''.join(appiter)
                assert status[:3] == '200'
                assert ('Content-Type', 'text/html; charset=utf-8') in headers
                for needle in (DOC_TYPE, page):
                    assert needle in output
            yield _test_

    def testWSGIAppAbsent(self):
        for page in self.NO_PAGES:
            def _test_(page=page):
                appiter, status, headers = self.client.get('/%s' % page)
                output = ''.join(appiter)
                assert 'This item does not exist' in output
                assert status[:3] == '404'
            yield _test_
