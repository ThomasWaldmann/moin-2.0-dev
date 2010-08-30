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

from flask import request, url_for, flash, render_template, Response, redirect, session
from flask import flaskg
from flask import current_app as app

from flatland import String, Form
from flatland.validation import Validator, Present, IsEmail

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import _, N_
from MoinMoin.apps.frontend import frontend
from MoinMoin.items import Item, NonExistent, MIMETYPE, ITEMLINKS
from MoinMoin import config, user, wikiutil
from MoinMoin.util.forms import make_generator

N_ = lambda x: x


@frontend.route('/+dispatch', methods=['GET', ])
def dispatch():
    args = request.values.to_dict()
    endpoint = str(args.pop('endpoint'))
    return redirect(url_for(endpoint, **args))


@frontend.route('/')
def show_root():
    item_name = app.cfg.page_front_page
    location = url_for('frontend.show_item', item_name=item_name)
    return redirect(location)

@frontend.route('/robots.txt')
def robots():
    return Response("""\
User-agent: *
Crawl-delay: 20
Disallow: /+convert/
Disallow: /+dom/
Disallow: /+modify/
Disallow: /+copy/
Disallow: /+delete/
Disallow: /+destroy/
Disallow: /+rename/
Disallow: /+revert/
Disallow: /+index/
Disallow: /+sitemap/
Disallow: /+similar_names/
Disallow: /+quicklink/
Disallow: /+subscribe/
Disallow: /+backlinks/
Disallow: /+register
Disallow: /+recoverpass
Disallow: /+usersettings
Disallow: /+login
Disallow: /+changepass
Disallow: /+logout
Disallow: /+diffsince/
Disallow: /+diff/
Disallow: /+dispatch/
Disallow: /+admin/
Allow: /
""", mimetype='text/plain')


@frontend.route('/favicon.ico')
def favicon():
    # although we tell that favicon.ico is at /static/favicon.ico,
    # some browsers still request it from /favicon.ico...
    return app.send_static_file('favicon.ico')


@frontend.route('/<itemname:item_name>', defaults=dict(rev=-1))
@frontend.route('/+show/<int:rev>/<itemname:item_name>')
def show_item(item_name, rev):
    flaskg.user.addTrail(item_name)
    item = Item.create(flaskg.context, item_name, rev_no=rev)
    rev_nos = item.rev.item.list_revisions()
    if rev_nos:
        first_rev = rev_nos[0]
        last_rev = rev_nos[-1]
    else:
        # Note: rev.revno of DummyRev is None
        first_rev = None
        last_rev = None
    if isinstance(item, NonExistent):
        status = 404
    else:
        status = 200
    content = render_template('show.html',
                              item=item, item_name=item.name,
                              rev=item.rev,
                              mimetype=item.mimetype,
                              first_rev_no=first_rev,
                              last_rev_no=last_rev,
                              data_rendered=item._render_data(),
                              show_navigation=(rev>=0),
                             )
    return Response(content, status)


@frontend.route('/+show/<itemname:item_name>')
def redirect_show_item(item_name):
    return redirect(url_for('frontend.show_item', item_name=item_name))


@frontend.route('/+dom/<int:rev>/<itemname:item_name>')
@frontend.route('/+dom/<itemname:item_name>', defaults=dict(rev=-1))
def show_dom(item_name, rev):
    item = Item.create(flaskg.context, item_name, rev_no=rev)
    if isinstance(item, NonExistent):
        status = 404
    else:
        status = 200
    content = render_template('dom.xml',
                              data_xml=item._render_data_xml(),
                             )
    return Response(content, status, mimetype='text/xml')


@frontend.route('/+meta/<itemname:item_name>', defaults=dict(rev=-1))
@frontend.route('/+meta/<int:rev>/<itemname:item_name>')
def show_item_meta(item_name, rev):
    flaskg.user.addTrail(item_name)
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
                           item=item, item_name=item.name,
                           rev=item.rev,
                           mimetype=item.mimetype,
                           first_rev_no=first_rev,
                           last_rev_no=last_rev,
                           meta_rendered=item._render_meta(),
                           show_navigation=(rev>=0),
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
    from MoinMoin.util.tree import html
    item = Item.create(flaskg.context, item_name, rev_no=rev)
    if isinstance(item, Text):
        from MoinMoin.converter2 import default_registry as reg
        from MoinMoin.util.mime import Type, type_moin_document
        data_text = item.data_storage_to_internal(item.data)
        # TODO: use registry as soon as it is in there
        from MoinMoin.converter2.pygments_in import Converter as PygmentsConverter
        pygments_conv = PygmentsConverter(mimetype=item.mimetype)
        doc = pygments_conv(data_text.split(u'\n'))
        # TODO: Real output format
        html_conv = reg.get(type_moin_document,
                Type('application/x-xhtml-moin-page'), request=flaskg.context)
        doc = html_conv(doc)
        from array import array
        out = array('u')
        doc.write(out.fromunicode, namespaces={html.namespace: ''}, method='xml')
        content = out.tounicode()
    elif isinstance(item, NonExistent):
        return redirect(url_for('frontend.show_item', item_name=item_name))
    else:
        content = u"highlighting not supported"
    return render_template('highlight.html',
                           item=item, item_name=item.name,
                           data_text=content,
                          )


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
        if mimetype in ('application/x-twikidraw', 'application/x-anywikidraw', 'application/x-svgdraw'):
            # TWikiDraw/AnyWikiDraw/SvgDraw POST more than once, redirecting would break them
            return "OK"
        return redirect(url_for('frontend.show_item', item_name=item_name))


@frontend.route('/+revert/<int:rev>/<itemname:item_name>', methods=['GET', 'POST'])
def revert_item(item_name, rev):
    item = Item.create(flaskg.context, item_name, rev_no=rev)
    if request.method == 'GET':
        return render_template(item.revert_template,
                               item=item, item_name=item_name,
                              )
    elif request.method == 'POST':
        if 'button_ok' in flaskg.context.form:
            item.revert()
        return redirect(url_for('frontend.show_item', item_name=item_name))


@frontend.route('/+copy/<itemname:item_name>', methods=['GET', 'POST'])
def copy_item(item_name):
    item = Item.create(flaskg.context, item_name)
    if request.method == 'GET':
        return render_template(item.copy_template,
                               item=item, item_name=item_name,
                              )
    if request.method == 'POST':
        if 'button_ok' in flaskg.context.form:
            target = flaskg.context.form.get('target')
            comment = flaskg.context.form.get('comment')
            item.copy(target, comment)
            redirect_to = target
        else:
            redirect_to = item_name
        return redirect(url_for('frontend.show_item', item_name=redirect_to))


@frontend.route('/+rename/<itemname:item_name>', methods=['GET', 'POST'])
def rename_item(item_name):
    item = Item.create(flaskg.context, item_name)
    if request.method == 'GET':
        return render_template(item.rename_template,
                               item=item, item_name=item_name,
                              )
    if request.method == 'POST':
        if 'button_ok' in flaskg.context.form:
            target = flaskg.context.form.get('target')
            comment = flaskg.context.form.get('comment')
            item.rename(target, comment)
            redirect_to = target
        else:
            redirect_to = item_name
        return redirect(url_for('frontend.show_item', item_name=redirect_to))


@frontend.route('/+delete/<itemname:item_name>', methods=['GET', 'POST'])
def delete_item(item_name):
    item = Item.create(flaskg.context, item_name)
    if request.method == 'GET':
        return render_template(item.delete_template,
                               item=item, item_name=item_name,
                              )
    elif request.method == 'POST':
        if 'button_ok' in flaskg.context.form:
            comment = flaskg.context.form.get('comment')
            item.delete(comment)
        return redirect(url_for('frontend.show_item', item_name=item_name))


@frontend.route('/+destroy/<int:rev>/<itemname:item_name>', methods=['GET', 'POST'])
@frontend.route('/+destroy/<itemname:item_name>', methods=['GET', 'POST'], defaults=dict(rev=None))
def destroy_item(item_name, rev):
    if rev is None:
        # no revision given
        _rev = -1 # for item creation
        destroy_item = True
    else:
        _rev = rev
        destroy_item = False
    item = Item.create(flaskg.context, item_name, rev_no=_rev)
    if request.method == 'GET':
        return render_template(item.destroy_template,
                               item=item, item_name=item_name,
                               rev_no=rev,
                              )
    if request.method == 'POST':
        if 'button_ok' in flaskg.context.form:
            comment = flaskg.context.form.get('comment')
            item.destroy(comment=comment, destroy_item=destroy_item)
        return redirect(url_for('frontend.show_item', item_name=item_name))


@frontend.route('/+index/<itemname:item_name>')
def index(item_name):
    item = Item.create(flaskg.context, item_name)
    index = item.flat_index()
    return render_template(item.index_template,
                           item=item, item_name=item_name,
                           index=index,
                          )


@frontend.route('/+index')
def global_index():
    item = Item.create(flaskg.context, '') # XXX hack: item_name='' gives toplevel index
    index = item.flat_index()
    item_name = request.values.get('item_name', '') # actions menu puts it into qs
    return render_template('global_index.html',
                           item_name=item_name, # XXX no item
                           index=index,
                          )


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
    history = flaskg.storage.history(item_name=item_name)
    return render_template('history.html',
                           item_name=item_name, # XXX no item here
                           history=history,
                          )


@frontend.route('/+history')
def global_history():
    history = flaskg.storage.history(item_name='')
    item_name = request.values.get('item_name', '') # actions menu puts it into qs
    return render_template('global_history.html',
                           item_name=item_name, # XXX no item
                           history=history,
                          )


@frontend.route('/+quicklink/<itemname:item_name>')
def quicklink_item(item_name):
    """ Add/Remove the current wiki page to/from the user quicklinks """
    request = flaskg.context
    u = flaskg.user
    msg = None
    if not u.valid:
        msg = _("You must login to use this action: %(action)s.") % {"action": "quicklink/quickunlink"}, "error"
    elif not flaskg.user.isQuickLinkedTo([item_name]):
        if not u.addQuicklink(item_name):
            msg = _('A quicklink to this page could not be added for you.'), "error"
    else:
        if not u.removeQuicklink(item_name):
            msg = _('Your quicklink to this page could not be removed.'), "error"
    if msg:
        flash(*msg)
    return redirect(url_for('frontend.show_item', item_name=item_name))


@frontend.route('/+subscribe/<itemname:item_name>')
def subscribe_item(item_name):
    """ Add/Remove the current wiki item to/from the user's subscriptions """
    request = flaskg.context
    u = flaskg.user
    cfg = app.cfg
    msg = None
    if not u.valid:
        msg = _("You must login to use this action: %(action)s.") % {"action": "subscribe/unsubscribe"}, "error"
    elif not u.may.read(item_name):
        msg = _("You are not allowed to subscribe to an item you may not read."), "error"
    elif not cfg.mail_enabled:
        msg = _("This wiki is not enabled for mail processing."), "error"
    elif not u.email:
        msg = _("Add your email address in your user settings to use subscriptions."), "error"
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
    return redirect(url_for('frontend.show_item', item_name=item_name))


class ValidRegistration(Validator):
    """Validator for a valid registration form
    """
    passwords_mismatch_msg = N_('The passwords do not match.')

    def validate(self, element, state):
        if not (element['username'].valid and
                element['password1'].valid and element['password2'].valid and
                element['email'].valid):
            return False
        if element['password1'].value != element['password2'].value:
            return self.note_error(element, state, 'passwords_mismatch_msg')
        return True


class RegistrationForm(Form):
    """a simple user registration form"""
    name = 'register'

    username = String.using(label=N_('Name')).validated_by(Present())
    password1 = String.using(label=N_('Password')).validated_by(Present())
    password2 = String.using(label=N_('Password')).validated_by(Present())
    email = String.using(label=N_('E-Mail')).validated_by(IsEmail())
    submit = String.using(default=N_('Register'), optional=True)

    validators = [ValidRegistration()]


def _using_moin_auth():
    """Check if MoinAuth is being used for authentication.

    Only then users can register with moin or change their password via moin.
    """
    from MoinMoin.auth import MoinAuth
    for auth in app.cfg.auth:
        if isinstance(auth, MoinAuth):
            return True
    return False


@frontend.route('/+register', methods=['GET', 'POST'])
def register():
    request = flaskg.context
    item_name = 'Register' # XXX

    if not _using_moin_auth():
        return Response('No MoinAuth in auth list', 403)

    if request.method == 'GET':
        form = RegistrationForm.from_defaults()
        return render_template('register.html',
                               gen=make_generator(),
                               form=form,
                              )
    if request.method == 'POST':
        form = RegistrationForm.from_flat(request.form)
        valid = form.validate()
        if valid:
            msg = user.create_user(request,
                                   username=form['username'].value,
                                   password=form['password1'].value,
                                   email=form['email'].value,
                                  )
            if msg:
                flash(msg, "error")
            else:
                flash(_('Account created, please log in now.'), "info")
            return redirect(url_for('frontend.show_root'))
        else:
            return render_template('register.html',
                                   gen=make_generator(),
                                   form=form,
                                  )


class ValidChangePass(Validator):
    """Validator for a valid password change
    """
    passwords_mismatch_msg = N_('The passwords do not match.')
    current_password_wrong_msg = N_('The current password was wrong.')
    password_encoding_problem_msg = N_('New password is unacceptable, encoding trouble.')

    def validate(self, element, state):
        if not (element['password_current'].valid and element['password1'].valid and element['password2'].valid):
            return False

        if not element['password_current'].value: # XXX add the real pw check
            return self.note_error(element, state, 'current_password_wrong_msg')

        if element['password1'].value != element['password2'].value:
            return self.note_error(element, state, 'passwords_mismatch_msg')

        try:
            user.encodePassword(element['password1'].value)
        except UnicodeError:
            return self.note_error(element, state, 'password_encoding_problem_msg')

        return True


class ChangePassForm(Form):
    """a simple change password form"""
    name = 'changepass'

    password_current = String.using(label=N_('Current Password')).validated_by(Present())
    password1 = String.using(label=N_('New password')).validated_by(Present())
    password2 = String.using(label=N_('New password (repeat)')).validated_by(Present())
    submit = String.using(default=N_('Change password'), optional=True)

    validators = [ValidChangePass()]


@frontend.route('/+changepass', methods=['GET', 'POST'])
def changepass():
    request = flaskg.context
    item_name = 'ChangePass' # XXX

    if not _using_moin_auth():
        return Response('No MoinAuth in auth list', 403)

    if request.method == 'GET':
        form = ChangePassForm.from_defaults()
        return render_template('changepass.html',
                               gen=make_generator(),
                               form=form,
                              )
    if request.method == 'POST':
        form = ChangePassForm.from_flat(request.form)
        valid = form.validate()
        if valid:
            flaskg.user.enc_password = user.encodePassword(form['password1'].value)
            flaskg.user.save()
            flash(_("Your password has been changed."), "info")
            return redirect(url_for('frontend.show_root'))
        else:
            return render_template('changepass.html',
                                   gen=make_generator(),
                                   form=form,
                                  )


class ValidLostPassword(Validator):
    """Validator for a valid lost password form
    """
    name_or_email_needed_msg = N_('Your user name or your email address is needed.')

    def validate(self, element, state):
        if not(element['username'].valid and element['username'].value
               or
               element['email'].valid and element['email'].value):
            return self.note_error(element, state, 'name_or_email_needed_msg')

        return True


class PasswordLostForm(Form):
    """a simple password lost form"""
    name = 'lostpass'

    username = String.using(label=N_('Name'), optional=True)
    email = String.using(label=N_('E-Mail'), optional=True).validated_by(IsEmail())
    submit = String.using(default=N_('Recover password'), optional=True)

    validators = [ValidLostPassword()]


@frontend.route('/+lostpass', methods=['GET', 'POST'])
def lostpass():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    item_name = 'LostPass' # XXX

    if not _using_moin_auth():
        return Response('No MoinAuth in auth list', 403)

    if request.method == 'GET':
        form = PasswordLostForm.from_defaults()
        return render_template('lostpass.html',
                               item_name=item_name,
                               gen=make_generator(),
                               form=form,
                              )
    if request.method == 'POST':
        form = PasswordLostForm.from_flat(request.form)
        valid = form.validate()
        if valid:
            u = None
            username = form['username'].value
            if username:
                u = user.User(flaskg.context, user.getUserId(username))
            email = form['email'].value
            if form['email'].valid and email:
                u = user.get_by_email_address(flaskg.context, email)
            if u and u.valid:
                is_ok, msg = u.mailAccountData()
                if not is_ok:
                    flash(msg, "error")
            flash(_("If this account exists, you will be notified."), "info")
            return redirect(url_for('frontend.show_root'))
        else:
            return render_template('lostpass.html',
                                   item_name=item_name,
                                   gen=make_generator(),
                                   form=form,
                                  )

class ValidPasswordRecovery(Validator):
    """Validator for a valid password recovery form
    """
    passwords_mismatch_msg = N_('The passwords do not match.')
    password_encoding_problem_msg = N_('New password is unacceptable, encoding trouble.')

    def validate(self, element, state):
        if element['password1'].value != element['password2'].value:
            return self.note_error(element, state, 'passwords_mismatch_msg')

        try:
            user.encodePassword(element['password1'].value)
        except UnicodeError:
            return self.note_error(element, state, 'password_encoding_problem_msg')

        return True

class PasswordRecoveryForm(Form):
    """a simple password recovery form"""
    name = 'recoverpass'

    username = String.using(label=N_('Name')).validated_by(Present())
    token = String.using(label=N_('Recovery token')).validated_by(Present())
    password1 = String.using(label=N_('New password')).validated_by(Present())
    password2 = String.using(label=N_('New password (repeat)')).validated_by(Present())
    submit = String.using(default=N_('Change password'), optional=True)

    validators = [ValidPasswordRecovery()]


@frontend.route('/+recoverpass', methods=['GET', 'POST'])
def recoverpass():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    item_name = 'RecoverPass' # XXX

    if not _using_moin_auth():
        return Response('No MoinAuth in auth list', 403)

    if request.method == 'GET':
        form = PasswordRecoveryForm.from_defaults()
        form.update(request.values)
        return render_template('recoverpass.html',
                               item_name=item_name,
                               gen=make_generator(),
                               form=form,
                              )
    if request.method == 'POST':
        form = PasswordRecoveryForm.from_flat(request.form)
        valid = form.validate()
        if valid:
            u = user.User(request, user.getUserId(form['username'].value))
            if u and u.valid and u.apply_recovery_token(form['token'].value, form['password1'].value):
                flash(_("Your password has been changed, you can log in now."), "info")
            else:
                flash(_('Your token is invalid!'), "error")
            return redirect(url_for('frontend.show_root'))
        else:
            return render_template('recoverpass.html',
                                   item_name=item_name,
                                   gen=make_generator(),
                                   form=form,
                                  )


@frontend.route('/+usersettings', methods=['GET', ])
def usersettings():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    item_name = 'User Settings' # XXX
    return render_template('usersettings.html',
                           item_name=item_name,
                          )


class ValidLogin(Validator):
    """Validator for a valid login

    If username is wrong or password is wrong, we do not tell exactly what was
    wrong, to prevent username phishing attacks.
    """
    fail_msg = N_('Either your username or password was invalid.')

    def validate(self, element, state):
        if not (element['username'].valid and element['password'].valid):
            return False
        # the real login happens at another place. if it worked, we have a valid user
        if flaskg.user.valid:
            return True
        else:
            return self.note_error(element, state, 'fail_msg')


class LoginForm(Form):
    """a simple login form"""
    name = 'login'

    username = String.using(label=N_('Name')).validated_by(Present())
    password = String.using(label=N_('Password')).validated_by(Present())
    submit = String.using(default=N_('Log in'), optional=True)

    validators = [ValidLogin()]


@frontend.route('/+login', methods=['GET', 'POST'])
def login():
    # TODO use ?next=next_location check if target is in the wiki and not outside domain
    item_name = 'LoggedIn' # XXX
    request = flaskg.context
    if request.method == 'GET':
        for authmethod in app.cfg.auth:
            hint = authmethod.login_hint(request)
            if hint:
                flash(hint, "info")
        form = LoginForm.from_defaults()
        return render_template('login.html',
                               login_inputs=app.cfg.auth_login_inputs,
                               gen=make_generator(),
                               form=form,
                              )
    if request.method == 'POST':
        for msg in flaskg._login_messages:
            flash(msg, "error")
        form = LoginForm.from_flat(request.form)
        valid = form.validate()
        if valid:
            # we have a logged-in, valid user
            userobj = flaskg.user
            session['user.id'] = userobj.id
            session['user.auth_method'] = userobj.auth_method
            session['user.auth_attribs'] = userobj.auth_attribs
            return redirect(url_for('frontend.show_root'))
        else:
            # if no valid user, show form again (with hints)
            return render_template('login.html',
                                   login_inputs=app.cfg.auth_login_inputs,
                                   gen=make_generator(),
                                   form=form,
                                  )


@frontend.route('/+logout')
def logout():
    item_name = 'LoggedOut' # XXX
    request = flaskg.context
    flash(_("You are now logged out."), "info")
    for key in ['user.id', 'user.auth_method', 'user.auth_attribs', ]:
        if key in session:
            del session[key]
    return redirect(url_for('frontend.show_root'))


@frontend.route('/+diffsince/<int:timestamp>/<path:item_name>')
def diffsince(item_name, timestamp):
    date = timestamp
    # this is how we get called from "recent changes"
    # try to find the latest rev1 before bookmark <date>
    item = flaskg.storage.get_item(item_name)
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
    item = flaskg.storage.get_item(item_name)
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
                           item=item, item_name=item.name,
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
        for name in keys:
            rank = matches[name]
            if rank == wanted_rank:
                item_names.append(name)
    return render_template("item_link_list.html",
                           headline=_("Items with similar names"),
                           item_name=item_name, # XXX no item
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
    item_names = [item.name for item in flaskg.storage.iteritems()]
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


@frontend.route('/+sitemap/<item_name>')
def sitemap(item_name):
    """
    sitemap view shows item link structure, relative to current item
    """
    sitemap = NestedItemListBuilder(flaskg.context).recurse_build([item_name])
    del sitemap[0] # don't show current item name as sole toplevel list item
    return render_template('sitemap.html',
                           item_name=item_name, # XXX no item
                           sitemap=sitemap,
                          )


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
        item = flaskg.storage.get_item(name)
        rev = item.get_revision(-1)
        itemlinks = rev.get(ITEMLINKS, [])
        return [child for child in itemlinks if self.is_ok(child)]

    def is_ok(self, child):
        if child not in self.children:
            if not flaskg.user.may.read(child):
                return False
            if flaskg.storage.has_item(child):
                self.children.add(child)
                return True
        return False

