# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - ACL Middleware

    This backend is a middleware implementing access control using ACLs (access
    control lists) and is referred to as AMW (ACL MiddleWare) hereafter.
    It does not store any data, but uses a given backend for this.
    This middleware is injected between the user of the storage API and the actual
    backend used for storage. It is independent of the backend being used.
    Instances of the AMW are bound to individual request objects. The user whose
    permissions the AMW checks is hence obtained by a lookup on the request object.
    The backend itself (and the objects it returns) need to be wrapped in order
    to make sure that no object of the real backend is (directly or indirectly)
    made accessible to the user of the API.
    The real backend is still available as an attribute of request.cfg and can
    be used by conversion utilities or for similar tasks.
    Regular users of the storage API, such as the views that modify an item,
    *MUST NOT*, in any way, use the real backend unless the author knows *exactly*
    what he's doing (as this may introduce security bugs without the code actually
    being broken).

    The classes wrapped are:
        * AclWrapperBackend (wraps MoinMoin.storage.Backend)
        * AclWrapperItem (wraps MoinMoin.storage.Item)
        * AclWrappedRevision (wraps MoinMoin.storage.Revision)

    MoinMoin.storage.StoredRevision is not wrapped since it's read-only by design
    anyway, and an object thereof can only be obtained by the dedicated methods
    of the Item class which are, of course, wrapped.

    When an attribute is 'wrapped' it means that, in this context, the user's
    permissions are checked prior to attribute usage. If the user may not perform
    the action he intended to perform, an AccessDeniedError is raised.
    Otherwise the action is performed on the respective attribute of the real backend.
    It is important to note here that the outcome of such an action may need to
    be wrapped itself, as is the case when items or revisions are returned.

    All wrapped classes must, of course, adhere to the normal storage API.

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

from MoinMoin.storage import Item, NewRevision, StoredRevision
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, AccessDeniedError

ADMIN = 'admin'
READ = 'read'
WRITE = 'write'
# One may decide that only items that have been created by a trusted user can be edited.
CREATE = 'create'
DESTROY = 'destroy'


class AclWrapperBackend(object):
    """
    The AMW is bound to a specific request. The actual backend is retrieved
    from the request. Any method that is in some way relevant to security needs
    to be wrapped in order to ensure the user has the permissions necessary to
    perform the desired action.
    Note: This may *not* inherit from MoinMoin.storage.Backend because that would
    break our __getattr__ attribute 'redirects' (which are necessary because a backend
    implementor may decide to use his own helper functions which the items and revisions
    will still try to call).
    """
    def __init__(self, request, backend, hierarchic=False, before="", default="", after=""):
        self.request = request
        cfg = request.cfg
        self.backend = backend
        self.hierarchic = hierarchic
        self.before = AccessControlList(cfg, [before])
        self.default = AccessControlList(cfg, [default])
        self.after = AccessControlList(cfg, [after])

    def __getattr__(self, attr):
        # Attributes that this backend does not define itself are just looked
        # up on the real backend.
        return getattr(self.backend, attr)

    def search_item(self, searchterm):
        """
        @see: Backend.search_item.__doc__
        """
        for item in self.backend.search_item(searchterm):
            if self._may(item.name, READ):
                # The item returned needs to be wrapped because otherwise the
                # item's methods (like create_revision) wouldn't be wrapped.
                wrapped_item = AclWrapperItem(item, self)
                yield wrapped_item

    def get_item(self, itemname):
        """
        @see: Backend.get_item.__doc__
        """
        if not self._may(itemname, READ):
            raise AccessDeniedError(self.request.user.name, READ, itemname)
        real_item = self.backend.get_item(itemname)
        # Wrap the item here as well.
        wrapped_item = AclWrapperItem(real_item, self)
        return wrapped_item

    def has_item(self, itemname):
        """
        @see: Backend.has_item.__doc__
        """
        # We do not hide the sheer existance of items. When trying
        # to create an item with the same name, the user would notice anyway.
        return self.backend.has_item(itemname)

    def create_item(self, itemname):
        """
        @see: Backend.create_item.__doc__
        """
        if not self._may(itemname, CREATE):
            raise AccessDeniedError(self.request.user.name, CREATE, itemname)
        real_item = self.backend.create_item(itemname)
        # Wrap item.
        wrapped_item = AclWrapperItem(real_item, self)
        return wrapped_item

    def iteritems(self):
        """
        @see: Backend.iteritems.__doc__
        """
        for item in self.backend.iteritems():
            if self._may(item.name, READ):
                yield AclWrapperItem(item, self)

    def history(self, reverse=True):
        """
        @see: Backend.history.__doc__
        """
        for revision in self.backend.history(reverse):
            if self._may(revision.item.name, READ):
                # The revisions returned here should only be StoredRevisions.
                # We wrap them nevertheless to be sure. Esp. revision.item
                # would otherwise give access to an unwrapped item.
                item = revision.item
                item = AclWrapperItem(item, self)
                revision = AclWrappedRevision(revision, item)
                yield revision

    def _get_acl(self, itemname):
        """
        Get ACL strings from the last revision's metadata and return ACL object.
        """
        try:
            item = self.backend.get_item(itemname)
            # we always use the ACLs set on the latest revision:
            current_rev = item.get_revision(-1)
            acls = current_rev[ACL]
        except (NoSuchItemError, NoSuchRevisionError, KeyError):
            # do not use default acl here
            acls = []
        if not isinstance(acls, (tuple, list)):
            acls = (acls, )
        return AccessControlList(self.request.cfg, acls)

    def _may(self, itemname, right):
        """ Check if self.username may have <right> access on item <itemname>.

        For hierarchic=False we just check the item in question.

        For hierarchic=True we, we check each item in the hierarchy. We
        start with the deepest item and recurse to the top of the tree.
        If one of those permits, True is returned.
        This is done *only* if there is *no ACL at all* (not even an empty one)
        on the items we 'recurse over'.

        For both configurations, we check `before` before the item/default
        acl and `after` after the item/default acl, of course.

        `default` is only used if there is no ACL on the item (and none on
        any of the item's parents when using hierarchic.)

        @param itemname: item to get permissions from
        @param right: the right to check

        @rtype: bool
        @return: True if you have permission or False
        """
        request = self.request
        username = request.user.name

        allowed = self.before.may(request, username, right)
        if allowed is not None:
            return allowed

        if self.hierarchic:
            items = itemname.split('/') # create item hierarchy list
            some_acl = False
            for i in range(len(items), 0, -1):
                # Create the next pagename in the hierarchy
                # starting at the leaf, going to the root
                name = '/'.join(items[:i])
                acl = self._get_acl(name)
                if acl.has_acl():
                    some_acl = True
                    allowed = acl.may(request, username, right)
                    if allowed is not None:
                        return allowed
                    # If the item has an acl (even one that doesn't match) we *do not*
                    # check the parents. We only check the parents if there's no acl on
                    # the item at all.
                    break
            if not some_acl:
                allowed = self.default.may(request, username, right)
                if allowed is not None:
                    return allowed
        else:
            acl = self._get_acl(itemname)
            if acl.has_acl():
                allowed = acl.may(request, username, right)
                if allowed is not None:
                    return allowed
            else:
                allowed = self.default.may(request, username, right)
                if allowed is not None:
                    return allowed

        allowed = self.after.may(request, username, right)
        if allowed is not None:
            return allowed

        return False


class AclWrapperItem(Item):
    """
    Similar to AclWrapperBackend.
    """
    def __init__(self, item, aclbackend):
        self._backend = aclbackend
        self._item = item
        self._may = aclbackend._may

    @property
    def name(self):
        """
        @see: Item.name.__doc__
        """
        return self._item.name

    # needed by storage.serialization:
    @property
    def element_name(self):
        return self._item.element_name
    @property
    def element_attrs(self):
        return self._item.element_attrs

    def require_privilege(*privileges):
        """
        This decorator is used in order to avoid code duplication
        when checking a user's permissions. It allows providing arguments
        that represent the permissions to check, such as READ and WRITE
        (see module level constants; don't pass strings, please).
        """
        def wrap(f):
            def wrapped_f(self, *args, **kwargs):
                for privilege in privileges:
                    if not self._may(self.name, privilege):
                        username = self._backend.request.user.name
                        raise AccessDeniedError(username, privilege, self.name)
                return f(self, *args, **kwargs)
            return wrapped_f
        return wrap


    @require_privilege(WRITE)
    def __setitem__(self, key, value):
        """
        @see: Item.__setitem__.__doc__
        """
        return self._item.__setitem__(key, value)

    @require_privilege(WRITE)
    def __delitem__(self, key):
        """
        @see: Item.__delitem__.__doc__
        """
        return self._item.__delitem__(key)

    @require_privilege(READ)
    def __getitem__(self, key):
        """
        @see: Item.__getitem__.__doc__
        """
        return self._item.__getitem__(key)

    @require_privilege(READ)
    def keys(self):
        """
        @see: Item.keys.__doc__
        """
        return self._item.keys()

    @require_privilege(WRITE)
    def change_metadata(self):
        """
        @see: Item.change_metadata.__doc__
        """
        return self._item.change_metadata()

    @require_privilege(WRITE)
    def publish_metadata(self):
        """
        @see: Item.publish_metadata.__doc__
        """
        return self._item.publish_metadata()

    @require_privilege(READ)
    def get_revision(self, revno):
        """
        @see: Item.get_revision.__doc__
        """
        return AclWrappedRevision(self._item.get_revision(revno), self)

    @require_privilege(READ)
    def list_revisions(self):
        """
        @see: Item.list_revisions.__doc__
        """
        return self._item.list_revisions()

    @require_privilege(READ, WRITE)
    def rename(self, newname):
        """
        Rename item from name (src) to newname (dst).
        Note that there is no special rename privilege. By taking other
        privileges into account, we implicitly perform the permission check here.
        This checks R/W at src and W/C at dst. This combination was chosen for
        the following reasons:
         * It is the most intuitive of the possible solutions.
         * If we'd only check for R at src, everybody would be able to rename even
           ImmutablePages if there is a writable/creatable name somewhere else
           (e.g., Trash/).
         * 'delete' aka 'rename to trashbin' can be controlled with 'create':
           Just don't provide create for the trash namespace.
         * Someone without create in the target namespace cannot rename.

        @see: Item.rename.__doc__
        """
        # Special case since we need to check newname as well. Easier to special-case than
        # adjusting the decorator.
        username = self._backend.request.user.name
        if not self._may(newname, CREATE):
            raise AccessDeniedError(username, CREATE, newname)
        if not self._may(newname, WRITE):
            raise AccessDeniedError(username, WRITE, newname)
        return self._item.rename(newname)

    @require_privilege(WRITE)
    def commit(self):
        """
        @see: Item.commit.__doc__
        """
        return self._item.commit()

    # This does not require a privilege as the item must have been obtained
    # by either get_item or create_item already, which already check permissions.
    def rollback(self):
        """
        @see: Item.rollback.__doc__
        """
        return self._item.rollback()

    @require_privilege(DESTROY)
    def destroy(self):
        """
        USE WITH GREAT CARE!

        Choosing the required privileges for this one is difficult. If we'd introduce
        a new 'destroy item' privilege, everyone who, at some point, wants to perform an
        inter-backend rename (with RouterBackend) would need to run around with the
        'destroy item' privilege. We don't want that. Hence, we ask you to use this method
        only in very well thought-over situations.

        @see: Item.destroy.__doc__
        """
        return self._item.destroy()

    @require_privilege(WRITE)
    def create_revision(self, revno):
        """
        @see: Item.create_revision.__doc__
        """
        wrapped_revision = AclWrappedRevision(self._item.create_revision(revno), self)
        return wrapped_revision


class AclWrappedRevision(DictMixin):
    """
    Wrapper for revision classes. We need to wrap NewRevisions because they allow altering data.
    We need to wrap StoredRevisions since they offer a destroy() method.
    The caller should know what kind of revision he gets. Hence, we just implement the methods of
    both, StoredRevision and NewRevision. If a method is invoked that is not defined on the
    kind of revision we wrap, we will see an AttributeError one level deeper.
    """
    def __init__(self, revision, item):
        self._revision = revision
        self._item = item
        self._may = item._may

    def __getattr__(self, attr):
        return getattr(self._revision, attr)

    @property
    def item(self):
        """
        @see: Revision.item.__doc__
        """
        return self._item

    @property
    def timestamp(self):
        """
        @see: NewRevision.timestamp.__doc__
        """
        return self._revision.timestamp

    @property
    def size(self):
        """
        @see: NewRevision.size.__doc__
        """
        return self._revision.size

    def __setitem__(self, key, value):
        """
        In order to change an ACL on an item you must have the ADMIN privilege.
        We must allow the (unchanged) preceeding revision's ACL being stored
        into the new revision, though.

        @see: NewRevision.__setitem__.__doc__
        """
        if key == ACL:
            try:
                # This rev is not yet committed
                last_rev = self._item.get_revision(-1)
                last_acl = last_rev[ACL]
            except (NoSuchRevisionError, KeyError):
                last_acl = ''

            acl_changed = value != last_acl

            if acl_changed and not self._may(self._item.name, ADMIN):
                username = self._item._backend.request.user.name
                raise AccessDeniedError(username, ADMIN, self._item.name)
        return self._revision.__setitem__(key, value)

    def __getitem__(self, key):
        return self._revision[key]

    def __delitem__(self, key):
        del self._revision[key]

    def read(self, chunksize=-1):
        """
        @see: Backend._read_revision_data.__doc__
        """
        return self._revision.read(chunksize)

    def seek(self, position, mode=0):
        """
        @see: StringIO.StringIO().seek.__doc__
        """
        return self._revision.seek(position, mode)

    def destroy(self):
        """
        @see: Backend._destroy_revision.__doc__
        """
        if not self._may(self._item.name, DESTROY):
            username = self._item._backend.request.user.name
            raise AccessDeniedError(username, DESTROY + " revisions of", self._item.name)
        return self._revision.destroy()

    def write(self, data):
        """
        @see: Backend._write_revision_data.__doc__
        """
        return self._revision.write(data)

