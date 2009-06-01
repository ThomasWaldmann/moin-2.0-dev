# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - ACL middleware

    This backend is a middleware implementing access control using ACLs (access
    control lists). It does not store any data, but uses a given backend for
    this.

    @copyright: 2003-2008 MoinMoin:ThomasWaldmann,
                2000-2004 Juergen Hermann <jh@web.de>,
                2003 Gustavo Niemeyer,
                2005 Oliver Graf,
                2007 Alexander Schremmer,
                2009 Christopher Denter
    @license: GNU GPL, see COPYING for details.
"""

from UserDict import DictMixin

from MoinMoin.items import ACL
from MoinMoin.security import AccessControlList

from MoinMoin.storage import Backend
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, AccessDeniedError

ADMIN = 'admin'
READ = 'read'
WRITE = 'write'
DELETE = 'delete'


class AclWrapperBackend(object):
    def __init__(self, request):
        self.request = request
        self.backend = request.cfg.data_backend
        self.username = request.user.name
        self.acl_hierarchic = request.cfg.acl_hierarchic
        self.acl_before = request.cfg.cache.acl_rights_before
        self.acl_default = request.cfg.cache.acl_rights_default
        self.acl_after = request.cfg.cache.acl_rights_after

    def __getattr__(self, attr):
        return getattr(self.backend, attr)

    def search_item(self, searchterm):
        for item in self.backend.search_item(searchterm):
            if self._may(item.name, READ):
                wrapped_item = AclWrapperItem(item, self)
                yield wrapped_item

    def get_item(self, itemname):
        if not self._may(itemname, READ):
            raise AccessDeniedError()
        real_item = self.backend.get_item(itemname)
        wrapped_item = AclWrapperItem(real_item, self)
        return wrapped_item

    def has_item(self, itemname):
        # We do not hide the sheer existance of items. When trying
        # to create an item with the same name, the user would notice anyway.
        return self.backend.has_item(itemname)

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
        revisions = []
        for revision in self.backend.history(reverse):
            if self._may(revision.item.name, READ):
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


class AclWrapperItem(object, DictMixin):
    def __init__(self, item, aclbackend):
        self._backend = aclbackend
        self._item = item
        self._may = aclbackend._may

    @property
    def name(self):
        return self._item.name

    def require_privilege(*privileges):
        def wrap(f):
            def wrapped_f(self, *args, **kwargs):
                for privilege in privileges:
                    if not self._may(self.name, privilege):
                        raise AccessDeniedError()
                return f(self, *args, **kwargs)
            return wrapped_f
        return wrap


    @require_privilege(WRITE)
    def __setitem__(self, key, value):
        return self._item.__setitem__(key, value)

    @require_privilege(WRITE)
    def __delitem__(self, key):
        return self._item.__delitem__(key)

    @require_privilege(READ)
    def __getitem__(self, key):
        return self._item.__getitem__(key)

    @require_privilege(READ)
    def keys(self):
        return self._item.keys()

    @require_privilege(WRITE)
    def change_metadata(self):
        return self._item.change_metadata()

    @require_privilege(WRITE)
    def publish_metadata(self):
        return self._item.publish_metadata()

    @require_privilege(READ)
    def get_revision(self, revno):
        # The revision returned here is immutable already.
        return self._item.get_revision(revno)

    @require_privilege(READ)
    def list_revisions(self):
        return self._item.list_revisions()

    @require_privilege(WRITE)
    def rename(self, newname):
        # XXX Special case since we need to check newname as well.
        #     Maybe find a proper solution.
        if not self._may(newname, WRITE):
            raise AccessDeniedError()
        return self._item.rename(newname)

    @require_privilege(WRITE)
    def commit(self):
        return self._item.commit()

    # XXX Does this even require a privilege?
    def rollback(self):
        return self._item.rollback()

    @require_privilege(WRITE)
    def create_revision(self, revno):
        wrapped_revision = AclWrappedNewRevision(self._item.create_revision(revno), self)
        return wrapped_revision


class AclWrappedNewRevision(object, DictMixin):
    def __init__(self, revision, item):
        self._revision = revision
        self._item = item
        self._may = item._may

        # It's ok to redirect here since item.commit() and item.create_revision
        # already perform permission checks.
        for attr in ('__delitem__', 'write'):
            setattr(self, attr, getattr(revision, attr))

    @property
    def timestamp(self):
        return self._revision.timestamp

    @property
    def size(self):
        return self._revision.size

    def __setitem__(self, key, value):
        """
        In order to store an ACL on a page you must have the ADMIN privilege.
        We must allow storing the preceeding revision's ACL in the new revision
        (i.e., keeping it), though.
        """
        if key == ACL:
            try:
                # This rev is not yet committed
                last_rev = self._item.get_revision(-1)
                last_acl = last_rev[ACL]
            except NoSuchRevisionError:
                last_acl = ''

            acl_changed = not (value == last_acl)

            if acl_changed and not self._may(self._item.name, ADMIN):
                raise AccessDeniedError()
        return self._revision.__setitem__(key, value)

    def __getitem__(self, key):
        return self._revision[key]
