# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MoinMoin.PageEditor Tests

    @copyright: 2003-2004 by Juergen Hermann <jh@web.de>,
                2007 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import py

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor
from MoinMoin._tests.common import gain_superuser_rights

class TestExpandVars(object):
    """PageEditor: testing page editor"""
    pagename = u'AutoCreatedMoinMoinTemporaryTestPage'

    _tests = (
        # Variable,             Expanded
        ("@PAGE@", pagename),
        ("em@PAGE@bedded", "em%sbedded" % pagename),
        ("@NOVAR@", "@NOVAR@"),
        ("case@Page@sensitive", "case@Page@sensitive"),
        )

    def setup_method(self, method):
        self.page = PageEditor(self.request, self.pagename)

    def testExpandVariables(self):
        """ PageEditor: expand general variables """
        for var, expected in self._tests:
            result = self.page._expand_variables(var)
            assert result == expected


class TestExpandUserName(object):
    """ Base class for user name tests

    Set user name during tests.
    """
    pagename = u'AutoCreatedMoinMoinTemporaryTestPage'
    variable = u'@USERNAME@'

    def setup_method(self, method):
        self.page = PageEditor(self.request, self.pagename)
        self.savedName = self.request.user.name
        self.request.user.name = self.name

    def teardown_method(self, method):
        self.request.user.name = self.savedName

    def expand(self):
        return self.page._expand_variables(self.variable)


class TestExpandCamelCaseName(TestExpandUserName):

    name = u'UserName'

    def testExpandCamelCaseUserName(self):
        """ PageEditor: expand @USERNAME@ CamelCase """
        assert self.expand() == self.name


class TestExpandExtendedName(TestExpandUserName):

    name = u'user name'

    def testExtendedNamesEnabled(self):
        """ PageEditor: expand @USERNAME@ extended name - enabled """
        try:
            config = self.TestConfig()
            assert self.expand() == u'[[%s]]' % self.name
        finally:
            del config


class TestExpandMailto(TestExpandUserName):

    variable = u'@MAILTO@'
    name = u'user name'
    email = 'user@example.com'

    def setup_method(self, method):
        super(TestExpandMailto, self).setup_method(method)
        self.savedValid = self.request.user.valid
        self.request.user.valid = 1
        self.savedEmail = self.request.user.email
        self.request.user.email = self.email

    def teardown_method(self, method):
        super(TestExpandMailto, self).teardown_method(method)
        self.request.user.valid = self.savedValid
        self.request.user.email = self.savedEmail

    def testMailto(self):
        """ PageEditor: expand @MAILTO@ """
        assert self.expand() == u'<<MailTo(%s)>>' % self.email


class TestExpandPrivateVariables(TestExpandUserName):

    variable = u'@ME@'
    name = u'AutoCreatedMoinMoinTemporaryTestUser'
    dictPage = name + '/MyDict'

    def setup_method(self, method):
        super(TestExpandPrivateVariables, self).setup_method(method)
        self.savedValid = self.request.user.valid
        self.request.user.valid = 1
        self.createTestPage()

    def teardown_method(self, method):
        super(TestExpandPrivateVariables, self).teardown_method(method)
        self.request.user.valid = self.savedValid
        self.deleteTestPage()

    def testPrivateVariables(self):
        """ PageEditor: expand user variables """
        assert self.expand() == self.name

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


class TestSave(object):

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


class TestDictPageDeletion(object):

    def testCreateDictAndDeleteDictPage(self):
        """
        simple test if it is possible to delete a Dict page after creation
        """
        pagename = u'SomeDict'
        page = PageEditor(self.request, pagename, do_editor_backup=0)
        body = u"This is an example text"
        page.saveText(body, 0)

        success_i, result = page.deletePage()

        expected = u'Page "SomeDict" was successfully deleted!'

        assert result == expected

coverage_modules = ['MoinMoin.PageEditor']

