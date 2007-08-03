# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MoinMoin.security Tests

    TODO: when refactoring this, do not use "iter" (is a builtin)

    @copyright: 2003-2004 by Juergen Hermann <jh@web.de>
                2007 by MoinMoin:ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""

import py
import unittest # LEGACY UNITTEST, PLEASE DO NOT IMPORT unittest IN NEW TESTS, PLEASE CONSULT THE py.test DOCS
from MoinMoin import security

acliter = security.ACLStringIterator

class TestACLStringIterator(unittest.TestCase):

    def setUp(self):
        self.config = self.TestConfig(defaults=['acl_rights_valid', 'acl_rights_before'])
    def tearDown(self):
        del self.config

    def testEmpty(self):
        """ security: empty acl string raise StopIteration """
        iter = acliter(self.request.cfg.acl_rights_valid, '')
        self.failUnlessRaises(StopIteration, iter.next)

    def testWhiteSpace(self):
        """ security: white space acl string raise StopIteration """
        iter = acliter(self.request.cfg.acl_rights_valid, '       ')
        self.failUnlessRaises(StopIteration, iter.next)

    def testDefault(self):
        """ security: default meta acl """
        iter = acliter(self.request.cfg.acl_rights_valid, 'Default Default')
        for mod, entries, rights in iter:
            self.assertEqual(entries, ['Default'])
            self.assertEqual(rights, [])

    def testEmptyRights(self):
        """ security: empty rights """
        iter = acliter(self.request.cfg.acl_rights_valid, 'WikiName:')
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['WikiName'])
        self.assertEqual(rights, [])

    def testSingleWikiNameSingleWrite(self):
        """ security: single wiki name, single right """
        iter = acliter(self.request.cfg.acl_rights_valid, 'WikiName:read')
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['WikiName'])
        self.assertEqual(rights, ['read'])

    def testMultipleWikiNameAndRights(self):
        """ security: multiple wiki names and rights """
        iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne,UserTwo:read,write')
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['UserOne', 'UserTwo'])
        self.assertEqual(rights, ['read', 'write'])

    def testMultipleWikiNameAndRightsSpaces(self):
        """ security: multiple names with spaces """
        iter = acliter(self.request.cfg.acl_rights_valid, 'user one,user two:read')
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['user one', 'user two'])
        self.assertEqual(rights, ['read'])

    def testMultipleEntries(self):
        """ security: multiple entries """
        iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne:read,write UserTwo:read All:')
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['UserOne'])
        self.assertEqual(rights, ['read', 'write'])
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['UserTwo'])
        self.assertEqual(rights, ['read'])
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['All'])
        self.assertEqual(rights, [])

    def testNameWithSpaces(self):
        """ security: single name with spaces """
        iter = acliter(self.request.cfg.acl_rights_valid, 'user one:read')
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['user one'])
        self.assertEqual(rights, ['read'])

    def testMultipleEntriesWithSpaces(self):
        """ security: multiple entries with spaces """
        iter = acliter(self.request.cfg.acl_rights_valid, 'user one:read,write user two:read')
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['user one'])
        self.assertEqual(rights, ['read', 'write'])
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['user two'])
        self.assertEqual(rights, ['read'])

    def testMixedNames(self):
        """ security: mixed wiki names and names with spaces """
        iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne,user two:read,write user three,UserFour:read')
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['UserOne', 'user two'])
        self.assertEqual(rights, ['read', 'write'])
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['user three', 'UserFour'])
        self.assertEqual(rights, ['read'])

    def testModifier(self):
        """ security: acl modifiers """
        iter = acliter(self.request.cfg.acl_rights_valid, '+UserOne:read -UserTwo:')
        mod, entries, rights = iter.next()
        self.assertEqual(mod, '+')
        self.assertEqual(entries, ['UserOne'])
        self.assertEqual(rights, ['read'])
        mod, entries, rights = iter.next()
        self.assertEqual(mod, '-')
        self.assertEqual(entries, ['UserTwo'])
        self.assertEqual(rights, [])

    def testIgnoreInvalidACL(self):
        """ security: ignore invalid acl

        The last part of this acl can not be parsed. If it ends with :
        then it will be parsed as one name with spaces.
        """
        iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne:read user two is ignored')
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['UserOne'])
        self.assertEqual(rights, ['read'])
        self.failUnlessRaises(StopIteration, iter.next)

    def testEmptyNamesWithRight(self):
        """ security: empty names with rights

        The documents does not talk about this case, may() should ignore
        the rights because there is no entry.
        """
        iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne:read :read All:')
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['UserOne'])
        self.assertEqual(rights, ['read'])
        mod, entries, rights = iter.next()
        self.assertEqual(entries, [])
        self.assertEqual(rights, ['read'])
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['All'])
        self.assertEqual(rights, [])

    def testIgnodeInvalidRights(self):
        """ security: ignore rights not in acl_rights_valid """
        iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne:read,sing,write,drink,sleep')
        mod, entries, rights = iter.next()
        self.assertEqual(rights, ['read', 'write'])

    def testBadGuy(self):
        """ security: bad guy may not allowed anything

        This test was failing on the apply acl rights test.
        """
        iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne:read,write BadGuy: All:read')
        mod, entries, rights = iter.next()
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['BadGuy'])
        self.assertEqual(rights, [])

    def testAllowExtraWhitespace(self):
        """ security: allow extra white space between entries """
        iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne,user two:read,write   user three,UserFour:read  All:')
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['UserOne', 'user two'])
        self.assertEqual(rights, ['read', 'write'])
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['user three', 'UserFour'])
        self.assertEqual(rights, ['read'])
        mod, entries, rights = iter.next()
        self.assertEqual(entries, ['All'])
        self.assertEqual(rights, [])


class TestAcl(unittest.TestCase):
    """ security: testing access control list

    TO DO: test unknown user?
    """
    def setUp(self):
        # Backup user
        self.config = self.TestConfig(defaults=['acl_rights_valid', 'acl_rights_before'])
        self.savedUser = self.request.user.name

    def tearDown(self):
        # Restore user
        self.request.user.name = self.savedUser
        del self.config

    def testApplyACLByUser(self):
        """ security: applying acl by user name"""
        # This acl string...
        acl_rights = [
            "Admin1,Admin2:read,write,delete,revert,admin  "
            "Admin3:read,write,admin  "
            "JoeDoe:read,write  "
            "name with spaces,another one:read,write  "
            "CamelCase,extended name:read,write  "
            "BadGuy:  "
            "All:read  "
            ]
        acl = security.AccessControlList(self.request.cfg, acl_rights)

        # Should apply these rights:
        users = (
            # user,                 rights
            # CamelCase names
            ('Admin1',              ('read', 'write', 'admin', 'revert', 'delete')),
            ('Admin2',              ('read', 'write', 'admin', 'revert', 'delete')),
            ('Admin3',              ('read', 'write', 'admin')),
            ('JoeDoe',              ('read', 'write')),
            ('SomeGuy',             ('read', )),
            # Extended names or mix of extended and CamelCase
            ('name with spaces',    ('read', 'write', )),
            ('another one',         ('read', 'write', )),
            ('CamelCase',           ('read', 'write', )),
            ('extended name',       ('read', 'write', )),
            # Blocking bad guys
            ('BadGuy',              ()),
            # All other users - every one not mentioned in the acl lines
            ('All',                 ('read', )),
            ('Anonymous',           ('read', )),
            )

        # Check rights
        for user, may in users:
            mayNot = [right for right in self.request.cfg.acl_rights_valid
                      if right not in may]
            # User should have these rights...
            for right in may:
                self.assert_(acl.may(self.request, user, right),
                    '"%(user)s" should be allowed to "%(right)s"' % locals())
            # But NOT these:
            for right in mayNot:
                self.failIf(acl.may(self.request, user, right),
                    '"%(user)s" should NOT be allowed to "%(right)s"' % locals())

    def testACLsWithoutEditLogEntry(self):
        """ tests what are the page rights if edit-log entry doesn't exist
            for a page where no access is given to
        """
        py.test.skip("test tricks out the caching system, page modifications without making an edit-log entry are not supported")
        import os
        from MoinMoin.Page import Page
        pagename = u'AutoCreatedMoinMoinTemporaryTestPage'

        result = self.request.user.may.write(pagename)
        page = Page(self.request, pagename)
        path = page.getPagePath(use_underlay=0, check_create=0)
        if os.path.exists(path):
            py.test.skip("%s exists. Won't overwrite exiting page" % self.dictPage)

        try:
            try:
                os.mkdir(path)
                revisionsDir = os.path.join(path, 'revisions')
                os.mkdir(revisionsDir)
                current = '00000001'
                file(os.path.join(path, 'current'), 'w').write('%s\n' % current)
                text = u'#acl All: \n'
                file(os.path.join(revisionsDir, current), 'w').write(text)
            except Exception, err:
                py.test.skip("Can not be create test page: %s" % err)

            assert not self.request.user.may.write(pagename)
        finally:
            if os.path.exists(path):
                import shutil
                shutil.rmtree(path, True)

coverage_modules = ['MoinMoin.security']
