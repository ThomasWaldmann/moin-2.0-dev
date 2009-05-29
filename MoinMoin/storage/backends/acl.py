# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - ACL middleware

    This backend is a middleware implementing access control using ACLs (access
    control lists). It does not store any data, but uses a given backend for
    this.

    TODO: needs more work, does not work yet

    @copyright: 2003-2008 MoinMoin:ThomasWaldmann,
                2000-2004 Juergen Hermann <jh@web.de>,
                2003 Gustavo Niemeyer,
                2005 Oliver Graf,
                2007 Alexander Schremmer
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.Page import ACL
from MoinMoin.security import AccessControlList

from MoinMoin.storage import Backend
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError

ADMIN = 'admin'
READ = 'read'
WRITE = 'write'
DELETE = 'delete'
REVERT = 'revert'

class AccessDeniedError(Exception):
    """ raised when ACLs deny access to item """


class AclWrapperBackend(Backend):
    def __init__(self, request):
        self.request = request
        self.backend = request.cfg.data_backend
        self.username = request.user.name
        self.acl_hierarchic = request.cfg.acl_hierarchic
        self.acl_before = request.cfg.cache.acl_rights_before
        self.acl_default = request.cfg.cache.acl_rights_default
        self.acl_after = request.cfg.cache.acl_rights_after

    def get_item(self, itemname):
        if not self._may(itemname, READ):
            raise AccessDeniedError()
        real_item = self.backend.get_item(itemname)
        wrapped_item = AclWrapperItem(real_item, self)
        return wrapped_item

    def create_item(self, itemname):
        if not self._may(itemname, WRITE):
            raise AccessDeniedError()
        real_item = self.backend.create_item(itemname)
        wrapped_item = AclWrapperItem(real_item, self)
        return wrapped_item

    def iteritems(self):
        for item in self.backend.iteritems():
            if self._may(item.name, READ):
                yield item

    def history(self, reverse=True):
        """
        Returns an iterator over ALL revisions of ALL items stored in the
        backend.

        If reverse is True (default), give history in reverse revision
        timestamp order, otherwise in revision timestamp order.

        Note: some functionality (e.g. completely cloning one storage into
              another) requires that the iterator goes over really every
              revision we have).
        """
        revisions = []
        for revision in self.backend.history(reverse):
            # XXX check
            revisions.append(revision)

        # TODO: SORT THIS ACCORDINGLY!
        return iter(revisions)


    def _get_acl(self, itemname):
        """ get ACL strings from metadata and return ACL object """
        try:
            item = self.backend.get_item(itemname)
            # we always use the ACLs set on the latest revision:
            current_rev = item.get_revision(-1)
            acls = current_rev[ACL]
        except (NoSuchItemError, KeyError):
            # do not use default acl here
            acls = []
        if not isinstance(acls, (tuple, list)):
            acls = (acls, )
        return AccessControlList(self.request.cfg, acls)

    def _may(self, itemname, right):
        """ Check if self.username may have <right> access on item <itemname>.

        For self.acl_hierarchic=False we just check the item in question.

        For self.acl_hierarchic=True we, we check each item in the hierarchy. We
        start with the deepest item and recurse to the top of the tree.
        If one of those permits, True is returned.

        For both configurations, we check acl_rights_before before the item/default
        acl and acl_rights_after after the item/default acl, of course.

        @param itemname: item to get permissions from
        @param right: the right to check

        @rtype: bool
        @return: True if you have permission or False
        """
        request = self.request
        username = self.username

        allowed = self.acl_before.may(request, username, right)
        if allowed is not None:
            return allowed

        if self.acl_hierarchic:
            items = itemname.split('/') # create item hierarchy list
            some_acl = False
            for i in range(len(items), 0, -1):
                # Create the next pagename in the hierarchy
                # starting at the leaf, going to the root
                name = '/'.join(items[:i])
                acl = self._get_acl(name)
                if acl.acl:
                    some_acl = True
                    allowed = acl.may(request, username, right)
                    if allowed is not None:
                        return allowed
            if not some_acl:
                allowed = self.acl_default.may(request, username, right)
                if allowed is not None:
                    return allowed
        else:
            acl = self._get_acl(itemname)
            allowed = acl.may(request, username, right)
            if allowed is not None:
                return allowed

        allowed = self.acl_after.may(request, username, right)
        if allowed is not None:
            return allowed

        return False


class AclWrapperItem(object):
    def __init__(self, item, aclbackend):
        self._backend = aclbackend
        self._item = item
        self._may = aclbackend._may

    @property
    def name(self):
        return self._item.name

    def __setitem__(self, key, value):
        if not self._may(self.name, WRITE):
            raise AccessDeniedError()
        self._item.__setitem__(key, value)

    def commit(self):
        if not self._may(self.name, WRITE):
            raise AccessDeniedError()
        return self._item.commit()

    def create_revision(self, revno):
        if not self._may(self.name, WRITE):
            raise AccessDeniedError()
        return self._item.create_revision(revno)

    def change_metadata(self):
        if not self._may(self.name, WRITE):
            raise AccessDeniedError()
        return self._item.change_metadata()

    def rename(self, newname):
        if not self._may(self.name, DELETE):
            raise AccessDeniedError()
        if not self._may(newname, WRITE):
            raise AccessDeniedError()
        return self._item.rename_item(newname)

    def publish_metadata(self):
        if not self._may(self.name, WRITE):
            raise AccessDeniedError()
        return self._item.publish_metadata()

    def get_revision(self, revno):
        if not self._may(self.name, READ):
            raise AccessDeniedError()
        return self._item.get_revision(revno)

