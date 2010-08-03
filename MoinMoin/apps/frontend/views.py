# -*- coding: ascii -*-
"""
    MoinMoin - frontend views

    This shows the usual things users see when using the wiki.

    @copyright: 2003-2010 MoinMoin:ThomasWaldmann,
                2008 MoinMoin:FlorianKrupicka,
                2010 MoinMoin:DiogenesAugusto
@license: GNU GPL, see COPYING for details.
"""

import re
import difflib

from flask import request, url_for, flash, render_template, Response, redirect
from flask import flaskg

from MoinMoin.apps.frontend import frontend
from MoinMoin.items import Item, MIMETYPE, ITEMLINKS
from MoinMoin import config, user, wikiutil


@frontend.route('/')
def show_root():
    location = url_for('frontend.show_item', item_name='FrontPage') # wikiutil.getFrontPage(flaskg.context)
    return redirect(location)

@frontend.route('/robots.txt')
def robots():
    return Response("""\
User-agent: *
Crawl-delay: 20
Disallow: /+convert/
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
    flaskg.context.user.addTrail(item_name)
    item = Item.create(flaskg.context, item_name, rev_no=rev)
    rev_nos = item.rev.item.list_revisions()
    if rev_nos:
        first_rev = rev_nos[0]
        last_rev = rev_nos[-1]
    else:
        # Note: rev.revno of DummyRev is None
        first_rev = None
        last_rev = None
    return render_template('show.html',
                           item_name=item.name,
                           rev=item.rev,
                           mimetype=item.mimetype,
                           first_rev_no=first_rev,
                           last_rev_no=last_rev,
                           data_rendered=item._render_data(),
                           show_navigation=True if rev>-1 else False,
                          )

@frontend.route('/+show/<itemname:item_name>')
def redirect_show_item(item_name):
    return redirect(url_for('show_item', item_name=item_name))


@frontend.route('/+meta/<itemname:item_name>', defaults=dict(rev=-1))
@frontend.route('/+meta/<int:rev>/<itemname:item_name>')
def show_item_meta(item_name, rev):
    flaskg.context.user.addTrail(item_name)
    item = Item.create(flaskg.context, item_name, rev_no=rev)
    rev_nos = item.rev.item.list_revisions()
    if rev_nos:
        first_rev = rev_nos[0]
        last_rev = rev_nos[-1]
    else:
        # Note: rev.revno of DummyRev is None
        first_rev = None
        last_rev = None
    return render_template('meta.html',
                           item_name=item.name,
                           rev=item.rev,
                           mimetype=item.mimetype,
                           first_rev_no=first_rev,
                           last_rev_no=last_rev,
                           meta_rendered=item._render_meta(),
                           show_navigation=True if rev>-1 else False,
                          )


@frontend.route('/+get/<int:rev>/<itemname:item_name>')
@frontend.route('/+get/<itemname:item_name>', defaults=dict(rev=-1))
def get_item(item_name, rev):
    item = Item.create(flaskg.context, item_name, rev_no=rev)
    return item.do_get()

@frontend.route('/+convert/<itemname:item_name>')
def convert_item(item_name):
    """
    return a converted item.

    We create two items : the original one, and an empty
    one with the expected mimetype for the converted item.

    To get the converted item, we just feed his converter,
    with the internal representation of the item.
    """
    mimetype = request.values.get('mimetype')
    item = Item.create(flaskg.context, item_name, rev_no=-1)
    # We don't care about the name of the converted object
    # It should just be a name which does not exist.
    # XXX Maybe use a random name to be sure it does not exist
    item_name_converted = item_name + 'converted'
    converted_item = Item.create(flaskg.context, item_name_converted, mimetype=mimetype)
    return converted_item._convert(item.internal_representation())

@frontend.route('/+highlight/<int:rev>/<itemname:item_name>')
@frontend.route('/+highlight/<itemname:item_name>', defaults=dict(rev=-1))
def highlight_item(item_name, rev):
    from MoinMoin.items import Text, NonExistent
    item = Item.create(flaskg.context, item_name, rev_no=rev)
    if isinstance(item, Text):
        from MoinMoin.converter2 import default_registry as reg
        from MoinMoin.util.mime import Type, type_moin_document
        data_text = item.data_storage_to_internal(item.data)
        # TODO: use registry as soon as it is in there
        from MoinMoin.converter2.pygments_in import Converter as PygmentsConverter
        pygments_conv = PygmentsConverter(flaskg.context, mimetype=item.mimetype)
        doc = pygments_conv(data_text.split(u'\n'))
        # TODO: Real output format
        html_conv = reg.get(type_moin_document,
                Type('application/x-xhtml-moin-page'), request=flaskg.context)
        doc = html_conv(doc)
        from array import array
        out = array('u')
        # TODO: Switch to xml
        doc.write(out.fromunicode, method='html')
        content = out.tounicode()
    elif isinstance(item, NonExistent):
        return redirect(url_for('frontend.show_item', item_name=item_name))
    else:
        content = u"highlighting not supported"
    return render_template('highlight.html', item_name=item.name, data_text=content)


@frontend.route('/+modify/<itemname:item_name>', methods=['GET', 'POST'])
def modify_item(item_name):
    """Modify the wiki item item_name.

    On GET, displays a form.
    On POST, saves the new page (unless there's an error in input, or cancelled).
    After successful POST, redirects to the page.
    """
    mimetype = flaskg.context.values.get('mimetype')
    template_name = flaskg.context.values.get('template')
    item = Item.create(flaskg.context, item_name, mimetype=mimetype)
    if request.method == 'GET':
        content = item.do_modify(template_name)
        return content
    elif flaskg.context.method == 'POST':
        cancelled = 'button_cancel' in flaskg.context.form
        if not cancelled:
            item.modify()
        if mimetype in ('application/x-twikidraw', 'application/x-anywikidraw'):
            # TWikiDraw/AnyWikiDraw POST more than once, redirecting would break them
            return "OK"
        return redirect(url_for('show_item', item_name=item_name))


@frontend.route('/+revert/<int:rev>/<itemname:item_name>', methods=['GET', 'POST'])
def revert_item(item_name, rev):
    item = Item.create(flaskg.context, item_name, rev_no=rev)
    if request.method == 'GET':
        return render_template(item.revert_template, item=item)
    elif request.method == 'POST':
        if 'button_ok' in request.form:
            item.revert()
        return redirect(url_for('show_item', item_name=item_name))


@frontend.route('/+copy/<itemname:item_name>', methods=['GET', 'POST'])
def copy_item(item_name):
    item = Item.create(flaskg.context, item_name)
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
        return redirect(url_for('show_item', item_name=redirect_to))


@frontend.route('/+rename/<itemname:item_name>', methods=['GET', 'POST'])
def rename_item(item_name):
    item = Item.create(flaskg.context, item_name)
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
        return redirect(url_for('show_item', item_name=redirect_to))


@frontend.route('/+delete/<itemname:item_name>', methods=['GET', 'POST'])
def delete_item(item_name):
    item = Item.create(flaskg.context, item_name)
    if request.method == 'GET':
        return render_template(item.delete_template, item=item)
    elif request.method == 'POST':
        if 'button_ok' in request.form:
            comment = request.form.get('comment')
            item.delete(comment)
        return redirect(url_for('show_item', item_name=item_name))


@frontend.route('/+destroy/<itemname:item_name>', methods=['GET', 'POST'])
def destroy_item(item_name):
    item = Item.create(flaskg.context, item_name)
    if request.method == 'GET':
        return render_template(item.destroy_template, item=item)
    if request.method == 'POST':
        if 'button_ok' in request.form:
            comment = request.form.get('comment')
            item.destroy(comment)
        return redirect(url_for('show_item', item_name=item_name))


@frontend.route('/+index/<itemname:item_name>')
def index(item_name):
    item = Item.create(flaskg.context, item_name)
    return render_template(item.index_template, item=item)


@frontend.route('/+index')
def global_index():
    item_name = ''
    item = Item.create(flaskg.context, item_name)
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
    history = flaskg.context.storage.history(item_name=item_name)
    return render_template('history.html', item_name=item_name, history=history)


@frontend.route('/+history')
def global_history():
    history = flaskg.context.storage.history(item_name='')
    return render_template('global_history.html', history=history)


@frontend.route('/+quicklink/<itemname:item_name>')
def quicklink_item(item_name):
    """ Add/Remove the current wiki page to/from the user quicklinks """
    request = flaskg.context
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
    return redirect(url_for('show_item', item_name=item_name))


@frontend.route('/+subscribe/<itemname:item_name>')
def subscribe_item(item_name):
    """ Add/Remove the current wiki item to/from the user's subscriptions """
    request = flaskg.context
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
    return redirect(url_for('show_item', item_name=item_name))


@frontend.route('/+register', methods=['GET', 'POST'])
def register():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    request = flaskg.context
    _ = request.getText
    cfg = request.cfg
    item_name = 'Register' # XXX

    from MoinMoin.auth import MoinAuth
    from MoinMoin.security.textcha import TextCha

    for auth in cfg.auth:
        if isinstance(auth, MoinAuth):
            break
    else:
        return Response('No MoinAuth in auth list', 403)

    if request.method == 'GET':
        textcha = TextCha(request)
        if textcha.is_enabled():
            textcha = textcha and textcha.render()
        else:
            textcha = None
        return render_template('register.html',
                               title=_("Create Account"),
                               textcha=textcha,
                               ticket=wikiutil.createTicket(request),
                              )
    if request.method == 'POST':
        if 'create' in request.form:
            if False: # TODO re-add this later: not wikiutil.checkTicket(request, request.form.get('ticket', '')):
                msg = _('Please use the interactive user interface to use action %(actionname)s!') % {'actionname': 'register'}
            elif not TextCha(request).check_answer_from_form():
                msg = _('TextCha: Wrong answer! Go back and try again...')
            else:
                msg = user.create_user(request)
            if msg:
                flash(msg, "error")
        return redirect(url_for('frontend.show_root'))


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
    request = flaskg.context
    _ = request.getText
    if request.method == 'GET':
        for authmethod in request.cfg.auth:
            hint = authmethod.login_hint(request)
            if hint:
                flash(hint, "info")
        return render_template('login.html',
                               login_inputs=request.cfg.auth_login_inputs,
                               title=_("Login"),
                              )
    if request.method == 'POST':
        if 'login' in request.form:
            if hasattr(request, '_login_messages'):
                for msg in request._login_messages:
                    flash(msg, "error")
        return redirect(url_for('show_root'))


@frontend.route('/+logout')
def logout():
    item_name = 'LoggedOut' # XXX
    request = flaskg.context
    _ = request.getText
    # if the user really was logged out say so,
    # but if the user manually added ?do=logout
    # and that isn't really supported, then don't
    if request.user.valid:
        # something went wrong
        flash(_("You are still logged in."), "warning")
    else:
        flash(_("You are now logged out."), "info")
    return redirect(url_for('show_root'))


@frontend.route('/+diffsince/<int:timestamp>/<path:item_name>')
def diffsince(item_name, timestamp):
    date = timestamp
    # this is how we get called from "recent changes"
    # try to find the latest rev1 before bookmark <date>
    item = flaskg.context.storage.get_item(item_name)
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
    item = flaskg.context.storage.get_item(item_name)
    rev1 = flaskg.context.values.get('rev1')
    rev2 = flaskg.context.values.get('rev2')
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

    item = Item.create(flaskg.context, item_name, mimetype=commonmt, rev_no=newrevno)
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


@frontend.route('/+similar_names/<itemname:item_name>')
def similar_names(item_name):
    """
    list similar item names

    @copyright: 2001 Richard Jones <richard@bizarsoftware.com.au>,
                2001 Juergen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
    """
    _ = flaskg.context.getText
    start, end, matches = findMatches(item_name)
    keys = matches.keys()
    keys.sort()
    # TODO later we could add titles for the misc ranks:
    # 8 item_name
    # 4 "%s/..." % item_name
    # 3 "%s...%s" % (start, end)
    # 1 "%s..." % (start, )
    # 2 "...%s" % (end, )
    item_names = []
    for wanted_rank in [8, 4, 3, 1, 2, ]:
        for item_name in keys:
            item_rank = matches[item_name]
            if item_rank == wanted_rank:
                item_names.append(item_name)
    return render_template("item_link_list.html",
                           headline=_("Items with similar names"),
                           item_names=item_names)


def findMatches(item_name, s_re=None, e_re=None):
    """ Find similar item names.

    @param item_name: name to match
    @param request: current reqeust
    @param s_re: start re for wiki matching
    @param e_re: end re for wiki matching
    @rtype: tuple
    @return: start word, end word, matches dict
    """
    request = flaskg.context
    item_names = [item.name for item in request.storage.iteritems()]
    if item_name in item_names:
        item_names.remove(item_name)
    # Get matches using wiki way, start and end of word
    start, end, matches = wikiMatches(item_name, item_names, start_re=s_re, end_re=e_re)
    # Get the best 10 close matches
    close_matches = {}
    found = 0
    for name in closeMatches(item_name, item_names):
        if name not in matches:
            # Skip names already in matches
            close_matches[name] = 8
            found += 1
            # Stop after 10 matches
            if found == 10:
                break
    # Finally, merge both dicts
    matches.update(close_matches)
    return start, end, matches


def wikiMatches(item_name, item_names, start_re=None, end_re=None):
    """
    Get item names that starts or ends with same word as this item name.

    Matches are ranked like this:
        4 - item is subitem of item_name
        3 - match both start and end
        2 - match end
        1 - match start

    @param item_name: item name to match
    @param item_names: list of item names
    @param start_re: start word re (compile regex)
    @param end_re: end word re (compile regex)
    @rtype: tuple
    @return: start, end, matches dict
    """
    if start_re is None:
        start_re = re.compile('([%s][%s]+)' % (config.chars_upper,
                                               config.chars_lower))
    if end_re is None:
        end_re = re.compile('([%s][%s]+)$' % (config.chars_upper,
                                              config.chars_lower))

    # If we don't get results with wiki words matching, fall back to
    # simple first word and last word, using spaces.
    words = item_name.split()
    match = start_re.match(item_name)
    if match:
        start = match.group(1)
    else:
        start = words[0]

    match = end_re.search(item_name)
    if match:
        end = match.group(1)
    else:
        end = words[-1]

    matches = {}
    subitem = item_name + '/'

    # Find any matching item names and rank by type of match
    for name in item_names:
        if name.startswith(subitem):
            matches[name] = 4
        else:
            if name.startswith(start):
                matches[name] = 1
            if name.endswith(end):
                matches[name] = matches.get(name, 0) + 2

    return start, end, matches


def closeMatches(item_name, item_names):
    """ Get close matches.

    Return all matching item names with rank above cutoff value.

    @param item_name: item name to match
    @param item_names: list of item names
    @rtype: list
    @return: list of matching item names, sorted by rank
    """
    # Match using case insensitive matching
    # Make mapping from lower item names to item names.
    lower = {}
    for name in item_names:
        key = name.lower()
        if key in lower:
            lower[key].append(name)
        else:
            lower[key] = [name]

    # Get all close matches
    all_matches = difflib.get_close_matches(item_name.lower(), lower.keys(),
                                            len(lower), cutoff=0.6)

    # Replace lower names with original names
    matches = []
    for name in all_matches:
        matches.extend(lower[name])

    return matches


@frontend.route('/+dispatch', methods=['GET', ])
def dispatch():
    args = request.values.to_dict()
    endpoint = str(args.pop('endpoint'))
    return redirect(url_for(endpoint, **args))


@frontend.route('/+sitemap/<item_name>')
def sitemap(item_name):
    """
    sitemap view shows item link structure, relative to current item
    """
    sitemap = NestedItemListBuilder(flaskg.context).recurse_build([item_name])
    del sitemap[0] # don't show current item name as sole toplevel list item
    return render_template('sitemap.html', item_name=item_name, sitemap=sitemap)


class NestedItemListBuilder(object):
    def __init__(self, request):
        self.request = request
        self.children = set()
        self.numnodes = 0
        self.maxnodes = 35 # approx. max count of nodes, not strict

    def recurse_build(self, names):
        result = []
        if self.numnodes < self.maxnodes:
            for name in names:
                self.children.add(name)
                result.append(name)
                self.numnodes += 1
                childs = self.childs(name)
                if childs:
                    childs = self.recurse_build(childs)
                    result.append(childs)
        return result

    def childs(self, name):
        # does not recurse
        item = self.request.storage.get_item(name)
        rev = item.get_revision(-1)
        itemlinks = rev[ITEMLINKS]
        return [child for child in itemlinks if self.is_ok(child)]

    def is_ok(self, child):
        if child not in self.children:
            if not self.request.user.may.read(child):
                return False
            if self.request.storage.has_item(child):
                self.children.add(child)
                return True
        return False

