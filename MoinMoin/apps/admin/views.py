# -*- coding: ascii -*-
"""
    MoinMoin - admin views
    
    This shows the user interface for wiki admins.

    @copyright: 2008-2010 MoinMoin:ThomasWaldmann,
                2001-2003 Juergen Hermann <jh@web.de>,
                2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""

from flask import request, g, url_for, render_template, flash, redirect

from MoinMoin.apps.admin import admin
from MoinMoin import user, wikiutil

@admin.route('/')
def index():
    return render_template('admin/index.html')


@admin.route('/userbrowser')
def userbrowser():
    """
    User Account Browser
    """
    # XXX add superuser check
    #isgroup = g.context.cfg.cache.page_group_regexact.search
    #groupnames = list(g.context.rootpage.getPageList(user='', filter=isgroup))
    user_accounts = []
    for uid in user.getUserList(g.context):
        u = user.User(g.context, uid)
        #groups = [groupname for groupname in groupnames if g.context.dicts.has_member(groupname, account.name)])
        user_accounts.append(dict(
            uid=uid,
            name=u.name,
            email=u.email,
            jid=u.jid,
            disabled=u.disabled,
            groups=[], # TODO
            ))
    return render_template('admin/userbrowser.html', user_accounts=user_accounts)


@admin.route('/userprofile/<user_name>', methods=['GET', 'POST', ])
def userprofile(user_name):
    """
    Set values in user profile
    """
    # XXX add superuser check
    uid = user.getUserId(g.context, user_name)
    u = user.User(g.context, uid)
    if request.method == 'GET':
        return "userprofile of %s: %r" % (user_name, (u.email, u.jid, u.disabled))

    if request.method == 'POST':
        if wikiutil.checkTicket(g.context, request.form.get('ticket', '')):
            key = request.form.get('key', '')
            val = request.form.get('val', '')
            if key in g.context.cfg.user_checkbox_fields:
                val = int(val)
            oldval = getattr(u, key)
            setattr(u, key, val)
            theuser.save()
            flash('%s.%s: %s -> %s' % tuple([wikiutil.escape(s) for s in [user_name, key, oldval, val]]), "info")
        else:
            flash("ticket fail")
    return redirect(url_for('admin.userbrowser'))


@admin.route('/mail_recovery_token', methods=['GET', 'POST', ])
def mail_recovery_token():
    """
    Send user an email so he can reset his password.
    """
    flash("mail recovery token not implemented yet")
    return redirect(url_for('admin.userbrowser'))

