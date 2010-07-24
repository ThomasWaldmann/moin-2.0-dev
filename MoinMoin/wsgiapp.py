# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - WSGI application

    @copyright: 2003-2008 MoinMoin:ThomasWaldmann,
                2008-2008 MoinMoin:FlorianKrupicka,
                2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""
import os, sys

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.web.contexts import AllContext, Context, XMLRPCContext
from MoinMoin.web.exceptions import HTTPException, Forbidden
from MoinMoin.web.request import Request, MoinMoinFinish, HeaderSet
from MoinMoin.web.utils import check_forbidden, check_surge_protect, fatal_response, \
    redirect_last_visited
from MoinMoin.storage.error import AccessDeniedError, StorageError
from MoinMoin.storage.serialization import unserialize
from MoinMoin.storage.backends import router, acl, memory
from MoinMoin.Page import Page
from MoinMoin.items import Item, MIMETYPE
from MoinMoin import auth, config, i18n, user, wikiutil, xmlrpc, error

from flask import Flask, request, g, url_for, render_template
import werkzeug


def set_umask(new_mask=0777^config.umask):
    """ Set the OS umask value (and ignore potential failures on OSes where
        this is not supported).
        Default: the bitwise inverted value of config.umask
    """
    try:
        old_mask = os.umask(new_mask)
    except:
        # maybe we are on win32?
        pass


def init_unprotected_backends(context):
    """ initialize the backend

        This is separate from init because the conftest request setup needs to be
        able to create fresh data storage backends in between init and init_backend.
    """
    # A ns_mapping consists of several lines, where each line is made up like this:
    # mountpoint, unprotected backend, protection to apply as a dict
    # We don't consider the protection here. That is done in protect_backends.
    ns_mapping = context.cfg.namespace_mapping
    # Just initialize with unprotected backends.
    unprotected_mapping = [(ns, backend) for ns, backend, acls in ns_mapping]
    index_uri = context.cfg.router_index_uri
    context.unprotected_storage = router.RouterBackend(unprotected_mapping, index_uri=index_uri)

    # This makes the first request after server restart potentially much slower...
    preload_xml(context)


def preload_xml(context):
    # If the content was already pumped into the backend, we don't want
    # to do that again. (Works only until the server is restarted.)
    xmlfile = context.cfg.preloaded_xml
    if xmlfile:
        context.cfg.preloaded_xml = None
        tmp_backend = router.RouterBackend([('/', memory.MemoryBackend())],
                                           index_uri='sqlite://')
        unserialize(tmp_backend, xmlfile)
        # TODO optimize this, maybe unserialize could count items it processed
        item_count = 0
        for item in tmp_backend.iteritems():
            item_count += 1
        logging.debug("preloaded xml into tmp_backend: %s, %d items" % (xmlfile, item_count))
        try:
            # In case the server was restarted we cannot know whether
            # the xml data already exists in the target backend.
            # Hence we check the existence of the items before we unserialize
            # them to the backend.
            backend = context.unprotected_storage
            for item in tmp_backend.iteritems():
                item = backend.get_item(item.name)
        except StorageError:
            # if there is some exception, we assume that backend needs to be filled
            # we need to use it as unserialization target so that update mode of
            # unserialization creates the correct item revisions
            logging.debug("unserialize xml file %s into %r" % (xmlfile, backend))
            unserialize(backend, xmlfile)
    else:
        item_count = 0

    # XXX wrong place / name - this is a generic preload functionality, not just for tests
    # To make some tests happy
    context.cfg.test_num_pages = item_count


def protect_backends(context):
    """
    This function is invoked after the user has been set up. setup_user needs access to
    storage and the ACL middleware needs access to the user's name. Hence we first
    init the unprotected backends so setup_user can access storage, and protect the
    backends after the user has been set up.
    """
    amw = acl.AclWrapperBackend
    ns_mapping = context.cfg.namespace_mapping
    # Protect each backend with the acls provided for it in the mapping at position 2
    protected_mapping = [(ns, amw(context, backend, **acls)) for ns, backend, acls in ns_mapping]
    index_uri = context.cfg.router_index_uri
    context.storage = router.RouterBackend(protected_mapping, index_uri=index_uri)

def setup_user(context, session):
    """ Try to retrieve a valid user object from the request, be it
    either through the session or through a login. """
    # first try setting up from session
    userobj = auth.setup_from_session(context, session)
    userobj, olduser = auth.setup_setuid(context, userobj)
    context._setuid_real_user = olduser

    # then handle login/logout forms
    form = context.request.values

    if 'login' in form:
        params = {
            'username': form.get('name'),
            'password': form.get('password'),
            'attended': True,
            'openid_identifier': form.get('openid_identifier'),
            'stage': form.get('stage')
        }
        userobj = auth.handle_login(context, userobj, **params)
    elif 'logout' in form:
        userobj = auth.handle_logout(context, userobj)
    else:
        userobj = auth.handle_request(context, userobj)

    # if we still have no user obj, create a dummy:
    if not userobj:
        userobj = user.User(context, auth_method='invalid')

    return userobj

def setup_i18n_preauth(context):
    """ Determine language for the request in absence of any user info. """
    if i18n.languages is None:
        i18n.i18n_init(context)

    lang = None
    if i18n.languages:
        cfg = context.cfg
        if not cfg.language_ignore_browser:
            for l, w in context.request.accept_languages:
                logging.debug("client accepts language %r, weight %r" % (l, w))
                if l in i18n.languages:
                    logging.debug("moin supports language %r" % l)
                    lang = l
                    break
            else:
                logging.debug("moin does not support any language client accepts")
        if not lang:
            if cfg.language_default in i18n.languages:
                lang = cfg.language_default
                logging.debug("fall back to cfg.language_default (%r)" % lang)
    if not lang:
        lang = 'en'
        logging.debug("emergency fallback to 'en'")
    logging.debug("setup_i18n_preauth returns %r" % lang)
    return lang

def setup_i18n_postauth(context):
    """ Determine language for the request after user-id is established. """
    lang = context.user.getLang()
    logging.debug("setup_i18n_postauth returns %r" % lang)
    return lang

class MoinFlask(Flask):
    # TODO: at all places where we insert html into output, use the Markup
    # class of flask/jinja so we can switch autoescape on in the end.
    def select_jinja_autoescape(self, filename):
        return False

application = app = MoinFlask('MoinMoin', '/moin_static200')

from werkzeug.routing import PathConverter
class ItemNameConverter(PathConverter):
    pass #regex = r'[^+].*?'

app.url_map.converters['itemname'] = ItemNameConverter


def setup_jinja_env(request):
    from werkzeug import url_quote, url_encode
    from MoinMoin.theme.filters import shorten_item_name
    from MoinMoin.items import EDIT_LOG_USERID, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME
    theme = request.theme
    app.jinja_env.filters['urlencode'] = lambda x: url_encode(x)
    app.jinja_env.filters['urlquote'] = lambda x: url_quote(x)
    app.jinja_env.filters['datetime_format'] = lambda tm, u = request.user: u.getFormattedDateTime(tm)
    app.jinja_env.filters['date_format'] = lambda tm, u = request.user: u.getFormattedDate(tm)
    app.jinja_env.filters['shorten_item_name'] = shorten_item_name
    app.jinja_env.filters['user_format'] = lambda rev, request = request: \
                                          user.get_printable_editor(request,
                                                                    rev.get(EDIT_LOG_USERID),
                                                                    rev.get(EDIT_LOG_ADDR),
                                                                    rev.get(EDIT_LOG_HOSTNAME))
    app.jinja_env.globals.update({
                            'theme': theme,
                            'user': request.user,
                            'cfg': request.cfg,
                            '_': request.getText,
                            'href': request.href,
                            'static_href': request.static_href,
                            'abs_href': request.abs_href,
                            'item_name': 'handlers need to give it',
                            'translated_item_name': theme.translated_item_name,
                            })


@app.before_request
def before():
    """
    Wraps an incoming WSGI request in a Context object and initializes
    several important attributes.
    """
    set_umask() # do it once per request because maybe some server
                # software sets own umask

    context = AllContext(Request(request.environ))
    context.clock.start('total')
    context.clock.start('init')

    context.lang = setup_i18n_preauth(context)

    context.session = context.cfg.session_service.get_session(context)

    init_unprotected_backends(context)
    context.user = setup_user(context, context.session)

    context.lang = setup_i18n_postauth(context)

    def finish():
        pass

    context.finish = finish

    context.reset()

    context.clock.stop('init')
    protect_backends(context)

    setup_jinja_env(context)

    g.context = context
    # if return value is not None, it is the final response

@app.after_request
def after(response):
    context = g.context
    context.cfg.session_service.finalize(context, context.session)
    context.finish()
    return response


################## experimental Flask stuff below here: #########################

@app.route('/')
def show_root():
    location = 'FrontPage' # wikiutil.getFrontPage(g.context)
    return werkzeug.redirect(location, code=302)

@app.route('/<itemname:item_name>', defaults=dict(rev=-1))
@app.route('/+show/<int:rev>/<itemname:item_name>')
def show_item(item_name, rev):
    g.context.user.addTrail(item_name)
    mimetype = request.values.get('mimetype')
    item = Item.create(g.context, item_name, mimetype=mimetype, rev_no=rev)
    return item.do_show()

@app.route('/+show/<itemname:item_name>')
def redirect_show_item(item_name):
    return werkzeug.redirect(url_for('show_item', item_name=item_name))

@app.route('/+get/<int:rev>/<itemname:item_name>')
@app.route('/+get/<itemname:item_name>', defaults=dict(rev=-1))
def get_item(item_name, rev):
    item = Item.create(g.context, item_name, rev_no=rev)
    return item.do_get()

@app.route('/+modify/<itemname:item_name>', methods=['GET', 'POST'])
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


@app.route('/+revert/<int:rev>/<itemname:item_name>', methods=['GET', 'POST'])
def revert_item(item_name, rev):
    item = Item.create(g.context, item_name, rev_no=rev)
    if request.method == 'GET':
        return item.do_revert()
    elif request.method == 'POST':
        cancelled = 'button_cancel' in g.context.form
        if not cancelled:
            item.revert()
        return werkzeug.redirect(url_for('show_item', item_name=item_name))


@app.route('/+index/<itemname:item_name>')
@app.route('/+index', defaults=dict(item_name=''))
def index(item_name):
    item = Item.create(g.context, item_name)
    return item.do_index()

@app.route('/+history/<itemname:item_name>')
@app.route('/+history', defaults=dict(item_name=''))
def history(item_name):
    request = g.context
    # TODO: No fake-metadata anymore, fix this
    history = request.storage.history(item_name=item_name)
    return render_template('rc.html', item_name=item_name, history=history)


@app.route('/+quicklink/<itemname:item_name>')
def quicklink(item_name):
    """ Add the current wiki page to the user quicklinks """
    request = g.context
    _ = request.getText

    if not request.user.valid:
        request.theme.add_msg(_("You must login to add a quicklink."), "error")
    elif not request.user.isQuickLinkedTo([item_name]):
        if request.user.addQuicklink(item_name):
            request.theme.add_msg(_('A quicklink to this page has been added for you.'), "info")
        else: # should not happen
            request.theme.add_msg(_('A quicklink to this page could not be added for you.'), "error")
    else:
        request.theme.add_msg(_('You already have a quicklink to this page.'))
    item = Item.create(request, item_name)
    return item.do_show()

@app.route('/+quickunlink/<itemname:item_name>')
def quickunlink(item_name):
    """ Remove the current wiki page from the user's quicklinks """
    request = g.context
    _ = request.getText
    msg = None

    if not request.user.valid:
        msg = _("You must login to remove a quicklink.")
    elif request.user.isQuickLinkedTo([item_name]):
        if request.user.removeQuicklink(item_name):
            msg = _('Your quicklink to this page has been removed.')
        else: # should not happen
            msg = _('Your quicklink to this page could not be removed.')
    else:
        msg = _('You need to have a quicklink to this page to remove it.')
    if msg:
        request.theme.add_msg(msg)
    item = Item.create(request, item_name)
    return item.do_show()

@app.route('/+login', methods=['GET', 'POST'])
def login():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    item_name = 'LoggedIn' # XXX
    request = g.context
    _ = request.getText
    title = _("Login")
    if request.method == 'GET':
        login_hints = []
        for authmethod in request.cfg.auth:
            hint = authmethod.login_hint(request)
            if hint:
                login_hints.append(hint)
        return render_template('login.html',
                                    login_hints=login_hints,
                                    login_inputs=request.cfg.auth_login_inputs,
                                    title=title
                                   )
    if request.method == 'POST':
        if 'login' in request.form:
            if hasattr(request, '_login_messages'):
                for msg in request._login_messages:
                    request.theme.add_msg(msg, "error")
        item = Item.create(request, item_name)
        return item.do_show()

@app.route('/+logout')
def logout():
    item_name = 'LoggedOut' # XXX
    request = g.context
    _ = request.getText
    title = _("Logout")
    # if the user really was logged out say so,
    # but if the user manually added ?do=logout
    # and that isn't really supported, then don't
    if not request.user.valid:
        msg = _("You are now logged out."), "info"
    else:
        # something went wrong
        msg = _("You are still logged in."), "warning"
    request.theme.add_msg(*msg)
    item = Item.create(request, item_name)
    return item.do_show()

@app.route('/+diffsince/<int:timestamp>/<path:item_name>')
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

@app.route('/+diff/<path:item_name>')
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

if __name__ == '__main__':
    app.run(port=8888, debug=True)


