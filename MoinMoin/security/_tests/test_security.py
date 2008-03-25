# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MoinMoin.security Tests

    TODO: when refactoring this, do not use "iter" (is a builtin)

    @copyright: 2003-2004 by Juergen Hermann <jh@web.de>,
                2007 by MoinMoin:ReimarBauer,
                2007 by MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import py

from MoinMoin import security

acliter = security.ACLStringIterator

class TestACLStringIterator(object):

    def setup_method(self, method):
        self.config = self.TestConfig(defaults=['acl_rights_valid', 'acl_rights_before'])
    def teardown_method(self, method):
        del self.config

    def testEmpty(self):
        """ security: empty acl string raise StopIteration """
        iter = acliter(self.request.cfg.acl_rights_valid, '')
        py.test.raises(StopIteration, iter.next)

    def testWhiteSpace(self):
        """ security: white space acl string raise StopIteration """
        iter = acliter(self.request.cfg.acl_rights_valid, '       ')
        py.test.raises(StopIteration, iter.next)

    def testDefault(self):
        """ security: default meta acl """
        iter = acliter(self.request.cfg.acl_rights_valid, 'Default Default')
        for mod, entries, rights in iter:
            assert entries == ['Default']
            assert rights == []

    def testEmptyRights(self):
        """ security: empty rights """
        iter = acliter(self.request.cfg.acl_rights_valid, 'WikiName:')
        mod, entries, rights = iter.next()
        assert entries == ['WikiName']
        assert rights == []

    def testSingleWikiNameSingleWrite(self):
        """ security: single wiki name, single right """
        iter = acliter(self.request.cfg.acl_rights_valid, 'WikiName:read')
        mod, entries, rights = iter.next()
        assert entries == ['WikiName']
        assert rights == ['read']

    def testMultipleWikiNameAndRights(self):
        """ security: multiple wiki names and rights """
        iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne,UserTwo:read,write')
        mod, entries, rights = iter.next()
        assert entries == ['UserOne', 'UserTwo']
        assert rights == ['read', 'write']

    def testMultipleWikiNameAndRightsSpaces(self):
        """ security: multiple names with spaces """
        iter = acliter(self.request.cfg.acl_rights_valid, 'user one,user two:read')
        mod, entries, rights = iter.next()
        assert entries == ['user one', 'user two']
        assert rights == ['read']

    def testMultipleEntries(self):
        """ security: multiple entries """
        iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne:read,write UserTwo:read All:')
        mod, entries, rights = iter.next()
        assert entries == ['UserOne']
        assert rights == ['read', 'write']
        mod, entries, rights = iter.next()
        assert entries == ['UserTwo']
        assert rights == ['read']
        mod, entries, rights = iter.next()
        assert entries == ['All']
        assert rights == []

    def testNameWithSpaces(self):
        """ security: single name with spaces """
        iter = acliter(self.request.cfg.acl_rights_valid, 'user one:read')
        mod, entries, rights = iter.next()
        assert entries == ['user one']
        assert rights == ['read']

    def testMultipleEntriesWithSpaces(self):
        """ security: multiple entries with spaces """
        iter = acliter(self.request.cfg.acl_rights_valid, 'user one:read,write user two:read')
        mod, entries, rights = iter.next()
        assert entries == ['user one']
        assert rights == ['read', 'write']
        mod, entries, rights = iter.next()
        assert entries == ['user two']
        assert rights == ['read']

    def testMixedNames(self):
        """ security: mixed wiki names and names with spaces """
        iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne,user two:read,write user three,UserFour:read')
        mod, entries, rights = iter.next()
        assert entries == ['UserOne', 'user two']
        assert rights == ['read', 'write']
        mod, entries, rights = iter.next()
        assert entries == ['user three', 'UserFour']
        assert rights == ['read']

    def testModifier(self):
        """ security: acl modifiers """
        iter = acliter(self.request.cfg.acl_rights_valid, '+UserOne:read -UserTwo:')
        mod, entries, rights = iter.next()
        assert mod == '+'
        assert entries == ['UserOne']
        assert rights == ['read']
        mod, entries, rights = iter.next()
        assert mod == '-'
        assert entries == ['UserTwo']
        assert rights == []

    def testIgnoreInvalidACL(self):
        """ security: ignore invalid acl

        The last part of this acl can not be parsed. If it ends with :
        then it will be parsed as one name with spaces.
        """
        iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne:read user two is ignored')
        mod, entries, rights = iter.next()
        assert entries == ['UserOne']
        assert rights == ['read']
        py.test.raises(StopIteration, iter.next)

    def testEmptyNamesWithRight(self):
        """ security: empty names with rights

        The documents does not talk about this case, may() should ignore
        the rights because there is no entry.
        """
        iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne:read :read All:')
        mod, entries, rights = iter.next()
        assert entries == ['UserOne']
        assert rights == ['read']
        mod, entries, rights = iter.next()
        assert entries == []
        assert rights == ['read']
        mod, entries, rights = iter.next()
        assert entries == ['All']
        assert rights == []

    def testIgnodeInvalidRights(self):
        """ security: ignore rights not in acl_rights_valid """
        iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne:read,sing,write,drink,sleep')
        mod, entries, rights = iter.next()
        assert rights == ['read', 'write']

    def testBadGuy(self):
        """ security: bad guy may not allowed anything

        This test was failing on the apply acl rights test.
        """
        iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne:read,write BadGuy: All:read')
        mod, entries, rights = iter.next()
        mod, entries, rights = iter.next()
        assert entries == ['BadGuy']
        assert rights == []

    def testAllowExtraWhitespace(self):
        """ security: allow extra white space between entries """
        iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne,user two:read,write   user three,UserFour:read  All:')
        mod, entries, rights = iter.next()
        assert  entries == ['UserOne', 'user two']
        assert rights == ['read', 'write']
        mod, entries, rights = iter.next()
        assert entries == ['user three', 'UserFour']
        assert rights == ['read']
        mod, entries, rights = iter.next()
        assert entries == ['All']
        assert rights == []


class TestAcl(object):
    """ security: testing access control list

    TO DO: test unknown user?
    """
    def setup_method(self, method):
        # Backup user
        self.config = self.TestConfig(defaults=['acl_rights_valid', 'acl_rights_before'])
        self.savedUser = self.request.user.name

    def teardown_method(self, method):
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
            ('Admin1', ('read', 'write', 'admin', 'revert', 'delete')),
            ('Admin2', ('read', 'write', 'admin', 'revert', 'delete')),
            ('Admin3', ('read', 'write', 'admin')),
            ('JoeDoe', ('read', 'write')),
            ('SomeGuy', ('read', )),
            # Extended names or mix of extended and CamelCase
            ('name with spaces', ('read', 'write', )),
            ('another one', ('read', 'write', )),
            ('CamelCase', ('read', 'write', )),
            ('extended name', ('read', 'write', )),
            # Blocking bad guys
            ('BadGuy', ()),
            # All other users - every one not mentioned in the acl lines
            ('All', ('read', )),
            ('Anonymous', ('read', )),
            )

        # Check rights
        for user, may in users:
            mayNot = [right for right in self.request.cfg.acl_rights_valid
                      if right not in may]
            # User should have these rights...
            for right in may:
                assert acl.may(self.request, user, right)
            # But NOT these:
            for right in mayNot:
                assert not acl.may(self.request, user, right)

    def testACLsWithoutEditLogEntry(self):
        """ tests what are the page rights if edit-log entry doesn't exist
            for a page where no access is given to
        """
        pagename = u'AutoCreatedMoinMoinACLTestPage'

        self.request.cfg.data_backend.create_item(pagename)
        self.request.cfg.data_backend.create_revision(pagename, 1)
        data = self.request.cfg.data_backend.get_data_backend(pagename, 1)
        data.write(u'#acl All: \n')
        data.close()

        assert not self.request.user.may.write(pagename)

        self.request.cfg.data_backend.remove_item(pagename)

coverage_modules = ['MoinMoin.security']

