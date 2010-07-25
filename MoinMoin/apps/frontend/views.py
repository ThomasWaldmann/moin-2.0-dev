# -*- coding: ascii -*-
"""
    MoinMoin - frontend views
    
    This shows the usual things users see when using the wiki.

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import werkzeug
from flask import request, g, url_for

from MoinMoin.apps.frontend import frontend
from MoinMoin.items import Item

@frontend.route('/')
def show_root():
    location = 'FrontPage' # wikiutil.getFrontPage(g.context)
    return werkzeug.redirect(location, code=302)


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
        return item.do_revert()
    elif request.method == 'POST':
        cancelled = 'button_cancel' in g.context.form
        if not cancelled:
            item.revert()
        return werkzeug.redirect(url_for('show_item', item_name=item_name))


@frontend.route('/+index/<itemname:item_name>')
@frontend.route('/+index', defaults=dict(item_name=''))
def index(item_name):
    item = Item.create(g.context, item_name)
    return item.do_index()


@frontend.route('/+history/<itemname:item_name>')
@frontend.route('/+history', defaults=dict(item_name=''))
def history(item_name):
    request = g.context
    # TODO: No fake-metadata anymore, fix this
    history = request.storage.history(item_name=item_name)
    return render_template('rc.html', item_name=item_name, history=history)


@frontend.route('/+quicklink/<itemname:item_name>')
def quicklink(item_name):
    """ Add the current wiki page to the user quicklinks """
    request = g.context
    _ = request.getText

    if not request.user.valid:
        msg = _("You must login to add a quicklink."), "error"
    elif not request.user.isQuickLinkedTo([item_name]):
        if request.user.addQuicklink(item_name):
            msg = _('A quicklink to this page has been added for you.'), "info"
        else: # should not happen
            msg = _('A quicklink to this page could not be added for you.'), "error"
    else:
        msg = _('You already have a quicklink to this page.'), "info"
    flash(*msg)
    return werkzeug.redirect(url_for('show_root'), code=302)


@frontend.route('/+quickunlink/<itemname:item_name>')
def quickunlink(item_name):
    """ Remove the current wiki page from the user's quicklinks """
    request = g.context
    _ = request.getText
    msg = None

    if not request.user.valid:
        msg = _("You must login to remove a quicklink."), "warning"
    elif request.user.isQuickLinkedTo([item_name]):
        if request.user.removeQuicklink(item_name):
            msg = _('Your quicklink to this page has been removed.'), "info"
        else: # should not happen
            msg = _('Your quicklink to this page could not be removed.'), "error"
    else:
        msg = _('You need to have a quicklink to this page to remove it.'), "info"
    if msg:
        flash(*msg)
    item = Item.create(request, item_name)
    return item.do_show()


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
    return item.do_diff(oldrev, newrev)

# +feed/atom
# favicon.ico / robots.txt
# off-with-his-head

