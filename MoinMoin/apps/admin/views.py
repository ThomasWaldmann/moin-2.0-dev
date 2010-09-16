# -*- coding: ascii -*-
"""
    MoinMoin - admin views

    This shows the user interface for wiki admins.

    @copyright: 2008-2010 MoinMoin:ThomasWaldmann,
                2001-2003 Juergen Hermann <jh@web.de>,
                2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""

from flask import request, url_for, flash, redirect
from flask import current_app as app
from flask import flaskg

from werkzeug import escape

from MoinMoin import _, N_
from MoinMoin.theme import render_template
from MoinMoin.apps.admin import admin
from MoinMoin import user

@admin.route('/')
def index():
    return render_template('admin/index.html')


@admin.route('/userbrowser')
def userbrowser():
    """
    User Account Browser
    """
    # XXX add superuser check
    #isgroup = app.cfg.cache.item_group_regexact.search
    #groupnames = list(rootpage.getPageList(user='', filter=isgroup))
    user_accounts = []
    for uid in user.getUserList():
        u = user.User(uid)
        #groups = [groupname for groupname in groupnames if flaskg.dicts.has_member(groupname, account.name)])
        user_accounts.append(dict(
            uid=uid,
            name=u.name,
            email=u.email,
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
    uid = user.getUserId(user_name)
    u = user.User(uid)
    if request.method == 'GET':
        return "userprofile of %s: %r" % (user_name, (u.email, u.disabled))

    if request.method == 'POST':
        key = request.form.get('key', '')
        val = request.form.get('val', '')
        ok = False
        if hasattr(u, key):
            ok = True
            oldval = getattr(u, key)
            if isinstance(oldval, bool):
                val = bool(val)
            elif isinstance(oldval, int):
                val = int(val)
            elif isinstance(oldval, unicode):
                val = unicode(val)
            else:
                ok = False
        if ok:
            setattr(u, key, val)
            theuser.save()
            flash('%s.%s: %s -> %s' % tuple([escape(s) for s in [user_name, key, unicode(oldval), unicode(val)]]), "info")
        else:
            flash('modifying %s.%s failed' % tuple([escape(s) for s in [user_name, key]]), "error")
    return redirect(url_for('admin.userbrowser'))


@admin.route('/mail_recovery_token', methods=['GET', 'POST', ])
def mail_recovery_token():
    """
    Send user an email so he can reset his password.
    """
    flash("mail recovery token not implemented yet")
    return redirect(url_for('admin.userbrowser'))


@admin.route('/sysitems_upgrade', methods=['GET', 'POST', ])
def sysitems_upgrade():
    from MoinMoin.storage.backends import upgrade_sysitems
    from MoinMoin.storage.error import BackendError
    if request.method == 'GET':
        action = 'syspages_upgrade'
        label = 'Upgrade System Pages'
        return render_template('admin/sysitems_upgrade.html',
                              )
    if request.method == 'POST':
        xmlfile = request.files.get('xmlfile')
        try:
            upgrade_sysitems(xmlfile)
        except BackendError, e:
            flash(_('System items upgrade failed due to the following error: %(error)s.', error=e), 'error')
        else:
            flash(_('System items have been upgraded successfully!'))
        return redirect(url_for('admin.index'))

