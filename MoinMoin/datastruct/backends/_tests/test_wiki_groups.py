# -*- coding: iso-8859-1 -*-
"""
MoinMoin - MoinMoin.backends.wiki_group tests

@copyright: 2003-2004 by Juergen Hermann <jh@web.de>,
            2007,2009 by MoinMoin:ThomasWaldmann,
            2008 by MoinMoin:MelitaMihaljevic,
            2009 by MoinMoin:DmitrijsMilajevs,
            2010 by MoinMoin:ReimarBauer
@license: GNU GPL, see COPYING for details.
"""

import py

from flask import current_app as app
from flask import flaskg
from MoinMoin.datastruct.backends._tests import GroupsBackendTest
from MoinMoin.datastruct import GroupDoesNotExistError
from MoinMoin import security
from MoinMoin.user import User
from MoinMoin._tests import append_item, become_trusted, create_item, create_random_string_list


class TestWikiGroupBackend(GroupsBackendTest):

    # Suppose that default configuration for the groups is used which
    # is WikiGroups backend.

    def setup_method(self, method):
        become_trusted()
        for group, members in self.test_groups.iteritems():
            text = "This is a group item"
            create_item(group, text, groupmember=members)

    def test_rename_group_item(self):
        """
        Tests renaming of a group item.
        """
        become_trusted()
        text = u"This is a group item"
        item = create_item(u'SomeGroup', text, groupmember=["ExampleUser"])
        item.rename(u'AnotherGroup')

        result = u'ExampleUser' in flaskg.groups[u'AnotherGroup']
        assert result

        py.test.raises(GroupDoesNotExistError, lambda: flaskg.groups[u'SomeGroup'])

    def test_copy_group_item(self):
        """
        Tests copying a group item.
        """
        py.test.skip("item.copy() is not finished")

        become_trusted()
        text = u"This is a group item"
        item = create_item(u'SomeGroup', text, groupmember=["ExampleUser"])
        item.copy(u'SomeOtherGroup')

        result = u'ExampleUser' in flaskg.groups[u'SomeOtherGroup']
        assert result

        result = u'ExampleUser' in flaskg.groups[u'SomeGroup']
        assert result

    def test_appending_group_item(self):
        """
        Test scalability by appending a name to a large list of group members.
        """
        become_trusted()
        text = "This is a group item"
        # long list of users
        members = create_random_string_list(length=15, count=1234)
        test_user = create_random_string_list(length=15, count=1)[0]
        create_item(u'UserGroup', text, groupmember=members)
        append_item(u'UserGroup', text, groupmember=[test_user])
        result = test_user in flaskg.groups['UserGroup']

        assert result

    def test_user_addition_to_group_item(self):
        """
        Test addition of a username to a large list of group members.
        """
        become_trusted()

        # long list of users
        members = create_random_string_list()
        text = "This is a group item"

        create_item(u'UserGroup', text, groupmember=members)
        new_user = create_random_string_list(length=15, count=1)[0]
        append_item(u'UserGroup', text, groupmember=[new_user])

        result = new_user in flaskg.groups[u'UserGroup']
        assert result

    def test_member_removed_from_group_item(self):
        """
        Tests appending a member to a large list of group members and
        recreating the item without the member.
        """
        become_trusted()

        # long list of users
        members = create_random_string_list()
        text = u"This is a group item"
        create_item(u'UserGroup', text, groupmember=members)

        # updates the text with the text_user
        test_user = create_random_string_list(length=15, count=1)[0]
        create_item(u'UserGroup', text, groupmember=[test_user])
        result = test_user in flaskg.groups[u'UserGroup']
        assert result

        # updates the text without test_user
        create_item(u'UserGroup', text)
        result = test_user in flaskg.groups[u'UserGroup']
        assert not result

    def test_wiki_backend_item_acl_usergroupmember_item(self):
        """
        Test if the wiki group backend works with acl code.
        First check acl rights of a user that is not a member of group
        then add user member to an item group and check acl rights
        """
        become_trusted()
        text = u"This is a group item"
        create_item(u'NewGroup', text, groupmember=["ExampleUser"])

        acl_rights = ["NewGroup:read,write"]
        acl = security.AccessControlList(app.cfg, acl_rights)

        has_rights_before = acl.may(u"AnotherUser", "read")

        # update item - add AnotherUser to a item group NewGroup
        append_item(u'NewGroup', text, groupmember=["AnotherUser"])

        has_rights_after = acl.may(u"AnotherUser", "read")

        assert not has_rights_before, 'AnotherUser has no read rights because in the beginning he is not a member of a group item NewGroup'
        assert has_rights_after, 'AnotherUser must have read rights because after appenditem he is member of NewGroup'

coverage_modules = ['MoinMoin.datastruct.backends.wiki_groups']

