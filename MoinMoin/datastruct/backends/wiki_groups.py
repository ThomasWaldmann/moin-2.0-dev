# -*- coding: iso-8859-1 -*-
"""
MoinMoin - wiki group backend

The wiki_groups backend allows to define groups on wiki items.

Normally, the name of the group item has to end with Group like
FriendsGroup. This lets MoinMoin recognize it as a group. This default
pattern could be changed (e.g. for non-english languages etc.), see
HelpOnConfiguration.

@copyright: 2008 MoinMoin:ThomasWaldmann,
            2009 MoinMoin:DmitrijsMilajevs,
            2010 MoinMoin:ReimarBauer
@license: GPL, see COPYING for details
"""
from flask import flaskg
from MoinMoin.items import USERGROUP
from MoinMoin.datastruct.backends import GreedyGroup, BaseGroupsBackend, GroupDoesNotExistError


class WikiGroup(GreedyGroup):

    def _load_group(self):
        group_name = self.name
        if flaskg.storage.has_item(group_name):
            members, member_groups = super(WikiGroup, self)._load_group()
            return members, member_groups
        else:
            raise GroupDoesNotExistError(group_name)


class WikiGroups(BaseGroupsBackend):

    def __contains__(self, group_name):
        return self.is_group_name(group_name) and flaskg.storage.has_item(group_name)

    def __iter__(self):
        """
        To find group pages, app.cfg.cache.item_group_regexact pattern is used.
        """
        all_items = flaskg.storage.iteritems()
        # XXX Is this independent of current user?
        item_list = [item.name for item in all_items
                     if self.item_group_regex.search(item.name)]
        return iter(item_list)

    def __getitem__(self, group_name):
        return WikiGroup(request=self.request, name=group_name, backend=self)

    def _retrieve_members(self, group_name):
        item = flaskg.storage.get_item(group_name)
        rev = item.get_revision(-1)
        usergroup = rev.get(USERGROUP, {})
        return usergroup
