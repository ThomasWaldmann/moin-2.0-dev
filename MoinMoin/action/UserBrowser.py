# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - User Account Browser

    TODO: use Item, not Page

    @copyright: 2001-2003 Juergen Hermann <jh@web.de>,
                2009 MoinMoin:ThomasWaldmann,
                2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""
from flask import render_template

from MoinMoin import user, wikiutil
from MoinMoin.Page import Page


def get_account_infos(request):
    """ Return a list with user account infos. """
    _ = request.getText

    isgroup = request.cfg.cache.page_group_regexact.search
    groupnames = list(request.rootpage.getPageList(user='', filter=isgroup))

    account_infos = []
    for uid in user.getUserList(request):
        account = user.User(request, uid)

        userhomepage = Page(request, account.name)
        if userhomepage.exists():
            namelink = userhomepage.link_to(request)
        else:
            namelink = wikiutil.escape(account.name)

        grouppage_links = ', '.join([Page(request, groupname).link_to(request)
                                     for groupname in groupnames
                                     if request.dicts.has_member(groupname, account.name)])

        account_infos.append(dict(
            namelink=namelink,
            name=account.name,
            email=account.email,
            jid=account.jid,
            grouppage_links=grouppage_links,
            disabled=account.disabled,
            ))
    return account_infos


def execute(item_name, request):
    return render_template('userbrowser.html',
                           user_accounts=get_account_infos(request))

