# -*- coding: ascii -*-
"""
    MoinMoin - frontend views
    
    This shows the usual things users see when using the wiki.

    @copyright: 2003-2010 MoinMoin:ThomasWaldmann,
                2008 MoinMoin:FlorianKrupicka,
                2010 MoinMoin:DiogenesAugusto
@license: GNU GPL, see COPYING for details.
"""

import werkzeug
from flask import request, g, url_for, flash, render_template, Response

from MoinMoin.apps.frontend import frontend
from MoinMoin.items import Item, MIMETYPE

@frontend.route('/')
def show_root():
    location = 'FrontPage' # wikiutil.getFrontPage(g.context)
    return werkzeug.redirect(location, code=302)

@frontend.route('/robots.txt')
def robots():
    return Response("""\
User-agent: *
Crawl-delay: 20
Disallow: /+modify/
Disallow: /+copy/
Disallow: /+delete/
Disallow: /+destroy/
Disallow: /+rename/
Disallow: /+revert/
Disallow: /+index/
Disallow: /+quicklink/
Disallow: /+subscribe/
Disallow: /+backlinks/
Disallow: /+register
Disallow: /+recoverpass
Disallow: /+userprefs
Disallow: /+login
Disallow: /+logout
Disallow: /+diffsince/
Disallow: /+diff/
Disallow: /+admin/
Allow: /
""", mimetype='text/plain')


@frontend.route('/<itemname:item_name>', defaults=dict(rev=-1))
@frontend.route('/+show/<int:rev>/<itemname:item_name>')
def show_item(item_name, rev):
    g.context.user.addTrail(item_name)
    mimetype = request.values.get('mimetype')
    item = Item.create(g.context, item_name, mimetype=mimetype, rev_no=rev)
    return item.do_show()

@frontend.route('/+show/<itemname:item_name>')
def redirect_show_item(item_name):
    return werkzeug.redirect(url_for('show_item', item_name=item_name))


@frontend.route('/+get/<int:rev>/<itemname:item_name>')
@frontend.route('/+get/<itemname:item_name>', defaults=dict(rev=-1))
def get_item(item_name, rev):
    item = Item.create(g.context, item_name, rev_no=rev)
    return item.do_get()


@frontend.route('/+highlight/<int:rev>/<itemname:item_name>')
@frontend.route('/+highlight/<itemname:item_name>', defaults=dict(rev=-1))
def highlight_item(item_name, rev):
    item = Item.create(g.context, item_name, rev_no=rev)
    return item.do_highlight()


@frontend.route('/+modify/<itemname:item_name>', methods=['GET', 'POST'])
def modify_item(item_name):
    """Modify the wiki item item_name.

    On GET, displays a form.
    On POST, saves the new page (unless there's an error in input, or cancelled).
    After successful POST, redirects to the page.
    """
    mimetype = g.context.values.get('mimetype', 'text/plain')
    template_name = g.context.values.get('template')
    item = Item.create(g.context, item_name, mimetype=mimetype)
    if request.method == 'GET':
        content = item.do_modify(template_name)
        return content
    elif g.context.method == 'POST':
        cancelled = 'button_cancel' in g.context.form
        if not cancelled:
            item.modify()
        if not mimetype in ('application/x-twikidraw', 'application/x-anywikidraw'):
            # TwikiDraw and AnyWikiDraw can send more than one request
            # the follwowing line breaks it
            return werkzeug.redirect(url_for('show_item', item_name=item_name))
        # Nick Booker: Any handling necessary here for TwikiDraw / AnyWikiDraw?


@frontend.route('/+revert/<int:rev>/<itemname:item_name>', methods=['GET', 'POST'])
def revert_item(item_name, rev):
    item = Item.create(g.context, item_name, rev_no=rev)
    if request.method == 'GET':
        return render_template(item.revert_template, item=item)
    elif request.method == 'POST':
        if 'button_ok' in request.form:
            item.revert()
        return werkzeug.redirect(url_for('show_item', item_name=item_name))


@frontend.route('/+copy/<itemname:item_name>', methods=['GET', 'POST'])
def copy_item(item_name):
    item = Item.create(g.context, item_name)
    if request.method == 'GET':
        return render_template(item.copy_template, item=item)
    if request.method == 'POST':
        if 'button_ok' in request.form:
            target = request.form.get('target')
            comment = request.form.get('comment')
            item.copy(target, comment)
            redirect_to = target
        else:
            redirect_to = item_name
        return werkzeug.redirect(url_for('show_item', item_name=redirect_to))


@frontend.route('/+rename/<itemname:item_name>', methods=['GET', 'POST'])
def rename_item(item_name):
    item = Item.create(g.context, item_name)
    if request.method == 'GET':
        return render_template(item.rename_template, item=item)
    if request.method == 'POST':
        if 'button_ok' in request.form:
            target = request.form.get('target')
            comment = request.form.get('comment')
            item.rename(target, comment)
            redirect_to = target
        else:
            redirect_to = item_name
        return werkzeug.redirect(url_for('show_item', item_name=redirect_to))


@frontend.route('/+delete/<itemname:item_name>', methods=['GET', 'POST'])
def delete_item(item_name):
    item = Item.create(g.context, item_name)
    if request.method == 'GET':
        return render_template(item.delete_template, item=item)
    elif request.method == 'POST':
        if 'button_ok' in request.form:
            comment = request.form.get('comment')
            item.delete(comment)
        return werkzeug.redirect(url_for('show_item', item_name=item_name))


@frontend.route('/+destroy/<itemname:item_name>', methods=['GET', 'POST'])
def destroy_item(item_name):
    item = Item.create(g.context, item_name)
    if request.method == 'GET':
        return render_template(item.destroy_template, item=item)
    if request.method == 'POST':
        if 'button_ok' in request.form:
            comment = request.form.get('comment')
            item.destroy(comment)
        return werkzeug.redirect(url_for('show_item', item_name=item_name))


@frontend.route('/+index/<itemname:item_name>')
def index(item_name):
    item = Item.create(g.context, item_name)
    return render_template(item.index_template, item=item)


@frontend.route('/+index')
def global_index():
    item_name = ''
    item = Item.create(g.context, item_name)
    return render_template(item.index_template, item=item)


@frontend.route('/+backlinks/<itemname:item_name>')
def backlinks(item_name):
    return _search(value='linkto:"%s"' % item_name, context=180)


@frontend.route('/+search')
def search():
    return _search()


def _search(**args):
    return "searching for %r not implemented yet" % args


@frontend.route('/+history/<itemname:item_name>')
def history(item_name):
    history = g.context.storage.history(item_name=item_name)
    return render_template('history.html', item_name=item_name, history=history)


@frontend.route('/+history')
def global_history():
    history = g.context.storage.history(item_name='')
    return render_template('global_history.html', history=history)


@frontend.route('/+quicklink/<itemname:item_name>')
def quicklink_item(item_name):
    """ Add/Remove the current wiki page to/from the user quicklinks """
    request = g.context
    _ = request.getText
    u = request.user
    msg = None
    if not u.valid:
        msg = _("You must login to use this action: %(action)s.") % {"action": "quicklink/quickunlink"}, "error"
    elif not request.user.isQuickLinkedTo([item_name]):
        if not u.addQuicklink(item_name):
            msg = _('A quicklink to this page could not be added for you.'), "error"
    else:
        if not u.removeQuicklink(item_name):
            msg = _('Your quicklink to this page could not be removed.'), "error"
    if msg:
        flash(*msg)
    item = Item.create(request, item_name)
    return item.do_show()


@frontend.route('/+subscribe/<itemname:item_name>')
def subscribe_item(item_name):
    """ Add/Remove the current wiki item to/from the user's subscriptions """
    request = g.context
    _ = request.getText
    u = request.user
    cfg = request.cfg
    msg = None
    if not u.valid:
        msg = _("You must login to use this action: %(action)s.") % {"action": "subscribe/unsubscribe"}, "error"
    elif not u.may.read(item_name):
        msg = _("You are not allowed to subscribe to an item you may not read."), "error"
    elif not cfg.mail_enabled and not cfg.jabber_enabled:
        msg = _("This wiki is not enabled for mail/Jabber processing."), "error"
    elif not u.email and not u.jid:
        msg = _("Add your email address or Jabber ID in your user settings to use subscriptions."), "error"
    elif u.isSubscribedTo([item_name]):
        # Try to unsubscribe
        if not u.unsubscribe(item_name):
            msg = _("Can't remove regular expression subscription!") + u' ' + \
                  _("Edit the subscription regular expressions in your settings."), "error"
    else:
        # Try to subscribe
        if not u.subscribe(item_name):
            msg = _('You could not get subscribed to this item.'), "error"
    if msg:
        flash(*msg)
    item = Item.create(request, item_name)
    return item.do_show()


@frontend.route('/+register', methods=['GET', 'POST'])
def register():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    item_name = 'Register' # XXX
    if request.method == 'GET':
        return "NotImplemented"
    if request.method == 'POST':
        return "NotImplemented"


@frontend.route('/+recoverpass', methods=['GET', 'POST'])
def recoverpass():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    item_name = 'RecoverPass' # XXX
    if request.method == 'GET':
        return "NotImplemented"
    if request.method == 'POST':
        return "NotImplemented"


@frontend.route('/+userprefs', methods=['GET', 'POST'])
def userprefs():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    item_name = 'UserPrefs' # XXX
    if request.method == 'GET':
        return "NotImplemented"
    if request.method == 'POST':
        return "NotImplemented"


@frontend.route('/+login', methods=['GET', 'POST'])
def login():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    item_name = 'LoggedIn' # XXX
    request = g.context
    _ = request.getText
    title = _("Login")
    if request.method == 'GET':
        for authmethod in request.cfg.auth:
            hint = authmethod.login_hint(request)
            if hint:
                flash(hint, "info")
        return render_template('login.html',
                               login_inputs=request.cfg.auth_login_inputs,
                               title=title
                              )
    if request.method == 'POST':
        if 'login' in request.form:
            if hasattr(request, '_login_messages'):
                for msg in request._login_messages:
                    flash(msg, "error")
    return werkzeug.redirect(url_for('show_root'), code=302)


@frontend.route('/+logout')
def logout():
    item_name = 'LoggedOut' # XXX
    request = g.context
    _ = request.getText
    title = _("Logout")
    # if the user really was logged out say so,
    # but if the user manually added ?do=logout
    # and that isn't really supported, then don't
    if not request.user.valid:
        flash(_("You are now logged out."), "info")
    else:
        # something went wrong
        flash(_("You are still logged in."), "warning")
    return werkzeug.redirect(url_for('show_root'), code=302)


@frontend.route('/+diffsince/<int:timestamp>/<path:item_name>')
def diffsince(item_name, timestamp):
    date = timestamp
    # this is how we get called from "recent changes"
    # try to find the latest rev1 before bookmark <date>
    item = g.context.storage.get_item(item_name)
    revnos = item.list_revisions()
    revnos.reverse()  # begin with latest rev
    for revno in revnos:
        revision = item.get_revision(revno)
        if revision.timestamp <= date:
            rev1 = revision.revno
            break
    else:
        rev1 = revno  # if we didn't find a rev, we just take oldest rev we have
    rev2 = -1  # and compare it with latest we have
    return _diff(item, rev1, rev2)


@frontend.route('/+diff/<path:item_name>')
def diff(item_name):
    # TODO get_item and get_revision calls may raise an AccessDeniedError.
    #      If this happens for get_item, don't show the diff at all
    #      If it happens for get_revision, we may just want to skip that rev in the list
    item = g.context.storage.get_item(item_name)
    rev1 = g.context.values.get('rev1')
    rev2 = g.context.values.get('rev2')
    return _diff(item, rev1, rev2)


def _diff(item, revno1, revno2):
    try:
        revno1 = int(revno1)
    except (ValueError, TypeError):
        revno1 = -2
    try:
        revno2 = int(revno2)
    except (ValueError, TypeError):
        revno2 = -1

    item_name = item.name
    # get (absolute) current revision number
    current_revno = item.get_revision(-1).revno
    # now we can calculate the absolute revnos if we don't have them yet
    if revno1 < 0:
        revno1 += current_revno + 1
    if revno2 < 0:
        revno2 += current_revno + 1

    if revno1 > revno2:
        oldrevno, newrevno = revno2, revno1
    else:
        oldrevno, newrevno = revno1, revno2

    oldrev = item.get_revision(oldrevno)
    newrev = item.get_revision(newrevno)

    oldmt = oldrev.get(MIMETYPE)
    newmt = newrev.get(MIMETYPE)

    if oldmt == newmt:
        # easy, exactly the same mimetype, call do_diff for it
        commonmt = newmt
    else:
        oldmajor = oldmt.split('/')[0]
        newmajor = newmt.split('/')[0]
        if oldmajor == newmajor:
            # at least same major mimetype, use common base item class
            commonmt = newmajor + '/'
        else:
            # nothing in common
            commonmt = ''

    item = Item.create(g.context, item_name, mimetype=commonmt, rev_no=newrevno)
    rev_nos = item.rev.item.list_revisions()
    return render_template(item.diff_template,
                           item=item,
                           item_name=item.name,
                           rev=item.rev,
                           first_rev_no=rev_nos[0],
                           last_rev_no=rev_nos[-1],
                           oldrev=oldrev,
                           newrev=newrev,
                          )

@frontend.route('/+dispatch', methods=['GET', ])
def dispatch():
    args = request.values.to_dict()
    endpoint = str(args.pop('endpoint'))
    return werkzeug.redirect(url_for(endpoint, **args), code=302)


# +feed/atom
# off-with-his-head

