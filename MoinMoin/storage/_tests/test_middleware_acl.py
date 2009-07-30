# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - ACLMiddleWare

    This defines tests for the ACLMiddleWare

    @copyright: 2009 MoinMoin:ChristopherDenter,
    @license: GNU GPL, see COPYING for details.
"""
from MoinMoin.items import ACL
from MoinMoin.storage.error import AccessDeniedError
from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.acl import AclWrapperBackend, AclWrapperItem, AclWrappedRevision
from MoinMoin.conftest import init_test_request
from MoinMoin._tests import wikiconfig

import py


class TestACLMiddleware(BackendTest):
    class Config(wikiconfig.Config):
        acl_rights_default = u"All:admin,read,write,destroy,create"

    def __init__(self):
        BackendTest.__init__(self, None)

    def create_backend(self):
        # Called before *each* testcase. Provides fresh backends every time.
        self.request = init_test_request(self.Config)
        return AclWrapperBackend(self.request)

    def kill_backend(self):
        pass


    def get_item(self, name):
        # Just as a shortcut
        return self.request.storage.get_item(name)

    def create_item_acl(self, name, acl):
        item = self.request.storage.create_item(name)
        rev = item.create_revision(0)
        rev[ACL] = acl
        item.commit()
        return item


    def test_noaccess(self):
        name = "noaccess"
        self.create_item_acl(name, "All:")
        assert py.test.raises(AccessDeniedError, self.get_item, name)

    def test_read_access_allowed(self):
        name = "readaccessallowed"
        self.create_item_acl(name, "All:read")
        # Should simply pass...
        item = self.get_item(name)

        # Should not...
        assert py.test.raises(AccessDeniedError, item.create_revision, 1)
        assert py.test.raises(AccessDeniedError, item.change_metadata)

    def test_write_after_create(self):
        name = "writeaftercreate"
        item = self.create_item_acl(name, "All:")
        assert py.test.raises(AccessDeniedError, item.create_revision, 1)

    def test_modify_without_acl_change(self):
        name = "copy_without_acl_change"
        acl = "All:read,write"
        self.create_item_acl(name, acl)
        item = self.get_item(name)
        rev = item.create_revision(1)
        # This should pass
        rev[ACL] = acl
        item.commit()

    def test_copy_with_acl_change(self):
        name = "copy_with_acl_change"
        acl = "All:read,write"
        self.create_item_acl(name, acl)
        item = self.get_item(name)
        rev = item.create_revision(1)
        py.test.raises(AccessDeniedError, rev.__setitem__, ACL, acl + ",write")

    def test_write_without_read(self):
        name = "write_but_not_read"
        acl = "All:write"
        item = self.request.storage.create_item(name)
        rev = item.create_revision(0)
        rev[ACL] = acl
        rev.write("My name is " + name)
        item.commit()

        py.test.raises(AccessDeniedError, item.get_revision, -1)
        py.test.raises(AccessDeniedError, item.get_revision, 0)

    def test_rev_item_wrapped(self):
        item = self.backend.create_item("foo")
        rev = item.create_revision(0)
        rev.write("me and my item will be wrapped")
        item.commit()
        stored_rev = item.get_revision(0)

        assert isinstance(stored_rev, AclWrappedRevision)
        assert isinstance(rev, AclWrappedRevision)
        assert isinstance(item, AclWrapperItem)
        assert isinstance(rev.item, AclWrapperItem)
        assert isinstance(stored_rev.item, AclWrapperItem)


