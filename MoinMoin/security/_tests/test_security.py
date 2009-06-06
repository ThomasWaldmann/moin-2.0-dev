# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MoinMoin.security Tests

    @copyright: 2003-2004 by Juergen Hermann <jh@web.de>,
                2007 by MoinMoin:ReimarBauer,
                2007,2009 by MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import py

from MoinMoin import security
acliter = security.ACLStringIterator
AccessControlList = security.AccessControlList

from MoinMoin.user import User

from MoinMoin._tests import create_page as create_item

class TestACLStringIterator(object):

    def testEmpty(self):
        """ security: empty acl string raise StopIteration """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, '')
        py.test.raises(StopIteration, acl_iter.next)

    def testWhiteSpace(self):
        """ security: white space acl string raise StopIteration """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, '       ')
        py.test.raises(StopIteration, acl_iter.next)

    def testDefault(self):
        """ security: default meta acl """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, 'Default Default')
        for mod, entries, rights in acl_iter:
            assert entries == ['Default']
            assert rights == []

    def testEmptyRights(self):
        """ security: empty rights """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, 'WikiName:')
        mod, entries, rights = acl_iter.next()
        assert entries == ['WikiName']
        assert rights == []

    def testSingleWikiNameSingleWrite(self):
        """ security: single wiki name, single right """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, 'WikiName:read')
        mod, entries, rights = acl_iter.next()
        assert entries == ['WikiName']
        assert rights == ['read']

    def testMultipleWikiNameAndRights(self):
        """ security: multiple wiki names and rights """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne,UserTwo:read,write')
        mod, entries, rights = acl_iter.next()
        assert entries == ['UserOne', 'UserTwo']
        assert rights == ['read', 'write']

    def testMultipleWikiNameAndRightsSpaces(self):
        """ security: multiple names with spaces """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, 'user one,user two:read')
        mod, entries, rights = acl_iter.next()
        assert entries == ['user one', 'user two']
        assert rights == ['read']

    def testMultipleEntries(self):
        """ security: multiple entries """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne:read,write UserTwo:read All:')
        mod, entries, rights = acl_iter.next()
        assert entries == ['UserOne']
        assert rights == ['read', 'write']
        mod, entries, rights = acl_iter.next()
        assert entries == ['UserTwo']
        assert rights == ['read']
        mod, entries, rights = acl_iter.next()
        assert entries == ['All']
        assert rights == []

    def testNameWithSpaces(self):
        """ security: single name with spaces """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, 'user one:read')
        mod, entries, rights = acl_iter.next()
        assert entries == ['user one']
        assert rights == ['read']

    def testMultipleEntriesWithSpaces(self):
        """ security: multiple entries with spaces """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, 'user one:read,write user two:read')
        mod, entries, rights = acl_iter.next()
        assert entries == ['user one']
        assert rights == ['read', 'write']
        mod, entries, rights = acl_iter.next()
        assert entries == ['user two']
        assert rights == ['read']

    def testMixedNames(self):
        """ security: mixed wiki names and names with spaces """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne,user two:read,write user three,UserFour:read')
        mod, entries, rights = acl_iter.next()
        assert entries == ['UserOne', 'user two']
        assert rights == ['read', 'write']
        mod, entries, rights = acl_iter.next()
        assert entries == ['user three', 'UserFour']
        assert rights == ['read']

    def testModifier(self):
        """ security: acl modifiers """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, '+UserOne:read -UserTwo:')
        mod, entries, rights = acl_iter.next()
        assert mod == '+'
        assert entries == ['UserOne']
        assert rights == ['read']
        mod, entries, rights = acl_iter.next()
        assert mod == '-'
        assert entries == ['UserTwo']
        assert rights == []

    def testIgnoreInvalidACL(self):
        """ security: ignore invalid acl

        The last part of this acl can not be parsed. If it ends with :
        then it will be parsed as one name with spaces.
        """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne:read user two is ignored')
        mod, entries, rights = acl_iter.next()
        assert entries == ['UserOne']
        assert rights == ['read']
        py.test.raises(StopIteration, acl_iter.next)

    def testEmptyNamesWithRight(self):
        """ security: empty names with rights

        The documents does not talk about this case, may() should ignore
        the rights because there is no entry.
        """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne:read :read All:')
        mod, entries, rights = acl_iter.next()
        assert entries == ['UserOne']
        assert rights == ['read']
        mod, entries, rights = acl_iter.next()
        assert entries == []
        assert rights == ['read']
        mod, entries, rights = acl_iter.next()
        assert entries == ['All']
        assert rights == []

    def testIgnodeInvalidRights(self):
        """ security: ignore rights not in acl_rights_valid """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne:read,sing,write,drink,sleep')
        mod, entries, rights = acl_iter.next()
        assert rights == ['read', 'write']

    def testBadGuy(self):
        """ security: bad guy may not allowed anything

        This test was failing on the apply acl rights test.
        """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne:read,write BadGuy: All:read')
        mod, entries, rights = acl_iter.next()
        mod, entries, rights = acl_iter.next()
        assert entries == ['BadGuy']
        assert rights == []

    def testAllowExtraWhitespace(self):
        """ security: allow extra white space between entries """
        acl_iter = acliter(self.request.cfg.acl_rights_valid, 'UserOne,user two:read,write   user three,UserFour:read  All:')
        mod, entries, rights = acl_iter.next()
        assert  entries == ['UserOne', 'user two']
        assert rights == ['read', 'write']
        mod, entries, rights = acl_iter.next()
        assert entries == ['user three', 'UserFour']
        assert rights == ['read']
        mod, entries, rights = acl_iter.next()
        assert entries == ['All']
        assert rights == []


class TestAcl(object):
    """ security: testing access control list

    TO DO: test unknown user?
    """
    def setup_method(self, method):
        # Backup user
        self.savedUser = self.request.user.name

    def teardown_method(self, method):
        # Restore user
        self.request.user.name = self.savedUser

    def testApplyACLByUser(self):
        """ security: applying acl by user name"""
        # This acl string...
        acl_rights = [
            "Admin1,Admin2:read,write,delete,admin  "
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
            ('Admin1', ('read', 'write', 'admin', 'delete')),
            ('Admin2', ('read', 'write', 'admin', 'delete')),
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


class TestItemAcls(object):
    """ security: real-life access control list on items testing
    """
    mainitem_name = u'AclTestMainItem'
    subitem1_name = u'AclTestMainItem/SubItem1'
    subitem2_name = u'AclTestMainItem/SubItem2'
    items = [
        # itemname, acl, content
        (mainitem_name, u'JoeDoe: JaneDoe:read,write', u'Foo!'),
        # acl None means: "no acl given in item metadata" - this will trigger
        # usage of default acl (non-hierarchical) or usage of default acl and
        # inheritance (hierarchical):
        (subitem1_name, None, u'FooFoo!'),
        # acl u'' means: "empty acl (no rights for noone) given" - this will
        # INHIBIT usage of default acl / inheritance (we DO HAVE an item acl,
        # it is just empty!):
        (subitem2_name, u'', u'BarBar!'),
    ]

    from MoinMoin._tests import wikiconfig
    class Config(wikiconfig.Config):
        acl_rights_before = u"WikiAdmin:admin,read,write,delete"
        acl_rights_default = u"All:read,write"
        acl_rights_after = u"All:read"
        acl_hierarchic = False

    def setup_class(self):
        # Backup user
        self.savedUser = self.request.user.name
        self.request.user = User(self.request, auth_username=u'WikiAdmin')
        self.request.user.valid = True

        for item_name, item_acl, item_content in self.items:
            create_item(self.request, item_name, item_content, acl=item_acl)

    def teardown_class(self):
        # Restore user
        self.request.user.name = self.savedUser

    def testItemACLs(self):
        """ security: test item acls """
        tests = [
            # hierarchic, itemname, username, expected_rights
            (False, self.mainitem_name, u'WikiAdmin', ['read', 'write', 'admin', 'delete']),
            (True,  self.mainitem_name, u'WikiAdmin', ['read', 'write', 'admin', 'delete']),
            (False, self.mainitem_name, u'AnyUser', ['read']), # by after acl
            (True,  self.mainitem_name, u'AnyUser', ['read']), # by after acl
            (False, self.mainitem_name, u'JaneDoe', ['read', 'write']), # by item acl
            (True,  self.mainitem_name, u'JaneDoe', ['read', 'write']), # by item acl
            (False, self.mainitem_name, u'JoeDoe', []), # by item acl
            (True,  self.mainitem_name, u'JoeDoe', []), # by item acl
            (False, self.subitem1_name, u'WikiAdmin', ['read', 'write', 'admin', 'delete']),
            (True,  self.subitem1_name, u'WikiAdmin', ['read', 'write', 'admin', 'delete']),
            (False, self.subitem1_name, u'AnyUser', ['read', 'write']), # by default acl
            (True,  self.subitem1_name, u'AnyUser', ['read']), # by after acl
            (False, self.subitem1_name, u'JoeDoe', ['read', 'write']), # by default acl
            (True,  self.subitem1_name, u'JoeDoe', []), # by inherited acl from main item
            (False, self.subitem1_name, u'JaneDoe', ['read', 'write']), # by default acl
            (True,  self.subitem1_name, u'JaneDoe', ['read', 'write']), # by inherited acl from main item
            (False, self.subitem2_name, u'WikiAdmin', ['read', 'write', 'admin', 'delete']),
            (True,  self.subitem2_name, u'WikiAdmin', ['read', 'write', 'admin', 'delete']),
            (False, self.subitem2_name, u'AnyUser', ['read']), # by after acl
            (True,  self.subitem2_name, u'AnyUser', ['read']), # by after acl
            (False, self.subitem2_name, u'JoeDoe', ['read']), # by after acl
            (True,  self.subitem2_name, u'JoeDoe', ['read']), # by after acl
            (False, self.subitem2_name, u'JaneDoe', ['read']), # by after acl
            (True,  self.subitem2_name, u'JaneDoe', ['read']), # by after acl
        ]

        for hierarchic, itemname, username, may in tests:
            u = User(self.request, auth_username=username)
            u.valid = True

            def _have_right(u, right, itemname, hierarchic):
                self.request.cfg.acl_hierarchic = hierarchic
                self.request.user = u
                can_access = getattr(u.may, right)(itemname)
                assert can_access, "%r may %s %r (%s)" % (u.name, right, itemname, ['normal', 'hierarchic'][hierarchic])

            # User should have these rights...
            for right in may:
                yield _have_right, u, right, itemname, hierarchic

            def _not_have_right(u, right, itemname, hierarchic):
                self.request.cfg.acl_hierarchic = hierarchic
                self.request.user = u
                can_access = getattr(u.may, right)(itemname)
                assert not can_access, "%r may not %s %r (%s)" % (u.name, right, itemname, ['normal', 'hierarchic'][hierarchic])

            # User should NOT have these rights:
            mayNot = [right for right in self.request.cfg.acl_rights_valid
                      if right not in may]
            for right in mayNot:
                yield _not_have_right, u, right, itemname, hierarchic

coverage_modules = ['MoinMoin.security']
