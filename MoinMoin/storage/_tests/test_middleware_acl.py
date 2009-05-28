# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - ACLMiddleWare

    This defines tests for the ACLMiddleWare

    @copyright: 2009 MoinMoin:ChristopherDenter,
    @license: GNU GPL, see COPYING for details.
"""
from MoinMoin.Page import ACL
from MoinMoin.storage.backends.acl import AccessDeniedError

import py


class TestACLMiddleware(object):
    """
    Test the AMW
    """

    def get_item(self, name):
        # Just as a shortcut
        return self.request.data_backend.get_item(name)

    def create_item_acl(self, name, acl):
        item = self.request.data_backend.create_item(name)
        rev = item.create_revision(0)
        rev[ACL] = acl
        item.commit()
        return item

    def test_noaccess(self):
        access = "noaccess"
        self.create_item_acl(access, "All:")
        assert py.test.raises(AccessDeniedError, self.get_item, access)

    def test_read_access_allowed(self):
        access = "readaccessallowed"
        self.create_item_acl(access, "All:read")
        # Should simply pass...
        item = self.get_item(access)

        # Should not...
        assert py.test.raises(AccessDeniedError, item.create_revision, 1)
        assert py.test.raises(AccessDeniedError, item.change_metadata)

    def test_write_after_create(self):
        access = "writeaftercreate"
        item = self.create_item_acl(access, "All:")
        assert py.test.raises(AccessDeniedError, item.create_revision, 1)
