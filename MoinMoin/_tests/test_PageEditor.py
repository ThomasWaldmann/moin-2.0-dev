# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MoinMoin.PageEditor Tests

    @copyright: 2003-2004 by Juergen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import unittest # LEGACY UNITTEST, PLEASE DO NOT IMPORT unittest IN NEW TESTS, PLEASE CONSULT THE py.test DOCS

import py

from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor
from MoinMoin._tests.common import gain_superuser_rights

class TestExpandVars(unittest.TestCase):
    """PageEditor: testing page editor"""

    pagename = u'AutoCreatedMoinMoinTemporaryTestPage'

    _tests = (
        # Variable,             Expanded
        ("@PAGE@",              pagename),
        ("em@PAGE@bedded",      "em%sbedded" % pagename),
        ("@NOVAR@",             "@NOVAR@"),
        ("case@Page@sensitive", "case@Page@sensitive"),
        )

    def setUp(self):
        self.page = PageEditor(self.request, self.pagename)

    def testExpandVariables(self):
        """ PageEditor: expand general variables """
        for var, expected in self._tests:
            result = self.page._expand_variables(var)
            self.assertEqual(result, expected,
                'Expected "%(expected)s" but got "%(result)s"' % locals())


class TestExpandUserName(unittest.TestCase):
    """ Base class for user name tests

    Set user name during tests.
    """
    pagename = u'AutoCreatedMoinMoinTemporaryTestPage'
    variable = u'@USERNAME@'

    def setUp(self):
        self.page = PageEditor(self.request, self.pagename)
        self.savedName = self.request.user.name
        self.request.user.name = self.name

    def tearDown(self):
        self.request.user.name = self.savedName

    def expand(self):
        return self.page._expand_variables(self.variable)


class TestExpandCamelCaseName(TestExpandUserName):

    name = u'UserName'

    def testExpandCamelCaseUserName(self):
        """ PageEditor: expand @USERNAME@ CamelCase """
        self.assertEqual(self.expand(), self.name)


class TestExpandExtendedName(TestExpandUserName):

    name = u'user name'

    def testExtendedNamesEnabled(self):
        """ PageEditor: expand @USERNAME@ extended name - enabled """
        try:
            config = self.TestConfig()
            self.assertEqual(self.expand(), u'["%s"]' % self.name)
        finally:
            del config


class TestExpandMailto(TestExpandUserName):

    variable = u'@MAILTO@'
    name = u'user name'
    email = 'user@example.com'

    def setUp(self):
        TestExpandUserName.setUp(self)
        self.savedValid = self.request.user.valid
        self.request.user.valid = 1
        self.savedEmail = self.request.user.email
        self.request.user.email = self.email

    def tearDown(self):
        TestExpandUserName.tearDown(self)
        self.request.user.valid = self.savedValid
        self.request.user.email = self.savedEmail

    def testMailto(self):
        """ PageEditor: expand @MAILTO@ """
        self.assertEqual(self.expand(), u'[[MailTo(%s)]]' % self.email)


class TestExpandPrivateVariables(TestExpandUserName):

    variable = u'@ME@'
    name = u'AutoCreatedMoinMoinTemporaryTestUser'
    dictPage = name + '/MyDict'

    def setUp(self):
        TestExpandUserName.setUp(self)
        self.savedValid = self.request.user.valid
        self.request.user.valid = 1
        self.createTestPage()

    def tearDown(self):
        TestExpandUserName.tearDown(self)
        self.request.user.valid = self.savedValid
        self.deleteTestPage()

    def testPrivateVariables(self):
        """ PageEditor: expand user variables """
        self.assertEqual(self.expand(), self.name)

    def createTestPage(self):
        """ Create temporary page, bypass logs, notification and backups
        """
        self.request.cfg.page_backend.create_item(self.name)
        self.request.cfg.page_backend.create_revision(self.name, 1)
        data = self.request.cfg.page_backend.get_data_backend(self.name, 1)
        data.write(u' ME:: %s\n' % self.name)
        data.close()

    def deleteTestPage(self):
        """ Delete temporary page, bypass logs and notifications """
        self.request.cfg.page_backend.remove_item(self.name)


class TestSave:

    def setup_method(self, method):
        self.old_handlers = self.request.cfg.event_handlers
        gain_superuser_rights(self.request)

    def teardown_method(self, method):
        self.request.cfg.event_handlers = self.old_handlers

    def testSaveAbort(self):
        """Test if saveText() is interrupted if PagePreSave event handler returns Abort"""

        def handler(event):
            from MoinMoin.events import Abort
            return Abort("This is just a test")

        pagename = u'AutoCreatedMoinMoinTemporaryTestPageFortestSave'
        testtext = u'ThisIsSomeStupidTestPageText!'

        self.request.cfg.event_handlers = [handler]

        page = Page(self.request, pagename)
        if page.exists():
            deleter = PageEditor(self.request, pagename)
            deleter.deletePage()

        editor = PageEditor(self.request, pagename)
        editor.saveText(testtext, 0)

        print "PageEditor can't save a page if Abort is returned from PreSave event handlers"
        page = Page(self.request, pagename)
        assert page.body != testtext


coverage_modules = ['MoinMoin.PageEditor']
