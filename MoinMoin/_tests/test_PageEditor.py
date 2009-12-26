# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MoinMoin.PageEditor Tests

    @copyright: 2003-2004 by Juergen Hermann <jh@web.de>,
                2007 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import py
py.test.skip("Broken. Needs Page -> Item refactoring.")

from MoinMoin.conftest import dirties_backend
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

# TODO: check if and where we can use the helpers:
from MoinMoin._tests import become_trusted, create_item, nuke_item

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
        assert self.expand() == u'[[%s]]' % self.name


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

    def testPrivateVariables(self):
        """ PageEditor: expand user variables """
        assert self.expand() == self.name

    def createTestPage(self):
        """ Create temporary page, bypass logs, notification and backups
        """
        # As this test is not acl related, we operate on the unprotected storage
        item = self.request.unprotected_storage.create_item(self.name)
        rev = item.create_revision(0)
        rev.write(u' ME:: %s\n' % self.name)
        item.commit()


class TestSave(object):

    def setup_method(self, method):
        self.old_handlers = self.request.cfg.event_handlers
        become_trusted(self.request)

    def teardown_method(self, method):
        self.request.cfg.event_handlers = self.old_handlers
        nuke_item(self.request, u'AutoCreatedMoinMoinTemporaryTestPageFortestSave')

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
        editor.saveText(testtext, None)

        # PageEditor may not save a page if Abort is returned from PreSave event handlers
        page = Page(self.request, pagename)
        assert not page.exists()


class TestDictPageDeletion(object):

    def testCreateDictAndDeleteDictPage(self):
        """
        simple test if it is possible to delete a Dict page after creation
        """
        become_trusted(self.request)
        pagename = u'SomeDict'
        page = PageEditor(self.request, pagename, do_editor_backup=0)
        body = u"This is an example text"
        page.saveText(body, None)

        success_i, result = page.deletePage()

        expected = u'Page "SomeDict" was successfully deleted!'

        assert result == expected

class TestCopyPage(object):

    pagename = u'AutoCreatedMoinMoinTemporaryTestPageX'
    copy_pagename = u'AutoCreatedMoinMoinTemporaryCopyTestPage'
    text = u'Example'

    def setup_method(self, method):
        self.savedValid = self.request.user.valid
        self.request.user.valid = 1

    def teardown_method(self, method):
        self.request.user.valid = self.savedValid

    def createTestPage(self):
        """ Create temporary page, bypass logs, notification and backups
        """
        item = self.request.unprotected_storage.create_item(self.pagename)
        rev = item.create_revision(0)
        rev.write(self.text)
        item.commit()

    def copyTest(self):
        result, msg = PageEditor(self.request, self.pagename).copyPage(self.copy_pagename)
        revision = Page(self.request, self.copy_pagename).current_rev()
        return result, revision

    @dirties_backend
    def test_copy_page(self):
        """
        Tests copying a page without restricted acls
        """
        self.createTestPage()
        result, revision = self.copyTest()
        assert result and revision == 1

    @dirties_backend
    def test_copy_page_to_already_existing_page(self):
        """
        Tests copying a page to a page that already exists
        """
        self.createTestPage()
        result, revision = self.copyTest()
        result, revision = self.copyTest()
        assert result and revision == 2

    def test_copy_page_acl_read(self):
        """
        Tests copying a page without write rights
        """
        py.test.skip("No use is being made of ACLs right now. Fix after SoC.")
        self.text = u'#acl SomeUser:read,write All:read\n'
        self.createTestPage()
        result, msg = PageEditor(self.request, self.pagename).copyPage(self.copy_pagename)
        revision = Page(self.request, self.copy_pagename).current_rev()
        assert result and revision == 2

    def test_copy_page_acl_no_read(self):
        """
        Tests copying a page without read rights
        """
        py.test.skip("No use is being made of ACLs right now. Fix after SoC.")
        self.text = u'#acl SomeUser:read,write All:\n'
        self.createTestPage()
        result, msg = PageEditor(self.request, self.pagename).copyPage(self.copy_pagename)
        revision = Page(self.request, self.copy_pagename).current_rev()
        assert result and revision == 2

coverage_modules = ['MoinMoin.PageEditor']
